from __future__ import annotations

import argparse
import os
import platform
import struct
import subprocess
import tomllib
from pathlib import Path


FORBIDDEN_NAMES = {
    "gcs-service-account.json",
    "settings.json",
    "auth.json",
    "credentials.json",
}
FORBIDDEN_SUFFIXES = {".pfx", ".p12", ".key"}

REQUIRED_FILES = {
    "windows": {
        "PRANA_ELEX.exe",
        "_internal/config/default.toml",
        "_internal/prana_windows/ui/resources/styles.qss",
        "_internal/prana_windows/ui/resources/google-g.svg",
    },
    "linux-arm64": {
        "PRANA_Station",
        "_internal/config/default.toml",
    },
}


def _elf_machine(path: Path) -> int | None:
    try:
        header = path.read_bytes()[:20]
    except OSError:
        return None
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return None
    byte_order = "<" if header[5] == 1 else ">"
    return struct.unpack(f"{byte_order}H", header[18:20])[0]


def _is_runtime_data(relative: str) -> bool:
    parts = {part.lower() for part in Path(relative).parts}
    name = Path(relative).name.lower()
    return (
        "vhf_storage" in parts
        or "prana_elex_data" in parts
        or name.startswith("vhf-ai-")
        or name in {"stdin.txt", "stdout.txt", "stderr.txt", "out.txt", "err.txt"}
    )


def _contains_private_key(path: Path) -> bool:
    if path.suffix.lower() not in {".pem", ".json", ".txt"}:
        return False
    try:
        return b"PRIVATE KEY" in path.read_bytes()[:65536]
    except OSError:
        return False


def _validate_linux_dependencies(files: dict[str, Path]) -> list[str]:
    if platform.system() != "Linux":
        return []

    errors: list[str] = []
    for relative, path in files.items():
        if _elf_machine(path) is None:
            continue
        result = subprocess.run(
            ["ldd", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = f"{result.stdout}\n{result.stderr}"
        if "not found" in output:
            missing = [line.strip() for line in output.splitlines() if "not found" in line]
            errors.extend(f"{relative}: {line}" for line in missing)
    return errors


def _validate_backend_config(path: Path | None, platform_name: str) -> list[str]:
    if path is None:
        return []
    try:
        with path.open("rb") as stream:
            backend = tomllib.load(stream).get("backend", {})
    except (OSError, tomllib.TOMLDecodeError):
        return [f"Cannot parse backend build config: {path.name}"]
    api_url = str(backend.get("api_url", ""))
    firebase_key = str(backend.get("firebase_api_key", ""))
    google_client_id = str(backend.get("google_oauth_client_id", ""))
    errors: list[str] = []
    if not api_url.startswith("https://") or "REPLACE_WITH" in api_url:
        errors.append("Release backend.api_url must be the production HTTPS Cloud Run URL")
    if platform_name == "windows" and (not firebase_key or "REPLACE_WITH" in firebase_key):
        errors.append("Release backend.firebase_api_key must contain the Firebase Web API key")
    if platform_name == "windows" and (
        not google_client_id.endswith(".apps.googleusercontent.com")
        or "REPLACE_WITH" in google_client_id
    ):
        errors.append(
            "Release backend.google_oauth_client_id must contain the Google Desktop OAuth client ID"
        )
    return errors


def validate(platform_name: str, bundle: Path) -> int:
    bundle = bundle.resolve()
    if not bundle.is_dir():
        print(f"[ERROR] Release directory not found: {bundle}")
        return 1

    relative_files = {
        path.relative_to(bundle).as_posix(): path
        for path in bundle.rglob("*")
        if path.is_file()
    }
    missing = sorted(REQUIRED_FILES[platform_name] - relative_files.keys())
    forbidden = sorted(
        relative
        for relative, path in relative_files.items()
        if path.name.lower() in FORBIDDEN_NAMES
        or path.suffix.lower() in FORBIDDEN_SUFFIXES
        or "service-account" in path.name.lower()
        or "refresh-token" in path.name.lower()
        or "device-private" in path.name.lower()
        or _is_runtime_data(relative)
        or _contains_private_key(path)
    )

    errors: list[str] = []
    config_relative = (
        "_internal/config/default.toml"
    )
    errors.extend(_validate_backend_config(relative_files.get(config_relative), platform_name))
    if platform_name == "linux-arm64":
        executable = relative_files.get("PRANA_Station")
        if executable and _elf_machine(executable) != 183:
            errors.append("PRANA_Station is not an ELF aarch64 executable")
        if executable and not os.access(executable, os.X_OK):
            errors.append("PRANA_Station is not executable")
        errors.extend(_validate_linux_dependencies(relative_files))

    if missing:
        print("[ERROR] Required release files are missing:")
        for relative in missing:
            print(f"  - {relative}")
    if forbidden:
        print("[ERROR] Sensitive or runtime files must not be distributed:")
        for relative in forbidden:
            print(f"  - {relative}")
    if errors:
        print("[ERROR] Release validation failed:")
        for error in errors:
            print(f"  - {error}")
    if missing or forbidden or errors:
        return 1

    total_bytes = sum(path.stat().st_size for path in relative_files.values())
    print(
        f"[OK] {platform_name} release validated: "
        f"{len(relative_files)} files, {total_bytes / 1024 / 1024:.1f} MiB"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a platform release bundle")
    parser.add_argument("--platform", required=True, choices=sorted(REQUIRED_FILES))
    parser.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    return validate(args.platform, args.bundle)


if __name__ == "__main__":
    raise SystemExit(main())
