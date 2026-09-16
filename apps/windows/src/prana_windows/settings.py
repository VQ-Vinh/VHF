from __future__ import annotations

import json
import os
from pathlib import Path


_DEFAULT_FILENAME = "settings.json"


def get_settings_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PRANA ELEX"


def get_settings_path() -> Path:
    return get_settings_dir() / _DEFAULT_FILENAME


def get_machine_settings_path() -> Path:
    base = Path(os.environ.get("PROGRAMDATA", Path.home() / "AppData" / "ProgramData"))
    return base / "PRANA ELEX" / _DEFAULT_FILENAME


def get_user_config_dir() -> Path:
    return get_settings_dir()


def _load_settings_file(path: Path) -> dict[str, str] | None:
    if path.exists():
        try:
            try:
                raw = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                # PRANA ELEX 1.1.0 installers wrote this file using the active
                # Windows code page. Keep upgrades working, then save_settings
                # will replace it with UTF-8 on the next update.
                raw = path.read_text(encoding="mbcs")
            data = json.loads(raw)
            if isinstance(data, dict):
                return {
                    "data_dir": data.get("data_dir", "") if isinstance(data.get("data_dir", ""), str) else "",
                    "ui_locale": data.get("ui_locale", "en") if data.get("ui_locale") in {"en", "vi"} else "en",
                    # save_settings re-reads through this function before writing,
                    # so a key missing from this whitelist is erased on the next save.
                    "ui_theme": data.get("ui_theme", "light") if data.get("ui_theme") in {"light", "dark"} else "light",
                }
        except (OSError, ValueError):
            pass
    return None


def load_settings() -> dict[str, str]:
    paths = [get_settings_path()]
    paths.append(get_machine_settings_path())
    result = {"data_dir": "", "ui_locale": "en", "ui_theme": "light"}
    for index, path in enumerate(paths):
        settings = _load_settings_file(path)
        if not settings:
            continue
        if index == 0:
            result["ui_locale"] = settings.get("ui_locale", "en")
            # Appearance is a personal choice; the machine-wide file does not pin it.
            result["ui_theme"] = settings.get("ui_theme", "light")
        if settings.get("data_dir") and not result["data_dir"]:
            result["data_dir"] = settings["data_dir"]
    return result


def save_settings(
    data_dir: str | None = None,
    ui_locale: str | None = None,
    ui_theme: str | None = None,
) -> None:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _load_settings_file(path) or {"data_dir": "", "ui_locale": "en", "ui_theme": "light"}
    if data_dir is not None:
        current["data_dir"] = data_dir
    if ui_locale in {"en", "vi"}:
        current["ui_locale"] = ui_locale
    if ui_theme in {"light", "dark"}:
        current["ui_theme"] = ui_theme
    path.write_text(
        json.dumps(
            current,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def ensure_settings() -> str:
    settings = load_settings()
    if not settings.get("data_dir"):
        data_dir = str(Path.home() / "PRANA_ELEX_Data")
        save_settings(data_dir)
        return data_dir
    return settings["data_dir"]
