"""Rules about how workflows pin their actions.

Actions are pinned by commit SHA with the version in a trailing comment, so
nothing here can be read off a tag. These tests read the pins as text.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github"
PIN = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@([0-9a-f]{40})\s*#\s*(v[\d.]+)")
USE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(?:\s*#\s*(\S+))?", re.MULTILINE)


def _pins() -> dict[str, set[tuple[str, str]]]:
    found: dict[str, set[tuple[str, str]]] = {}
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        for action, sha, version in PIN.findall(path.read_text(encoding="utf-8")):
            found.setdefault(action, set()).add((sha, version))
    return found


class WorkflowActionPinTests(unittest.TestCase):
    def test_every_external_action_is_pinned_to_commit_sha(self) -> None:
        for path in sorted(WORKFLOWS.rglob("*.yml")):
            for reference, version in USE.findall(path.read_text(encoding="utf-8")):
                if reference.startswith("./"):
                    continue
                with self.subTest(path=path, reference=reference):
                    self.assertRegex(reference, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
                    self.assertRegex(version, r"^v[\d.]+$")

    def test_every_action_is_pinned_to_one_sha(self) -> None:
        # The same action on two SHAs means a bump missed a workflow, and the
        # one it missed is usually a deploy path CI never exercises.
        for action, pins in _pins().items():
            with self.subTest(action=action):
                self.assertEqual(len(pins), 1, f"{action} pinned to {pins}")

    def test_artifact_upload_and_download_share_a_major(self) -> None:
        # terraform-staging.yml uploads a plan in one job and applies it in the
        # next. v5 changed download paths and v8 changed unzipping, so a pair on
        # different majors risks an apply that cannot find its own plan -- and
        # no CI job runs that path.
        pins = _pins()
        majors = {
            name: next(iter(pins[name]))[1].lstrip("v").split(".")[0]
            for name in ("actions/upload-artifact", "actions/download-artifact")
            if name in pins
        }
        self.assertEqual(len(majors), 2, "both artifact actions must be present")
        self.assertEqual(
            len(set(majors.values())), 1, f"artifact actions disagree: {majors}"
        )


if __name__ == "__main__":
    unittest.main()
