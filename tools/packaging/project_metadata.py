from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_metadata() -> dict[str, str]:
    version_file = PROJECT_ROOT / "packages" / "prana_core" / "src" / "prana_core" / "VERSION"
    return {
        "name": "prana-elex",
        "version": version_file.read_text(encoding="utf-8").strip(),
        "description": "PRANA ELEX VHF transcription and translation",
        "vendor": "DLV Corporation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read canonical project metadata")
    parser.add_argument("--field", choices=("name", "version", "description", "vendor"))
    args = parser.parse_args()
    metadata = load_metadata()
    print(metadata[args.field] if args.field else json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
