from __future__ import annotations

import subprocess

from tools.ci.changed_components import COMPONENTS, changed_paths, classify_paths


def enabled(*names: str) -> dict[str, bool]:
    return {component: component in names for component in COMPONENTS}


def test_docs_only_runs_no_heavy_component() -> None:
    assert classify_paths(["README.md", "docs/operations/cicd.md"]) == enabled()


def test_api_source_runs_backend_and_api_container() -> None:
    assert classify_paths(["services/prana_api/main.py"]) == enabled(
        "backend", "deploy_api"
    )


def test_api_test_does_not_request_deployment() -> None:
    assert classify_paths(["tests/api/test_main.py"]) == enabled("backend")


def test_core_change_runs_linux_and_windows() -> None:
    assert classify_paths(["packages/prana_core/src/prana_core/audio/base.py"]) == enabled(
        "core_linux", "windows"
    )


def test_platform_and_terraform_changes_are_targeted() -> None:
    assert classify_paths(
        ["apps/android/lib/main.dart", "infra/terraform/main.tf"]
    ) == enabled("android", "terraform")


def test_container_context_change_rebuilds_both_services() -> None:
    assert classify_paths([".dockerignore"]) == enabled(
        "deploy_api", "deploy_admin"
    )


def test_workflow_or_ci_helper_change_fails_safe_to_all_components() -> None:
    assert classify_paths([".github/workflows/ci.yml"]) == enabled(*COMPONENTS)
    assert classify_paths(["tools/ci/changed_components.py"]) == enabled(*COMPONENTS)


def test_unknown_path_fails_safe_to_all_components() -> None:
    assert classify_paths(["new-subsystem/config.yaml"]) == enabled(*COMPONENTS)


def _git(cwd, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def test_changed_paths_covers_an_entire_multi_commit_range(tmp_path, monkeypatch) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "ci@example.invalid")
    _git(tmp_path, "config", "user.name", "CI Test")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (tmp_path / "api.py").write_text("api\n", encoding="utf-8")
    _git(tmp_path, "add", "api.py")
    _git(tmp_path, "commit", "-m", "api")
    (tmp_path / "mobile.dart").write_text("mobile\n", encoding="utf-8")
    _git(tmp_path, "add", "mobile.dart")
    _git(tmp_path, "commit", "-m", "mobile")
    head = _git(tmp_path, "rev-parse", "HEAD")

    monkeypatch.chdir(tmp_path)
    paths, fallback = changed_paths(base, head)
    assert fallback is False
    assert paths == ["api.py", "mobile.dart"]


def test_invalid_base_falls_back_to_all_tracked_files(tmp_path, monkeypatch) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "ci@example.invalid")
    _git(tmp_path, "config", "user.name", "CI Test")
    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "base")
    head = _git(tmp_path, "rev-parse", "HEAD")

    monkeypatch.chdir(tmp_path)
    paths, fallback = changed_paths("0" * 40, head)
    assert fallback is True
    assert paths == ["tracked.txt"]
