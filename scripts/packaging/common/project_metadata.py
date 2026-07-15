from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_metadata() -> dict[str, str]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]

    authors = project.get("authors") or []
    vendor = authors[0].get("name", "") if authors else ""
    return {
        "name": str(project["name"]),
        "version": str(project["version"]),
        "description": str(project.get("description", "")),
        "vendor": vendor,
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
