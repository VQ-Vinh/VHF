from pathlib import Path

import qtawesome
from PySide6.QtGui import QIcon
from qtawesome.iconic_font import IconicFont


_phosphor_icons: IconicFont | None = None


def phosphor_icon(
    name: str,
    *,
    color: str = "#B8B8C8",
    active_color: str = "#00D7ED",
    scale_factor: float = 1.0,
) -> QIcon:
    global _phosphor_icons
    if _phosphor_icons is None:
        fonts_dir = Path(qtawesome.__file__).resolve().parent / "fonts"
        _phosphor_icons = IconicFont(
            (
                "ph",
                "phosphor-1.3.0.ttf",
                "phosphor-charmap-1.3.0.json",
                str(fonts_dir),
            )
        )
    return _phosphor_icons.icon(
        name,
        color=color,
        color_active=active_color,
        scale_factor=scale_factor,
    )
