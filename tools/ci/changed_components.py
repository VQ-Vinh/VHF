from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterable


COMPONENTS = (
    "backend",
    "core_linux",
    "windows",
    "android",
    "terraform",
    "deploy_api",
    "deploy_admin",
)

QUALITY_ONLY_PREFIXES = ("docs/",)
QUALITY_ONLY_FILES = {
    ".gitignore",
    "AGENTS.md",
    "LICENSE",
    "LICENSE.md",
    "README.md",
}
FULL_CI_PREFIXES = (".github/", "tests/conventions/", "tools/ci/")


def _all_enabled() -> dict[str, bool]:
    return {component: True for component in COMPONENTS}


def classify_paths(paths: Iterable[str]) -> dict[str, bool]:
    result = {component: False for component in COMPONENTS}

    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        if not path:
            continue
        if path in QUALITY_ONLY_FILES or path.startswith(QUALITY_ONLY_PREFIXES):
            continue
        if path.startswith(FULL_CI_PREFIXES):
            return _all_enabled()

        matched = False
        if path.startswith(("services/prana_api/", "tests/api/")):
            result["backend"] = True
            if path.startswith("services/prana_api/"):
                result["deploy_api"] = True
            matched = True
        if path.startswith(("services/prana_admin/", "tests/admin/")):
            result["backend"] = True
            if path.startswith("services/prana_admin/"):
                result["deploy_admin"] = True
            matched = True
        if path.startswith("packages/prana_core/"):
            result["core_linux"] = True
            result["windows"] = True
            matched = True
        if path.startswith(("apps/linux/", "tests/core/", "tests/linux/", "tests/packaging/", "tools/packaging/")):
            result["core_linux"] = True
            matched = True
        if path.startswith(("apps/windows/", "tests/windows/")):
            result["windows"] = True
            matched = True
        if path.startswith("apps/android/"):
            result["android"] = True
            matched = True
        if path.startswith("infra/terraform/"):
            result["terraform"] = True
            matched = True

        if path in {".dockerignore", ".gcloudignore"}:
            result["deploy_api"] = True
            result["deploy_admin"] = True
            matched = True
        elif path == "pyproject.toml":
            result["backend"] = True
            result["core_linux"] = True
            result["windows"] = True
            matched = True
        elif path in {"buildlinux", "install.sh", "release-pi.sh"}:
            result["core_linux"] = True
            matched = True
        elif path in {"build_android_apk.bat", "run_android_emulator.bat"}:
            result["android"] = True
            matched = True
        elif path.startswith("scripts/setup/"):
            result["backend"] = True
            result["core_linux"] = True
            result["windows"] = True
            matched = True
        elif path.startswith("scripts/dev/"):
            result["core_linux"] = True
            result["windows"] = True
            matched = True

        if not matched:
            return _all_enabled()

    return result


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def _valid_commit(sha: str) -> bool:
    if not sha or set(sha) == {"0"}:
        return False
    return subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def changed_paths(base_sha: str, head_sha: str) -> tuple[list[str], bool]:
    if not _valid_commit(base_sha) or not _valid_commit(head_sha):
        payload = _git("ls-files", "-z")
        fallback = True
    else:
        payload = _git("diff", "--name-only", "-z", base_sha, head_sha)
        fallback = False
    return [item.decode("utf-8") for item in payload.split(b"\0") if item], fallback


def write_outputs(path: Path, values: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            rendered = str(value).lower() if isinstance(value, bool) else str(value)
            output.write(f"{key}={rendered}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify changed repository components")
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--event", choices=("pull_request", "push"), required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()

    paths, fallback = changed_paths(args.base_sha, args.head_sha)
    flags = classify_paths(paths)
    payload: dict[str, object] = {
        "base_sha": args.base_sha,
        "head_sha": args.head_sha,
        **flags,
        "all_tracked_fallback": fallback,
    }
    args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_outputs(args.github_output, payload)

    print(f"Changed files: {len(paths)}; fallback={fallback}")
    for component in COMPONENTS:
        print(f"{component}={str(flags[component]).lower()}")


if __name__ == "__main__":
    main()
