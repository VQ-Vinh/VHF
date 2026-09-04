from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_uses_range_selection_and_exports_staging_artifact() -> None:
    workflow = read(".github/workflows/ci.yml")
    assert "tools/ci/changed_components.py" in workflow
    assert 'git diff --check "$BASE_SHA" "$HEAD_SHA"' in workflow
    assert "name: deploy-selection" in workflow
    assert "retention-days: 1" in workflow
    assert "tests/conventions" in workflow
    assert '"$result" == success || "$result" == skipped' in workflow


def test_staging_consumes_selection_from_the_triggering_ci_run() -> None:
    workflow = read(".github/workflows/deploy-staging.yml")
    assert "run-id: ${{ github.event.workflow_run.id }}" in workflow
    assert "workflow_run.head_sha" in workflow
    assert "actions: read" in workflow
    assert "HEAD^ HEAD" not in workflow


def test_release_and_promotion_require_main_gate_provenance() -> None:
    android = read(".github/workflows/android-release.yml")
    production = read(".github/workflows/deploy-production.yml")
    for workflow in (android, production):
        assert "checks: read" in workflow
        assert "merge-base --is-ancestor" in workflow
        assert '.name == "gate" and .conclusion == "success"' in workflow
    assert "source_sha:" in production
    assert "status.imageDigest" in production
    assert "cosign verify" in production


def test_terraform_uploads_only_an_encrypted_saved_plan() -> None:
    workflow = read(".github/workflows/terraform-staging.yml")
    assert workflow.count("TFPLAN_ENCRYPTION_KEY") >= 2
    assert "--cipher-algo AES256" in workflow
    assert "path: infra/terraform/staging.tfplan.gpg" in workflow
    assert "path: infra/terraform/staging.tfplan\n" not in workflow
    assert "terraform apply -input=false" in workflow


def test_container_bases_are_digest_pinned_and_automated() -> None:
    expected = re.compile(r"^FROM python:3\.12-slim@sha256:[0-9a-f]{64}$", re.MULTILINE)
    assert expected.search(read("services/prana_api/Dockerfile"))
    assert expected.search(read("services/prana_admin/Dockerfile"))
    dependabot = read(".github/dependabot.yml")
    assert dependabot.count("package-ecosystem: docker") == 2
    assert "package-ecosystem: terraform" in dependabot


def test_staging_images_include_attestations_and_keyless_signatures() -> None:
    workflow = read(".github/workflows/deploy-staging.yml")
    assert workflow.count("provenance: mode=max") == 2
    assert workflow.count("sbom: true") == 2
    assert workflow.count("cosign sign --yes") == 2
