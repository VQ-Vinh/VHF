from __future__ import annotations

import json
import os
import sys
from pathlib import Path


_DEFAULT_FILENAME = "settings.json"


def get_settings_dir() -> Path:
    if sys.platform.startswith("linux"):
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "prana-elex"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PRANA ELEX"
    return Path(__file__).resolve().parent.parent.parent.parent


def get_settings_path() -> Path:
    return get_settings_dir() / _DEFAULT_FILENAME


def get_machine_settings_path() -> Path:
    base = Path(os.environ.get("PROGRAMDATA", Path.home() / "AppData" / "ProgramData"))
    return base / "PRANA ELEX" / _DEFAULT_FILENAME


def get_user_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PRANA ELEX"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "prana-elex"


def _load_settings_file(path: Path) -> dict[str, str] | None:
    if path.exists():
        try:
            try:
                raw = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                if sys.platform != "win32":
                    raise
                # PRANA ELEX 1.1.0 installers wrote this file using the active
                # Windows code page. Keep upgrades working, then save_settings
                # will replace it with UTF-8 on the next update.
                raw = path.read_text(encoding="mbcs")
            data = json.loads(raw)
            if isinstance(data, dict):
                return {
                    "data_dir": data.get("data_dir", "") if isinstance(data.get("data_dir", ""), str) else "",
                    "ui_locale": data.get("ui_locale", "en") if data.get("ui_locale") in {"en", "vi"} else "en",
                }
        except (OSError, ValueError):
            pass
    return None


def load_settings() -> dict[str, str]:
    paths = [get_settings_path()]
    if sys.platform == "win32":
        paths.append(get_machine_settings_path())
    result = {"data_dir": "", "ui_locale": "en"}
    for index, path in enumerate(paths):
        settings = _load_settings_file(path)
        if not settings:
            continue
        if index == 0:
            result["ui_locale"] = settings.get("ui_locale", "en")
        if settings.get("data_dir") and not result["data_dir"]:
            result["data_dir"] = settings["data_dir"]
    return result


def save_settings(data_dir: str | None = None, ui_locale: str | None = None) -> None:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("linux"):
        path.parent.chmod(0o700)
    current = _load_settings_file(path) or {"data_dir": "", "ui_locale": "en"}
    if data_dir is not None:
        current["data_dir"] = data_dir
    if ui_locale in {"en", "vi"}:
        current["ui_locale"] = ui_locale
    path.write_text(
        json.dumps(
            current,
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
        save_settings(data_dir)
        return data_dir
    return settings["data_dir"]
