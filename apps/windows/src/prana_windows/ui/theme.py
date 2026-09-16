"""Design tokens and the light/dark switch.

The desktop console and the Flutter app are one product, so they share one
brand language. The values here come from the Flutter app:

  * `apps/android/lib/core/theme.dart` — the product surface (navy chrome, pale
    canvas, bordered cards).
  * `apps/android/lib/features/station/radio/presentation/widgets/console_palette.dart`
    — the Live VHF console, which is a flat instrument panel. Its own comment
    states the rule: "There are no card borders or radii."
  * `services/prana_admin/static/admin.css` `:root` — the roles Flutter
    generates from a Material 3 seed and never writes down (hover, disabled,
    selection, table chrome). It is the only hand-authored expansion of this
    palette in the repo, so it is the honest source for them.

Two desktop surfaces follow from that split: the fleet and account pages are a
product surface; the attached-Station workspace is a console.

Qt Style Sheets have no variables, so `styles.qss` is a `string.Template` and
this module supplies the substitutions. Re-applying a stylesheet to a live
QApplication restyles widgets already on screen, which is why switching themes
here does not rebuild anything -- the same property `language.changed` relies
on in `i18n.py`.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette

# Accessibility notes, measured rather than assumed:
#   `transmit` on the dark console panel is 3.48:1 and `text_muted` on the light
#   canvas is 4.27:1 -- both below 4.5:1. The Flutter app only uses them for
#   dots, borders and bold uppercase labels, where the 3:1 threshold applies.
#   Do not move them onto small body text; every other pair here is >= 4.6:1.

LIGHT: dict[str, str] = {
    # Product surface
    "canvas": "#F2F7FC",
    "surface": "#FFFFFF",
    "surface_muted": "#F7FAFD",
    "surface_strong": "#EAF2FB",
    "surface_sunken": "#EAF2FB",
    "border": "#D4E2E5",
    "border_strong": "#B9CDD2",
    "divider": "#DCE7F1",
    "text": "#0D2B4F",
    "text_secondary": "#355762",
    "text_muted": "#607983",
    "text_disabled": "#9AAAB4",
    "navy": "#0D2B4F",
    "navy_soft": "#173B63",
    "accent": "#123F7E",
    "accent_hover": "#0D2B4F",
    "accent_soft": "#EAF2FB",
    "on_accent": "#FFFFFF",
    # Console surface
    "console_bg": "#F2F7FC",
    "console_panel": "#FFFFFF",
    "hairline": "#D4E2E5",
    "console_accent": "#0B7285",
    "on_console_accent": "#FFFFFF",
    "console_ink": "#0D2B4F",
    "console_muted": "#607983",
    # Signalling
    "transmit": "#B12F40",
    "transmit_hover": "#C63A4C",
    "on_transmit": "#FFFFFF",
    "ok": "#21835A",
    "ok_soft": "#E3F4EB",
    # Stop-RX is amber, NOT `transmit`. The Flutter console reuses red for
    # "STOP CAPTURE" and for a held PTT, which puts one colour on "stop
    # receiving" and on "transmit on a live marine channel". Those two have
    # very different consequences, so the desktop keeps them apart.
    "stop": "#F4B942",
    "stop_hover": "#FFC957",
    "on_stop": "#2D2106",
    "warn_bg": "#FFF3D8",
    "warn_text": "#6D4A00",
    "warn_icon": "#9A6700",
    "error_bg": "#F9E1E5",
    "error_text": "#A42A3A",
    "neutral_bg": "#EDF0F2",
    "neutral_text": "#72838B",
    # Controls
    "input_bg": "#FFFFFF",
    "input_border": "#B9CDD2",
    "focus": "#123F7E",
    "selection_bg": "#EAF2FB",
    "selection_text": "#0D2B4F",
    "button_bg": "#FFFFFF",
    "button_hover": "#EAF2FB",
    "button_pressed": "#DCE7F1",
    "button_disabled_bg": "#F7FAFD",
    "scrollbar": "#B9CDD2",
    "scrollbar_hover": "#355D87",
    "table_alt": "#F7FAFD",
    "gridline": "#DCE7F1",
    "tooltip_bg": "#0D2B4F",
    "tooltip_text": "#FFFFFF",
}

DARK: dict[str, str] = {
    # Product surface
    "canvas": "#08141F",
    "surface": "#102536",
    "surface_muted": "#0C1C2A",
    "surface_strong": "#173B63",
    "surface_sunken": "#0C1C2A",
    "border": "#345064",
    "border_strong": "#496579",
    "divider": "#345064",
    "text": "#E0EEF7",
    "text_secondary": "#C2D6E4",
    "text_muted": "#8AA4B8",
    "text_disabled": "#718591",
    "navy": "#081F3A",
    "navy_soft": "#123048",
    "accent": "#91C3FF",
    "accent_hover": "#B6D8FF",
    "accent_soft": "#173B63",
    "on_accent": "#00315F",
    # Console surface
    "console_bg": "#04101C",
    "console_panel": "#071A2B",
    "hairline": "#123048",
    "console_accent": "#35D6F0",
    "on_console_accent": "#04101C",
    "console_ink": "#E0EEF7",
    "console_muted": "#8AA4B8",
    # Signalling
    "transmit": "#C33F4F",
    "transmit_hover": "#D95464",
    "on_transmit": "#FFFFFF",
    "ok": "#3FD69A",
    "ok_soft": "#12372A",
    "stop": "#E3B341",
    "stop_hover": "#F0CE87",
    "on_stop": "#2D2106",
    "warn_bg": "#3A2C0C",
    "warn_text": "#F0CE87",
    "warn_icon": "#E3B341",
    "error_bg": "#3A1A20",
    "error_text": "#FFB2BA",
    "neutral_bg": "#1A2C3C",
    "neutral_text": "#8AA4B8",
    # Controls
    "input_bg": "#132A3B",
    "input_border": "#496579",
    "focus": "#4E8FD5",
    "selection_bg": "#173B63",
    "selection_text": "#E0EEF7",
    "button_bg": "#132A3B",
    "button_hover": "#1B3A52",
    "button_pressed": "#0C1C2A",
    "button_disabled_bg": "#0C1C2A",
    "scrollbar": "#345064",
    "scrollbar_hover": "#496579",
    "table_alt": "#0C1C2A",
    "gridline": "#345064",
    "tooltip_bg": "#E0EEF7",
    "tooltip_text": "#0D2B4F",
}
THEMES = {"light": LIGHT, "dark": DARK}
DEFAULT_THEME = "light"


class ThemeManager(QObject):
    """Holds the active theme and re-applies the stylesheet on change.

    Deliberately shaped like `LanguageManager`: a singleton with a `changed`
    signal that widgets subscribe to, never a rebuild.
    """

    changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._name = DEFAULT_THEME
        self._app = None
        self._qss = ""

    @property
    def name(self) -> str:
        return self._name

    @property
    def tokens(self) -> dict[str, str]:
        return THEMES[self._name]

    def token(self, key: str) -> str:
        """Colour for Python-side styling, so nothing keeps a literal."""
        return self.tokens[key]

    def bind(self, app, qss_source: str, initial: str | None = None) -> None:
        """Attach to the application and paint the starting theme.

        Takes the initial theme rather than relying on a prior `set_theme`, so
        startup never emits `changed` and never writes the settings file for a
        choice the user did not make.
        """
        self._app = app
        self._qss = qss_source
        if initial in THEMES:
            self._name = initial
        self._apply()

    def set_theme(self, name: str) -> None:
        name = name if name in THEMES else DEFAULT_THEME
        if name == self._name:
            return
        self._name = name
        self._apply()
        self.changed.emit(name)

    def _apply(self) -> None:
        if self._app is None:
            return
        self._app.setStyleSheet(Template(self._qss).substitute(self.tokens))
        # QSS does not reach every native surface -- message boxes and tooltips
        # fall back to the application palette, which is light grey by default
        # and would glare in dark mode.
        self._app.setPalette(self.palette())

    def palette(self) -> QPalette:
        t = self.tokens
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(t["canvas"]))
        pal.setColor(QPalette.WindowText, QColor(t["text"]))
        pal.setColor(QPalette.Base, QColor(t["input_bg"]))
        pal.setColor(QPalette.AlternateBase, QColor(t["table_alt"]))
        pal.setColor(QPalette.Text, QColor(t["text"]))
        pal.setColor(QPalette.Button, QColor(t["button_bg"]))
        pal.setColor(QPalette.ButtonText, QColor(t["text"]))
        pal.setColor(QPalette.Highlight, QColor(t["accent"]))
        pal.setColor(QPalette.HighlightedText, QColor(t["on_accent"]))
        pal.setColor(QPalette.ToolTipBase, QColor(t["tooltip_bg"]))
        pal.setColor(QPalette.ToolTipText, QColor(t["tooltip_text"]))
        pal.setColor(QPalette.PlaceholderText, QColor(t["text_muted"]))
        pal.setColor(QPalette.Disabled, QPalette.Text, QColor(t["text_disabled"]))
        pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t["text_disabled"]))
        pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(t["text_disabled"]))
        return pal


theme = ThemeManager()


def token(key: str) -> str:
    """Module-level shorthand, mirroring `tr()` in i18n."""
    return theme.token(key)


def load_qss(path: Path) -> str:
    return path.read_text(encoding="utf-8")


__all__ = ["DARK", "DEFAULT_THEME", "LIGHT", "THEMES", "ThemeManager", "load_qss", "theme", "token"]
