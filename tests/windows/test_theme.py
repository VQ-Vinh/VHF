from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from string import Template
from unittest.mock import patch

UI = Path("apps/windows/src/prana_windows/ui")
QSS = UI / "resources" / "styles.qss"

try:
    from PySide6.QtWidgets import QApplication

    from prana_windows.ui.theme import DARK, LIGHT, THEMES, load_qss, theme
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    if not (exc.name or "").startswith("PySide6"):
        raise
    QApplication = None  # type: ignore[assignment]
    DARK = LIGHT = THEMES = None  # type: ignore[assignment]
    load_qss = theme = None  # type: ignore[assignment]


def _luminance(value: str) -> float:
    value = value.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Text sits on these backgrounds, so each pair must clear WCAG AA (4.5:1) in both
# themes -- the same guarantee apps/android/test/theme_mode_test.dart pins.
TEXT_PAIRS = [
    ("text", "canvas"),
    ("text", "surface"),
    ("text_secondary", "surface"),
    ("on_accent", "accent"),
    ("on_transmit", "transmit"),
    ("on_stop", "stop"),
    ("console_ink", "console_panel"),
    ("console_muted", "console_panel"),
    ("on_console_accent", "console_accent"),
    ("warn_text", "warn_bg"),
    ("error_text", "error_bg"),
    ("ok", "surface"),
    ("tooltip_text", "tooltip_bg"),
    # Control tab: captions on the page, pills and notices, the selected chip.
    ("text_secondary", "console_bg"),
    ("text_secondary", "surface_sunken"),
    ("text_secondary", "warn_bg"),
    ("accent", "accent_soft"),
]


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ThemeTokenTests(unittest.TestCase):
    def test_both_themes_define_exactly_the_same_tokens(self) -> None:
        """A token missing from one theme is a stylesheet that silently breaks."""
        self.assertEqual(set(LIGHT), set(DARK))

    def test_every_token_is_a_six_digit_hex_colour(self) -> None:
        for name, tokens in THEMES.items():
            for key, value in tokens.items():
                with self.subTest(theme=name, token=key):
                    self.assertRegex(value, r"^#[0-9A-Fa-f]{6}$")

    def test_stylesheet_substitutes_cleanly_for_every_theme(self) -> None:
        """`substitute` raises on any unknown placeholder, typo or stray dollar-brace."""
        template = Template(load_qss(QSS))
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                rendered = template.substitute(tokens)
                self.assertNotIn("${", rendered)

    def test_stylesheet_contains_no_hex_literals(self) -> None:
        """Colours live in theme.py. A literal here would ignore the theme switch."""
        literals = re.findall(r"#[0-9A-Fa-f]{6}\b", load_qss(QSS))
        self.assertEqual(literals, [])

    def test_text_pairs_meet_wcag_aa_in_both_themes(self) -> None:
        for name, tokens in THEMES.items():
            for foreground, background in TEXT_PAIRS:
                with self.subTest(theme=name, pair=f"{foreground}/{background}"):
                    ratio = _contrast(tokens[foreground], tokens[background])
                    self.assertGreaterEqual(ratio, 4.5, f"{ratio:.2f}:1")

    def test_stop_rx_is_never_the_transmit_colour(self) -> None:
        """Stopping reception and keying a transmitter must not look alike."""
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                self.assertNotEqual(tokens["stop"], tokens["transmit"])

    def test_only_the_theme_module_sets_a_stylesheet(self) -> None:
        """A widget-level stylesheet is baked at one colour and ignores the switch."""
        offenders = [
            str(path)
            for path in UI.rglob("*.py")
            if path.name != "theme.py" and "setStyleSheet" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])

    def test_every_dynamic_property_the_ui_sets_is_styled(self) -> None:
        """Properties that drive colour must have a rule, or a restyle drops them.

        Properties used purely as test or routing plumbing are exempt.
        """
        plumbing = {"device_id", "plan_id", "field"}
        names = set()
        for path in UI.rglob("*.py"):
            names.update(re.findall(r'setProperty\(\s*"(\w+)"', path.read_text(encoding="utf-8")))
        qss = load_qss(QSS)
        missing = sorted(n for n in names - plumbing if f"[{n}=" not in qss)
        self.assertEqual(missing, [])


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ThemeSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        theme.bind(cls.app, load_qss(QSS), "light")

    def tearDown(self) -> None:
        theme.set_theme("light")

    def test_switching_restyles_without_rebuilding_widgets(self) -> None:
        from prana_windows.ui.pages.fleet import FleetPage

        page = FleetPage()
        before = [id(child) for child in page.findChildren(object)]
        theme.set_theme("dark")
        self.app.processEvents()
        after = [id(child) for child in page.findChildren(object)]
        self.assertEqual(before, after)
        self.assertEqual(
            self.app.palette().color(self.app.palette().ColorRole.Window).name().upper(),
            DARK["canvas"],
        )
        page.close()

    def test_switch_emits_once_and_ignores_repeats_and_unknown_names(self) -> None:
        from PySide6.QtTest import QSignalSpy

        spy = QSignalSpy(theme.changed)
        theme.set_theme("dark")
        theme.set_theme("dark")
        theme.set_theme("purple")  # falls back to light: a real change
        self.assertEqual(spy.count(), 2)
        self.assertEqual(theme.name, "light")

    def test_theme_toggle_rebakes_its_icon(self) -> None:
        """Icons are pixmaps at a fixed colour; this is the bug no stylesheet catches."""
        from prana_windows.ui.components.theme_toggle import ThemeToggle

        toggle = ThemeToggle()
        light = toggle.icon().pixmap(18, 18).toImage()
        theme.set_theme("dark")
        dark = toggle.icon().pixmap(18, 18).toImage()
        self.assertNotEqual(light, dark)
        toggle.close()


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ThemedIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        theme.bind(cls.app, load_qss(QSS), "light")

    def tearDown(self) -> None:
        theme.set_theme("light")

    @staticmethod
    def _image(button):
        return button.icon().pixmap(18, 18).toImage()

    def test_material_glyphs_load_from_the_pinned_font(self) -> None:
        """Guards the explicit, version-stamped font and charmap filenames."""
        from prana_windows.ui.icons import themed_icon

        for name in ("radio", "play", "stop", "history", "eye-outline",
                     "account-circle-outline", "weather-night", "white-balance-sunny"):
            with self.subTest(glyph=name):
                self.assertFalse(themed_icon(name).pixmap(18, 18).isNull())

    def test_bound_icons_are_rebaked_when_the_theme_changes(self) -> None:
        from PySide6.QtWidgets import QPushButton

        from prana_windows.ui.icons import bind_icon

        button = QPushButton()
        bind_icon(button, "radio", role="text")
        light = self._image(button)
        theme.set_theme("dark")
        self.assertNotEqual(light, self._image(button))
        button.close()

    def test_a_deleted_widget_does_not_break_the_next_theme_switch(self) -> None:
        """Rows and bubbles come and go constantly; the registry must let them."""
        import shiboken6
        from PySide6.QtWidgets import QPushButton

        from prana_windows.ui.icons import bind_icon

        doomed = QPushButton()
        bind_icon(doomed, "history")
        shiboken6.delete(doomed)
        theme.set_theme("dark")  # must not raise on the deleted C++ object
        theme.set_theme("light")

    def test_start_stop_icon_follows_the_theme(self) -> None:
        from prana_core.console.models import StationSummary
        from prana_windows.ui.components.control_bar import ControlBar

        bar = ControlBar()
        bar.set_station(StationSummary.from_wire({
            "station_id": "a" * 32, "name": "S", "active": True,
            "desired_state": {"generation": 1, "running": False},
        }))
        light = self._image(bar._toggle)
        theme.set_theme("dark")
        self.assertNotEqual(light, self._image(bar._toggle))
        bar.close()


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class BrandFontTests(unittest.TestCase):
    FONTS = UI / "resources" / "fonts"

    def test_desktop_ships_the_flutter_faces_with_their_licences(self) -> None:
        """The OFL requires the licence to travel with the font files."""
        names = {path.name for path in self.FONTS.iterdir()}
        self.assertTrue({"Archivo-Medium.ttf", "Archivo-SemiBold.ttf", "Archivo-Bold.ttf",
                         "RobotoMono-Medium.ttf", "RobotoMono-Bold.ttf"} <= names)
        self.assertTrue({"Archivo-OFL.txt", "RobotoMono-OFL.txt"} <= names)

    def test_desktop_fonts_are_byte_identical_to_the_flutter_copies(self) -> None:
        """One brand, one set of glyphs -- a divergent copy would be a silent fork."""
        android = Path("apps/android/assets/fonts")
        for path in self.FONTS.glob("*.ttf"):
            with self.subTest(font=path.name):
                self.assertEqual(path.read_bytes(), (android / path.name).read_bytes())

    def test_fonts_register_under_the_families_the_stylesheet_names(self) -> None:
        """QSS says "Roboto Mono" with a space; the file is RobotoMono-*.ttf."""
        from PySide6.QtGui import QFontDatabase

        QApplication.instance() or QApplication([])
        from prana_windows.ui.app import _load_fonts

        _load_fonts()
        families = set(QFontDatabase.families())
        self.assertIn("Archivo", families)
        self.assertIn("Roboto Mono", families)
        qss = load_qss(QSS)
        self.assertIn('"Archivo"', qss)
        self.assertIn('"Roboto Mono"', qss)


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class BrandMarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        theme.bind(cls.app, load_qss(QSS), "light")

    def tearDown(self) -> None:
        theme.set_theme("light")

    def test_mark_is_recoloured_by_the_theme(self) -> None:
        from prana_windows.ui.brand import BrandMark

        mark = BrandMark(36)
        light = mark.pixmap().toImage()
        self.assertFalse(mark.pixmap().isNull())
        theme.set_theme("dark")
        self.assertNotEqual(light, mark.pixmap().toImage())
        mark.close()

    def test_fleet_header_carries_the_mark(self) -> None:
        """Mirrors apps/android/test/header_brand_test.dart for the desktop home."""
        from prana_windows.ui.brand import BrandMark
        from prana_windows.ui.pages.fleet import FleetPage

        page = FleetPage()
        self.assertEqual(len(page.findChildren(BrandMark)), 1)
        page.close()

    def test_window_and_tray_use_the_brand_icon(self) -> None:
        from prana_windows.ui.brand import app_icon

        icon = app_icon()
        self.assertFalse(icon.isNull())
        self.assertGreaterEqual(len(icon.availableSizes()), 5)


class ThemeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._env = patch.dict(
            os.environ,
            {"LOCALAPPDATA": self._tmp.name, "PROGRAMDATA": self._tmp.name + "-machine"},
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmp.cleanup()

    def test_theme_defaults_to_light_like_android(self) -> None:
        from prana_windows.settings import load_settings

        self.assertEqual(load_settings()["ui_theme"], "light")

    def test_theme_survives_saving_a_different_setting(self) -> None:
        """save_settings re-reads through a key whitelist before writing.

        If ui_theme were missing from that whitelist, changing the language
        would silently throw the user's theme away.
        """
        from prana_windows.settings import get_settings_path, load_settings, save_settings

        save_settings(ui_theme="dark")
        save_settings(ui_locale="vi")
        self.assertEqual(load_settings()["ui_theme"], "dark")
        stored = json.loads(get_settings_path().read_text(encoding="utf-8"))
        self.assertEqual(stored["ui_theme"], "dark")

    def test_unknown_theme_is_rejected(self) -> None:
        from prana_windows.settings import load_settings, save_settings

        save_settings(ui_theme="purple")
        self.assertEqual(load_settings()["ui_theme"], "light")


if __name__ == "__main__":
    unittest.main()
