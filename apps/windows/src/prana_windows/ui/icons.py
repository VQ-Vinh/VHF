"""Icons in the Flutter app's icon language, coloured by theme token.

The phone uses Material icons (`Icons.radio`, `Icons.lock_outline`, ...). The
installed qtawesome already ships Material Design Icons 6, so the desktop draws
the same glyph family without a new dependency.

The font files are bound by explicit, version-stamped name. That is safe only
because apps/windows/pyproject.toml pins qtawesome exactly -- if that pin is ever
loosened, these names are what breaks. Note the charmap is
`materialdesignicons6-webfont-charmap-*.json`, with `-webfont-` in the middle,
unlike the Phosphor charmap this module used to load.

A QIcon is rasterised at the colour it was made with, so a theme switch cannot
repaint it the way it repaints a stylesheet. `bind_icon` records each target and
re-bakes it when the theme changes; widgets whose glyph depends on their own
state re-make their icon in their own `theme.changed` handler instead.
"""

from __future__ import annotations

import weakref
from pathlib import Path

import qtawesome
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel
from qtawesome.iconic_font import IconicFont

from prana_windows.ui.theme import theme

_FONT = ("mdi6", "materialdesignicons6-webfont-6.9.96.ttf", "materialdesignicons6-webfont-charmap-6.9.96.json")
_font: IconicFont | None = None
_bindings: list[tuple[weakref.ref, str, str, str, float]] = []


def _iconic_font() -> IconicFont:
    global _font
    if _font is None:
        fonts_dir = Path(qtawesome.__file__).resolve().parent / "fonts"
        _font = IconicFont((*_FONT, str(fonts_dir)))
    return _font


def themed_icon(
    name: str,
    *,
    role: str = "text_secondary",
    active_role: str = "accent",
    scale_factor: float = 1.0,
) -> QIcon:
    """A Material glyph coloured from the current theme.

    `role` and `active_role` are token names, never hex strings, so the colour
    always follows the theme.
    """
    return _iconic_font().icon(
        f"mdi6.{name}",
        color=theme.token(role),
        color_active=theme.token(active_role),
        scale_factor=scale_factor,
    )


def bind_icon(
    target,
    name: str,
    *,
    role: str = "text_secondary",
    active_role: str = "accent",
    scale_factor: float = 1.0,
) -> None:
    """Set an icon on `target` and keep it in step with the theme.

    Weak references, because rows and bubbles are created and deleted
    constantly; a strong registry would keep dead wrappers alive and eventually
    touch a deleted C++ object.
    """
    target.setIcon(themed_icon(name, role=role, active_role=active_role, scale_factor=scale_factor))
    _bindings.append((weakref.ref(target), name, role, active_role, scale_factor))


def _rebake(*_args) -> None:
    import shiboken6

    alive = []
    for ref, name, role, active_role, scale in _bindings:
        target = ref()
        if target is None or not shiboken6.isValid(target):
            continue
        target.setIcon(themed_icon(name, role=role, active_role=active_role, scale_factor=scale))
        alive.append((ref, name, role, active_role, scale))
    _bindings[:] = alive


theme.changed.connect(_rebake)


class GlyphLabel(QLabel):
    """A standalone glyph beside a label, re-baked when the theme changes.

    `bind_icon` needs a widget with `setIcon`; a QLabel only has a pixmap.
    """

    def __init__(self, name: str, *, role: str, size: int = 16, parent=None):
        super().__init__(parent)
        self._name, self._role, self._size = name, role, size
        self.setFixedSize(size, size)
        theme.changed.connect(self._repaint)
        self._repaint()

    def _repaint(self, *_args) -> None:
        self.setPixmap(themed_icon(self._name, role=self._role).pixmap(self._size, self._size))


__all__ = ["GlyphLabel", "bind_icon", "themed_icon"]
