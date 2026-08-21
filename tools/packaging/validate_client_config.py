from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


# Only builds that sign a user in need the Firebase and Google OAuth values.
# The Raspberry Pi station authenticates with an Ed25519 signature per request
# and never reads them, so demanding them there forces a credential into a
# bundle that has no use for it. validate_release.py already scopes the same
# two checks this way.
SIGN_IN_PLATFORMS = {"windows"}


def validate(path: Path, platform_name: str = "windows") -> list[str]:
    try:
        with path.open("rb") as stream:
            backend = tomllib.load(stream).get("backend", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"Cannot read {path}: {exc}"]
    errors = []
    api_url = str(backend.get("api_url", ""))
    api_key = str(backend.get("firebase_api_key", ""))
    google_client_id = str(backend.get("google_oauth_client_id", ""))
    if not api_url.startswith("https://") or "REPLACE_WITH" in api_url:
        errors.append("backend.api_url must be the production HTTPS Cloud Run URL")
    if platform_name not in SIGN_IN_PLATFORMS:
        return errors
    if not api_key or "REPLACE_WITH" in api_key:
        errors.append("backend.firebase_api_key must contain the Firebase Web API key")
    if (
        not google_client_id.endswith(".apps.googleusercontent.com")
        or "REPLACE_WITH" in google_client_id
    ):
        errors.append(
            "backend.google_oauth_client_id must contain the Google Desktop OAuth client ID"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public client build configuration")
    parser.add_argument("config", type=Path)
    parser.add_argument("--platform", default="windows", choices=["windows", "linux-arm64"])
    args = parser.parse_args()
    errors = validate(args.config, args.platform)
    for error in errors:
        print(f"[ERROR] {error}")
    if errors:
        return 1
    print(f"[OK] Client build config: {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
