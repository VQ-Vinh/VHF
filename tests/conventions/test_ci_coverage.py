from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class CiSuiteCoverageTests(unittest.TestCase):
    """Every test suite must be named in a CI pytest invocation.

    CI lists the suite directories by hand, one job at a time, so adding or
    renaming a directory drops it from the gate with nothing failing.
    tests/conventions/ went dark exactly that way the day it was split out of
    tests/packaging/, taking the installer and git-mode guards with it.
    """

    def test_ci_runs_every_test_suite(self) -> None:
        suites = {
            path.name
            for path in (ROOT / "tests").iterdir()
            if path.is_dir() and any(path.glob("test_*.py"))
        }
        self.assertTrue(suites, "no test suites found under tests/")

        invoked: set[str] = set()
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
            if "pytest" not in line:
                continue
            invoked.update(re.findall(r"tests/([A-Za-z0-9_]+)", line))

        self.assertEqual(sorted(suites - invoked), [], "suites CI never runs")


if __name__ == "__main__":
    unittest.main()
