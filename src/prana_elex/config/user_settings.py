from __future__ import annotations

import json
import sys
from pathlib import Path


_DEFAULT_FILENAME = "settings.json"


def _get_settings_path() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent.resolve()
        return exe_dir / _DEFAULT_FILENAME
    return Path(__file__).resolve().parent.parent.parent.parent / _DEFAULT_FILENAME


def load_settings() -> dict:
    path = _get_settings_path()
    if path.exists():
        try:
            # Inno Setup may write UTF-8 with a BOM. utf-8-sig accepts both
            # BOM and regular UTF-8 files.
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                result = {}
                if isinstance(data.get("data_dir"), str):
                    result["data_dir"] = data["data_dir"]
                if isinstance(data.get("credentials_path"), str):
                    result["credentials_path"] = data["credentials_path"]
                if result:
                    return result
        except Exception:
            pass
    return {"data_dir": "", "credentials_path": ""}


def save_settings(data_dir: str, credentials_path: str = "") -> None:
    path = _get_settings_path()
    path.write_text(
        json.dumps(
            {
                "data_dir": data_dir,
                "credentials_path": credentials_path,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def ensure_settings() -> str:
    settings = load_settings()
    if not settings.get("data_dir"):
        data_dir = str(Path.home() / "Desktop")
        save_settings(data_dir)
        return data_dir
    return settings["data_dir"]
