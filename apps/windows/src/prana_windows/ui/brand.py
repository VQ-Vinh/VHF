"""The PRANA ELEX mark, as the desktop twin of `apps/android/lib/core/brand.dart`.

The mark is single-ink artwork with alpha, so it is recoloured at runtime by
compositing a solid colour into its alpha -- the Qt equivalent of the Flutter
widget's `BlendMode.srcIn`. One PNG therefore serves both themes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel

from prana_windows.ui.theme import theme

RESOURCES = Path(__file__).resolve().parent / "resources"


def resource(name: str) -> Path:
    """A bundled resource. Under PyInstaller `__file__` already sits inside
    `_MEIPASS/prana_windows/ui`, where the spec places `resources/`."""
    return RESOURCES / name


@lru_cache(maxsize=32)
def mark_pixmap(size: int, colour: str) -> QPixmap:
    source = QPixmap(str(resource("logo_mark.png")))
    if source.isNull():
        return QPixmap()
    scaled = source.scaled(QSize(size, size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    tinted = QPixmap(scaled.size())
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, scaled)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(colour))
    painter.end()
    return tinted


def app_icon() -> QIcon:
    """One icon for the window, taskbar and tray: the same .ico the installer uses."""
    return QIcon(str(resource("prana-elex.ico")))


class BrandMark(QLabel):
    """The mark before a page title, the way every Flutter header carries one."""

    def __init__(self, size: int = 28, role: str = "accent", parent=None):
        super().__init__(parent)
        self.setObjectName("BrandMark")
        self._size = size
        self._role = role
        self.setFixedSize(size, size)
        self.setAccessibleName("PRANA ELEX")
        theme.changed.connect(self._repaint)
        self._repaint()

    def _repaint(self, *_args) -> None:
        self.setPixmap(mark_pixmap(self._size, theme.token(self._role)))


__all__ = ["BrandMark", "app_icon", "mark_pixmap", "resource"]
