from __future__ import annotations

import sys
from pathlib import Path


FORBIDDEN_NAMES = {
    "gcs-service-account.json",
    "settings.json",
}
FORBIDDEN_SUFFIXES = {".pfx", ".p12", ".key"}
REQUIRED_FILES = {
    "PRANA_ELEX.exe",
    "_internal/config/default.toml",
    "_internal/prana_elex/ui/resources/styles.qss",
}


def main() -> int:
    bundle = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/PRANA_ELEX").resolve()
    if not bundle.is_dir():
        print(f"[ERROR] Release directory not found: {bundle}")
        return 1

    relative_files = {
        path.relative_to(bundle).as_posix(): path
        for path in bundle.rglob("*")
        if path.is_file()
    }

    missing = sorted(REQUIRED_FILES - relative_files.keys())
    forbidden = sorted(
        relative
        for relative, path in relative_files.items()
        if path.name.lower() in FORBIDDEN_NAMES
        or path.suffix.lower() in FORBIDDEN_SUFFIXES
        or "service-account" in path.name.lower()
    )

    if missing:
        print("[ERROR] Required release files are missing:")
        for relative in missing:
            print(f"  - {relative}")
    if forbidden:
        print("[ERROR] Sensitive files must not be distributed:")
        for relative in forbidden:
            print(f"  - {relative}")
    if missing or forbidden:
        return 1

    total_bytes = sum(path.stat().st_size for path in relative_files.values())
    print(f"[OK] Release validated: {len(relative_files)} files, {total_bytes / 1024 / 1024:.1f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
