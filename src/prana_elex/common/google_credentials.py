from __future__ import annotations

import os
import sys
from pathlib import Path

from google.auth.credentials import Credentials
from google.oauth2 import service_account


GOOGLE_CREDENTIALS_ENV = "PRANA_ELEX_GOOGLE_CREDENTIALS"
_LEGACY_GCS_CREDENTIALS_ENV = "PRANA_ELEX_GCS_CREDENTIALS"
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def resolve_google_credentials_path(configured_path: str = "") -> Path | None:
    """Resolve the shared Google service-account key in source and frozen apps."""
    raw_path = (
        os.environ.get(GOOGLE_CREDENTIALS_ENV, "").strip()
        or os.environ.get(_LEGACY_GCS_CREDENTIALS_ENV, "").strip()
        or configured_path.strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    if not raw_path:
        return None

    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()

    bases: list[Path] = [Path.cwd()]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        bases.extend([exe_dir, exe_dir.parent, exe_dir.parent.parent])
    else:
        bases.append(Path(__file__).resolve().parents[3])

    checked: set[Path] = set()
    for base in bases:
        candidate = (base / path).resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if candidate.is_file():
            return candidate

    return (bases[0] / path).resolve()


def load_google_credentials(configured_path: str) -> tuple[Credentials, str, Path]:
    """Load explicit service-account credentials and their Google Cloud project."""
    path = resolve_google_credentials_path(configured_path)
    if path is None:
        raise ValueError(
            "Google service-account JSON is not configured. Set "
            f"google_cloud.credentials_path or {GOOGLE_CREDENTIALS_ENV}."
        )
    if not path.is_file():
        raise FileNotFoundError(f"Google service-account JSON not found: {path}")

    credentials = service_account.Credentials.from_service_account_file(
        str(path),
        scopes=[_CLOUD_PLATFORM_SCOPE],
    )
    project_id = credentials.project_id
    if not project_id:
        raise ValueError(f"Google service-account JSON has no project_id: {path}")

    return credentials, project_id, path
