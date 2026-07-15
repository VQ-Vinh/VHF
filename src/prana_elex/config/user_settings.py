from __future__ import annotations

import json
import os
import sys
from pathlib import Path


_DEFAULT_FILENAME = "settings.json"


def get_settings_dir() -> Path:
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "prana-elex"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).resolve().parent.parent.parent.parent


def get_settings_path() -> Path:
    return get_settings_dir() / _DEFAULT_FILENAME


def get_credentials_path() -> Path:
    return get_settings_dir() / "gcs-service-account.json"


def load_settings() -> dict[str, str]:
    path = get_settings_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return {
                    "data_dir": data.get("data_dir", "") if isinstance(data.get("data_dir", ""), str) else "",
                    "credentials_path": data.get("credentials_path", "")
                    if isinstance(data.get("credentials_path", ""), str)
                    else "",
                }
        except (OSError, ValueError):
            pass
    return {"data_dir": "", "credentials_path": ""}


def save_settings(data_dir: str, credentials_path: str = "") -> None:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("linux"):
        path.parent.chmod(0o700)
    path.write_text(
        json.dumps(
            {"data_dir": data_dir, "credentials_path": credentials_path},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if sys.platform.startswith("linux"):
        path.chmod(0o600)


def ensure_settings() -> str:
    settings = load_settings()
    if not settings.get("data_dir"):
        data_dir = str(Path.home() / "PRANA_ELEX_Data")
        save_settings(data_dir, settings.get("credentials_path", ""))
        return data_dir
    return settings["data_dir"]
