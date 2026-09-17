"""The desktop Control tab: the phone's simulated helm and telemetry.

The pure rules mirror apps/android/test/control_test.dart and
telemetry_instruments_test.dart, so both apps are held to the same numbers.
"""

from __future__ import annotations

import math
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from prana_windows.ui import simulation as sim
    from prana_windows.ui.i18n import language
    from prana_windows.ui.pages.control_tab import ControlTab
    from prana_windows.ui.pages.station_workspace import StationWorkspacePage
    from prana_windows.ui.theme import load_qss, theme, token
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    if not (exc.name or "").startswith("PySide6"):
        raise
    QApplication = None  # type: ignore[assignment]

UI = Path("apps/windows/src/prana_windows/ui")
QSS = UI / "resources" / "styles.qss"
SIMULATION_MODULES = [
    UI / "simulation.py",
    UI / "pages" / "control_tab.py",
    UI / "components" / "chart.py",
    UI / "components" / "instruments.py",
    UI / "components" / "steering.py",
    UI / "components" / "sim_notice.py",
]
T0 = datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc)


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class SimulationRuleTests(unittest.TestCase):
    def test_generator_matches_the_phone_and_is_deterministic(self) -> None:
        first = sim.generate(0, T0)
        self.assertAlmostEqual(first.speed_knots, 10.2)
        self.assertAlmostEqual(first.depth_metres, 8.2)
        self.assertAlmostEqual(first.heading_degrees, 315)
        self.assertAlmostEqual(first.latitude, 10.7623)
        self.assertAlmostEqual(first.longitude, 106.6511)
        self.assertEqual(sim.generate(42.5, T0), sim.generate(42.5, T0))
        later = sim.generate(60, T0)
        self.assertNotEqual(
            sim.chart_point(first.latitude, first.longitude, 600, 300),
            sim.chart_point(later.latitude, later.longitude, 600, 300),
        )
        # Heading stays a bearing even where the sine pulls it below zero.
        self.assertTrue(all(0 <= sim.generate(s, T0).heading_degrees < 360 for s in range(0, 400, 7)))

    def test_steering_clamps_to_the_range_the_scale_shows(self) -> None:
        state = sim.SteeringState()
        for _ in range(50):
            state.adjust(sim.NUDGE_DEGREES)
        self.assertEqual(state.angle, 180)
        state.adjust(-500)
        self.assertEqual(state.angle, -180)
        self.assertEqual(sim.rudder_fraction(900), 1)
        self.assertEqual(sim.rudder_fraction(-90), -0.5)

    def test_auto_centres_the_helm_and_ignores_input(self) -> None:
        state = sim.SteeringState()
        state.adjust(35)
        state.select_mode(sim.ControlMode.AUTO)
        self.assertEqual(state.angle, 0)
        state.adjust(10)
        state.begin_drag(0.0)
        state.drag(1.0)
        state.center()
        self.assertEqual(state.angle, 0)

    def test_dragging_across_due_west_does_not_spin_a_full_turn(self) -> None:
        state = sim.SteeringState()
        state.begin_drag(math.pi - 0.05)
        state.drag(-math.pi + 0.05)  # 0.1 rad clockwise across the seam
        self.assertAlmostEqual(state.angle, math.degrees(0.1), places=6)
        state.end_drag()
        state.drag(0.0)
        self.assertAlmostEqual(state.angle, math.degrees(0.1), places=6)

    def test_a_fix_reads_in_dms_and_never_with_a_minus(self) -> None:
        self.assertEqual(sim.format_dms(10.99999, positive="N", negative="S"), "11°00'00\"N")
        self.assertEqual(sim.format_dms(-33.5, positive="N", negative="S"), "33°30'00\"S")
        self.assertEqual(sim.format_dms(-0.0001, positive="E", negative="W"), "0°00'00\"W")
        self.assertNotIn("-", sim.format_dms(-122.25, positive="E", negative="W"))

    def test_compass_points_and_directions(self) -> None:
        self.assertEqual(sim.compass_point(315), "NW")
        self.assertEqual(sim.compass_point(22.5), "NE")  # halves round up, as in Dart
        self.assertEqual(sim.compass_point(-10), "N")
        self.assertEqual(sim.direction(0.4), "straight")
        self.assertEqual(sim.direction(-3), "left")
        self.assertEqual(sim.direction(3), "right")

    def test_track_is_capped_and_goes_stale(self) -> None:
        track = sim.TelemetryTrack()
        self.assertIs(track.freshness(T0), sim.Freshness.MISSING)
        for second in range(55):
            track.push(sim.generate(second, T0 + timedelta(seconds=second)))
        self.assertEqual(len(track.history), sim.HISTORY_LENGTH)
        last = track.snapshot.timestamp
        self.assertIs(track.freshness(last + timedelta(seconds=5)), sim.Freshness.FRESH)
        self.assertIs(track.freshness(last + timedelta(seconds=6)), sim.Freshness.STALE)

    def test_track_breaks_where_the_chart_rebases(self) -> None:
        # Straddle a cell boundary: the marker jumps back across the chart.
        fixes = [(10.7623, 106.6505 + sim.CHART_CELL - 0.0001), (10.7623, 106.6505 + sim.CHART_CELL + 0.0001)]
        self.assertEqual(sim.track_segments(fixes, 600, 300), [])
        near = [(10.7623, 106.6511), (10.76231, 106.65111), (10.76232, 106.65112)]
        self.assertEqual(len(sim.track_segments(near, 600, 300)), 1)

    def test_the_simulation_has_no_path_to_a_station(self) -> None:
        """Mirrors the Flutter dependency-boundary test: no client, no API."""
        for path in SIMULATION_MODULES:
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertNotIn("prana_core.console", source)
                self.assertNotIn("prana_core.backend", source)
                self.assertNotIn("station_client", source)

    def test_painted_colours_come_from_the_theme(self) -> None:
        """A literal colour in a paintEvent would ignore the light/dark switch."""
        literal = re.compile(r"QColor\(\s*[\"'#\d]|Qt\.(white|black|red|green|blue|gray|yellow)\b")
        offenders = [
            str(path)
            for path in UI.rglob("*.py")
            if path.name != "theme.py" and literal.search(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [])


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ControlTabWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        theme.bind(cls.app, load_qss(QSS), "light")

    def tearDown(self) -> None:
        theme.set_theme("light")
        language.set_locale("en")

    def _tab(self) -> tuple["ControlTab", list[float]]:
        now = [1000.0]
        tab = ControlTab(clock=lambda: now[0])
        return tab, now

    def test_workspace_has_control_then_live_and_opens_on_live(self) -> None:
        page = StationWorkspacePage()
        self.assertEqual(list(page.tab_buttons), ["control", "live"])
        self.assertEqual(page.current_tab(), "live")
        self.assertEqual(page.tab_buttons["live"].property("current"), "true")
        self.assertEqual(page.tab_buttons["control"].text(), "Control")
        self.assertEqual(page.tab_buttons["live"].text(), "Live VHF")
        page.close()

    def test_switching_tabs_rebuilds_nothing(self) -> None:
        page = StationWorkspacePage()
        parts = (page.chat, page.control_bar, page.tx_panel, page.control_tab)
        page.show_tab("control")
        self.assertEqual(page.current_tab(), "control")
        self.assertIs(page._pages.currentWidget(), page.control_tab)
        self.assertEqual(page.tab_buttons["control"].property("current"), "true")
        self.assertEqual(page.tab_buttons["live"].property("current"), "false")
        page.show_tab("live")
        self.assertEqual((page.chat, page.control_bar, page.tx_panel, page.control_tab), parts)
        page.show_tab("nonsense")
        self.assertEqual(page.current_tab(), "live")
        page.close()

    def test_attaching_again_returns_to_live_with_a_fresh_helm(self) -> None:
        page = StationWorkspacePage()
        page.show_tab("control")
        page.control_tab.steering.adjust(40)
        page.control_tab._select_mode(sim.ControlMode.AUTO)
        page.reset()
        self.assertEqual(page.current_tab(), "live")
        self.assertIs(page.control_tab.steering.mode, sim.ControlMode.MANUAL)
        self.assertEqual(page.control_tab.steering.angle, 0)
        self.assertEqual(page.control_tab.mode.buttons[sim.ControlMode.MANUAL].property("selected"), "true")
        page.close()

    def test_auto_locks_the_helm_and_manual_nudges_by_five(self) -> None:
        tab, _now = self._tab()
        helm = tab.helm
        helm.right.click()
        helm.right.click()
        helm.left.click()
        self.assertEqual(tab.steering.angle, 5)
        self.assertEqual(helm.angle.text(), "5°")
        self.assertEqual(helm.direction.text(), "Right")

        tab.mode.buttons[sim.ControlMode.AUTO].click()
        self.assertEqual(tab.steering.angle, 0)
        for widget in (helm.wheel, helm.left, helm.right, helm.center):
            self.assertFalse(widget.isEnabled())
        self.assertFalse(helm.auto_note.isHidden())
        self.assertEqual(helm.chip.property("manual"), "false")
        self.assertEqual(tab.mode.buttons[sim.ControlMode.AUTO].property("selected"), "true")

        tab.mode.buttons[sim.ControlMode.MANUAL].click()
        self.assertTrue(helm.wheel.isEnabled())
        self.assertTrue(helm.auto_note.isHidden())
        tab.close()

    def test_readout_never_shows_negative_zero(self) -> None:
        tab, _now = self._tab()
        tab.steering.angle = -0.2
        tab.helm.refresh()
        self.assertEqual(tab.helm.angle.text(), "0°")
        tab.steering.angle = -2.5
        tab.helm.refresh()
        self.assertEqual(tab.helm.angle.text(), "-3°")
        tab.close()

    def test_dragging_the_rim_turns_the_wheel_but_the_hub_does_not(self) -> None:
        tab, _now = self._tab()
        wheel = tab.helm.wheel
        wheel.resize(280, 280)
        centre = QPoint(140, 140)

        QTest.mousePress(wheel, Qt.LeftButton, Qt.NoModifier, centre)
        QTest.mouseMove(wheel, QPoint(140, 40))
        QTest.mouseRelease(wheel, Qt.LeftButton, Qt.NoModifier, QPoint(140, 40))
        self.assertEqual(tab.steering.angle, 0)

        QTest.mousePress(wheel, Qt.LeftButton, Qt.NoModifier, QPoint(140, 40))  # 12 o'clock
        QTest.mouseMove(wheel, QPoint(240, 140))  # 3 o'clock: a quarter turn clockwise
        QTest.mouseRelease(wheel, Qt.LeftButton, Qt.NoModifier, QPoint(240, 140))
        self.assertAlmostEqual(tab.steering.angle, 90, places=3)
        self.assertEqual(tab.helm.angle.text(), "90°")

        QTest.keyClick(wheel, Qt.Key_Left)
        self.assertAlmostEqual(tab.steering.angle, 85, places=3)
        tab.close()

    def test_only_the_visible_tab_ticks_and_it_returns_with_its_track(self) -> None:
        tab, now = self._tab()
        tab.resize(1180, 820)
        self.assertFalse(tab.timer.isActive())
        now[0] += 120
        tab.show()
        self.app.processEvents()
        self.assertTrue(tab.timer.isActive())
        self.assertEqual(len(tab.track.history), sim.HISTORY_LENGTH)
        self.assertIs(tab.freshness(), sim.Freshness.FRESH)
        self.assertNotEqual(tab.strip.speed.value_text(), "—")
        self.assertEqual(tab.gps.source.text(), "SIMULATED")
        self.assertEqual(tab.status.text(), "Simulated telemetry — updating")

        tab.hide()
        self.app.processEvents()
        self.assertFalse(tab.timer.isActive())
        tab.close()

    def test_layout_puts_the_chart_beside_the_helm_only_when_wide(self) -> None:
        tab, _now = self._tab()
        tab.resize(1180, 820)
        tab.show()
        self.app.processEvents()
        self.assertTrue(tab.is_wide())
        self.assertTrue(tab.is_pinned())
        tab.resize(700, 820)
        self.app.processEvents()
        self.assertFalse(tab.is_wide())
        tab.resize(700, 200)
        self.app.processEvents()
        self.assertFalse(tab.is_pinned())
        tab.close()

    def test_language_switch_relabels_without_rebuilding(self) -> None:
        tab, _now = self._tab()
        helm, strip = tab.helm, tab.strip
        language.set_locale("vi")
        self.assertIs(tab.helm, helm)
        self.assertIs(tab.strip, strip)
        self.assertEqual(tab.helm._title.text(), "Vô lăng mô phỏng")
        self.assertEqual(tab.mode.buttons[sim.ControlMode.AUTO].text(), "Tự động")
        self.assertEqual(tab.control_notice.text(), "Mô phỏng — chưa kết nối phần cứng")
        self.assertEqual(tab.gps.notice.text(), "Mô phỏng — không dùng dẫn đường")
        tab.close()

    def test_painted_parts_read_the_theme_at_paint_time(self) -> None:
        """Colours are looked up when painting, never captured at construction.

        (Whether a visible widget repaints is Qt's job: re-applying the app
        stylesheet on a switch already repaints every widget.)
        """
        tab, _now = self._tab()
        tab.resize(1180, 820)
        tab.show()
        self.app.processEvents()
        chart = tab.gps.chart
        # Mid-cell and above the first grid line: plain chart background.
        corner = QPoint(int(20 + (chart.width() - 40) * 3.5 / 6), 3)

        def background() -> str:
            return chart.grab().toImage().pixelColor(corner).name().upper()

        before = background()
        self.assertEqual(before, token("surface_sunken").upper())
        theme.set_theme("dark")
        self.app.processEvents()
        self.assertIs(tab.gps.chart, chart)
        self.assertEqual(background(), token("surface_sunken").upper())
        self.assertNotEqual(background(), before)
        tab.close()


if __name__ == "__main__":
    unittest.main()
