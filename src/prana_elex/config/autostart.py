from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path


def _desktop_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / "prana-elex.desktop"


def is_supported() -> bool:
    return sys.platform.startswith("linux")


def is_enabled() -> bool:
    return is_supported() and _desktop_path().is_file()


def set_enabled(enabled: bool) -> None:
    if not is_supported():
        return
    path = _desktop_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    executable = "/usr/bin/prana-elex" if getattr(sys, "frozen", False) else sys.executable
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=PRANA ELEX",
                f"Exec={shlex.quote(executable)}",
                "Icon=audio-input-microphone",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)
