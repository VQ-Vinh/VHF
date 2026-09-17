from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prana_windows.ui.components.chart import GpsPositionCard
from prana_windows.ui.components.instruments import InstrumentStrip
from prana_windows.ui.components.sim_notice import SimNotice
from prana_windows.ui.components.steering import ModeSwitch, SteeringPanel
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.simulation import (
    HISTORY_LENGTH,
    Freshness,
    SteeringState,
    TelemetryTrack,
    generate,
)

TICK_MS = 1000
# Chart beside the controls from this width, as on a tablet in landscape.
WIDE_WIDTH = 840
# The strip stays pinned above the scroll only while it leaves room below it.
PINNED_MIN_HEIGHT = 94 * 2.6


class ControlTab(QWidget):
    """The phone's Control tab: simulated telemetry, chart and helm.

    Mirrors `apps/android/lib/features/station/control/presentation/control_tab.dart`.
    Nothing on it reaches the Station; both notices say so, and the tab has no
    client to reach it with.
    """

    def __init__(self, parent=None, *, clock=time.monotonic):
        super().__init__(parent)
        self.setObjectName("ControlTab")
        # A QWidget subclass paints its stylesheet background only when asked.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._clock = clock
        self._origin = clock()
        self._wall_origin = datetime.now(timezone.utc)
        self.steering = SteeringState()
        self.track = TelemetryTrack()

        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Caption and strip travel together between the pinned slot and the top
        # of the scrolling content.
        self.instruments = QWidget()
        instruments = QVBoxLayout(self.instruments)
        instruments.setContentsMargins(0, 0, 0, 0)
        instruments.setSpacing(6)
        self._caption = QLabel()
        self._caption.setObjectName("ControlCaption")
        instruments.addWidget(self._caption)
        self.strip = InstrumentStrip()
        instruments.addWidget(self.strip)

        self._pinned_slot = QVBoxLayout()
        self._pinned_slot.setContentsMargins(28, 14, 28, 0)
        root.addLayout(self._pinned_slot)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ControlScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("ControlContent")
        self._content = QVBoxLayout(content)
        self._content.setContentsMargins(28, 14, 28, 20)
        self._content.setSpacing(20)
        self._scroll_slot = QVBoxLayout()
        self._content.addLayout(self._scroll_slot)

        self.gps = GpsPositionCard()
        self.controls = QWidget()
        controls = QVBoxLayout(self.controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(12)
        self.mode = ModeSwitch()
        self.mode.mode_selected.connect(self._select_mode)
        controls.addWidget(self.mode)
        self.helm = SteeringPanel(self.steering)
        controls.addWidget(self.helm)
        self.control_notice = SimNotice("link-off")
        controls.addWidget(self.control_notice)
        controls.addStretch(1)

        self._main = QGridLayout()
        self._main.setSpacing(24)
        self._content.addLayout(self._main)

        self.footer = QFrame()
        self.footer.setObjectName("TelemetryFooter")
        footer = QHBoxLayout(self.footer)
        footer.setContentsMargins(0, 10, 0, 0)
        self.status = QLabel()
        self.status.setObjectName("FooterText")
        self.sample_time = QLabel()
        self.sample_time.setObjectName("FooterText")
        footer.addWidget(self.status, 1)
        footer.addWidget(self.sample_time)
        self._content.addWidget(self.footer)
        self._content.addStretch(1)

        self.scroll.setWidget(content)
        self.scroll.verticalScrollBar().rangeChanged.connect(self._match_gutter)
        root.addWidget(self.scroll, 1)

        self._wide: bool | None = None
        self._pinned: bool | None = None
        self._apply_layout(1180, 820)
        language.changed.connect(self._retranslate)
        self._retranslate()
        self._render()

    # -- layout -----------------------------------------------------------

    def is_wide(self) -> bool:
        return bool(self._wide)

    def is_pinned(self) -> bool:
        return bool(self._pinned)

    def _apply_layout(self, width: int, height: int) -> None:
        available = width - 56  # less the 28px gutter either side
        wide = width >= WIDE_WIDTH
        pinned = InstrumentStrip.fits_one_row(available) and height >= PINNED_MIN_HEIGHT
        self.strip.set_one_row(InstrumentStrip.fits_one_row(available))

        if pinned != self._pinned:
            self._pinned = pinned
            slot = self._pinned_slot if pinned else self._scroll_slot
            slot.addWidget(self.instruments)

        if wide != self._wide:
            self._wide = wide
            for widget in (self.gps, self.controls):
                self._main.removeWidget(widget)
            # Top-aligned: the helm column is taller, and a vertically centred
            # chart would float halfway down beside it.
            if wide:
                self._main.addWidget(self.gps, 0, 0, Qt.AlignTop)
                self._main.addWidget(self.controls, 0, 1, Qt.AlignTop)
                self._main.setColumnStretch(0, 2)
                self._main.setColumnStretch(1, 1)
            else:
                self._main.addWidget(self.gps, 0, 0, Qt.AlignTop)
                self._main.addWidget(self.controls, 1, 0, Qt.AlignTop)
                self._main.setColumnStretch(0, 1)
                self._main.setColumnStretch(1, 0)

    def _match_gutter(self, *_args) -> None:
        """End the pinned strip where the scrolling cards end.

        A visible scrollbar narrows only the scrolling column, which left the
        strip overhanging the chart and helm below it by the bar's width.
        """
        bar = self.scroll.verticalScrollBar()
        extra = bar.sizeHint().width() if bar.maximum() > 0 else 0
        self._pinned_slot.setContentsMargins(28, 14, 28 + extra, 0)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._apply_layout(event.size().width(), event.size().height())
        super().resizeEvent(event)

    # -- simulation -------------------------------------------------------

    def _elapsed(self) -> float:
        return max(0.0, self._clock() - self._origin)

    def _sample_at(self, elapsed: float):
        return generate(elapsed, self._wall_origin + timedelta(seconds=elapsed))

    def tick(self) -> None:
        self.track.push(self._sample_at(self._elapsed()))
        self._render()

    def _backfill(self) -> None:
        """Rebuild the recent track so returning to the tab shows no gap.

        The generator is deterministic, so the fixes the hidden tab skipped are
        exactly the ones it would have drawn.
        """
        elapsed = self._elapsed()
        self.track.clear()
        for back in range(HISTORY_LENGTH - 1, 0, -1):
            if elapsed - back >= 0:
                self.track.push(self._sample_at(elapsed - back))
        self.tick()

    def reset(self) -> None:
        """A different Station: a fresh helm and a fresh track."""
        self.steering.reset()
        self.mode.set_mode(self.steering.mode)
        self.helm.refresh()
        self._origin = self._clock()
        self._wall_origin = datetime.now(timezone.utc)
        self.track.clear()
        if self.isVisible():
            self.tick()
        else:
            self._render()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._backfill()
        self.timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        # Only the visible tab ticks; a hidden chart repainting every second
        # would cost the operator's machine for nothing.
        self.timer.stop()
        self.helm.wheel.end_drag()
        super().hideEvent(event)

    def _select_mode(self, mode) -> None:
        self.steering.select_mode(mode)
        self.mode.set_mode(mode)
        self.helm.refresh()

    # -- rendering --------------------------------------------------------

    def _render(self) -> None:
        sample = self.track.snapshot
        self.strip.set_snapshot(sample)
        self.gps.set_data(sample, [(s.latitude, s.longitude) for s in self.track.history])
        freshness = self.track.freshness(datetime.now(timezone.utc))
        self.status.setText(tr(f"sim.{freshness.value}"))
        self.sample_time.setText(
            "" if sample is None else sample.timestamp.astimezone().strftime("%H:%M:%S")
        )

    def freshness(self) -> Freshness:
        return self.track.freshness(datetime.now(timezone.utc))

    def _retranslate(self, *_args) -> None:
        self._caption.setText(tr("sim.telemetry"))
        self.control_notice.set_text(tr("sim.control_notice"))
        self._render()


__all__ = ["ControlTab"]
