from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton

from prana_windows.ui.i18n import language, tr
from prana_windows.ui.icons import themed_icon
from prana_windows.ui.theme import theme


class ThemeToggle(QPushButton):
    """Switches light/dark, beside the locale selector.

    Appearance and language are the same kind of preference, so they live in the
    same place and persist the same way.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeToggle")
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.clicked.connect(self._toggle)
        theme.changed.connect(self._retranslate)
        language.changed.connect(self._retranslate)
        self._retranslate()

    def _toggle(self) -> None:
        theme.set_theme("light" if theme.name == "dark" else "dark")

    def _retranslate(self, *_args) -> None:
        going_dark = theme.name == "light"
        label = tr("theme.dark") if going_dark else tr("theme.light")
        self.setToolTip(label)
        self.setAccessibleName(label)
        # Icons are baked at a fixed colour, so this has to be re-made whenever
        # the theme changes -- which is exactly what this handler is for.
        self.setIcon(
            themed_icon(
                "weather-night" if going_dark else "white-balance-sunny",
                role="text_secondary",
                active_role="accent",
                scale_factor=0.95,
            )
        )


__all__ = ["ThemeToggle"]
