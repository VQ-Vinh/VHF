from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


def validate(path: Path) -> list[str]:
    try:
        with path.open("rb") as stream:
            backend = tomllib.load(stream).get("backend", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"Cannot read {path}: {exc}"]
    errors = []
    api_url = str(backend.get("api_url", ""))
    api_key = str(backend.get("firebase_api_key", ""))
    if not api_url.startswith("https://") or "REPLACE_WITH" in api_url:
        errors.append("backend.api_url must be the production HTTPS Cloud Run URL")
    if not api_key or "REPLACE_WITH" in api_key:
        errors.append("backend.firebase_api_key must contain the Firebase Web API key")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public client build configuration")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    errors = validate(args.config)
    for error in errors:
        print(f"[ERROR] {error}")
    if errors:
        return 1
    print(f"[OK] Client build config: {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
