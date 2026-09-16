from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton

from prana_core.common.languages import LANGUAGE_NAMES
from prana_core.console.command_phase import CommandPhase, CommandState, can_toggle
from prana_core.console.models import StationSummary
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.icons import phosphor_icon

_PHASE_TEXT = {
    CommandPhase.SENDING: "phase.sending",
    CommandPhase.AWAITING_STATION: "phase.awaiting",
    CommandPhase.APPLIED: "phase.applied",
    CommandPhase.FAILED: "phase.failed",
    CommandPhase.OFFLINE: "phase.offline",
    CommandPhase.VIEW_ONLY: "control.view_only",
}


class ControlBar(QFrame):
    """Start/Stop, target language and capture device for the attached Station."""

    toggle_requested = Signal(bool)
    language_changed = Signal(str)
    capture_changed = Signal(str, str)
    rescan_requested = Signal()
    retry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlBar")
        self._station: StationSummary | None = None
        self._state = CommandState()
        self._suppress = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 12)
        layout.setSpacing(12)

        self._toggle = QPushButton()
        self._toggle.setObjectName("StartStopButton")
        self._toggle.setFixedHeight(36)
        self._toggle.setIconSize(QSize(14, 14))
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle)

        self._language_label = QLabel()
        self._language_label.setObjectName("LangLabel")
        layout.addWidget(self._language_label)
        self._language = QComboBox()
        self._language.setFixedHeight(36)
        for code, name in LANGUAGE_NAMES.items():
            self._language.addItem(name, code)
        self._language.currentIndexChanged.connect(self._on_language)
        layout.addWidget(self._language)

        self._mode_label = QLabel()
        self._mode_label.setObjectName("LangLabel")
        layout.addWidget(self._mode_label)
        self._mode = QComboBox()
        self._mode.setFixedHeight(36)
        self._mode.currentIndexChanged.connect(self._on_capture)
        layout.addWidget(self._mode)

        self._device_label = QLabel()
        self._device_label.setObjectName("LangLabel")
        layout.addWidget(self._device_label)
        self._device = QComboBox()
        self._device.setFixedHeight(36)
        self._device.setMinimumWidth(220)
        self._device.currentIndexChanged.connect(self._on_capture)
        layout.addWidget(self._device, stretch=1)

        self._rescan = QPushButton()
        self._rescan.setCursor(Qt.PointingHandCursor)
        self._rescan.clicked.connect(self.rescan_requested)
        layout.addWidget(self._rescan)

        self._phase = QLabel()
        self._phase.setObjectName("PhaseLabel")
        layout.addWidget(self._phase)

        self._retry = QPushButton()
        self._retry.setCursor(Qt.PointingHandCursor)
        self._retry.clicked.connect(self.retry_requested)
        self._retry.setVisible(False)
        layout.addWidget(self._retry)

        language.changed.connect(self._retranslate)
        self._retranslate()

    # -- input ------------------------------------------------------------

    def _on_toggle(self) -> None:
        if self._station is not None:
            self.toggle_requested.emit(not self._station.desired.running)

    def _on_language(self) -> None:
        if not self._suppress:
            self.language_changed.emit(self._language.currentData())

    def _on_capture(self) -> None:
        if not self._suppress:
            self.capture_changed.emit(
                self._mode.currentData() or "device",
                self._device.currentData() or "",
            )

    # -- state ------------------------------------------------------------

    def set_station(self, station: StationSummary) -> None:
        self._station = station
        self._suppress = True
        index = self._language.findData(station.desired.target_language)
        if index >= 0:
            self._language.setCurrentIndex(index)

        capabilities = station.capabilities
        modes = list(capabilities.capture_modes) if capabilities else ["device"]
        if [self._mode.itemData(i) for i in range(self._mode.count())] != modes:
            self._mode.clear()
            for mode in modes:
                self._mode.addItem(mode, mode)
        mode_index = self._mode.findData(station.desired.capture_mode)
        if mode_index >= 0:
            self._mode.setCurrentIndex(mode_index)

        active_mode = self._mode.currentData() or "device"
        devices = capabilities.devices_for(active_mode) if capabilities else ()
        wanted = [device.id for device in devices]
        if [self._device.itemData(i) for i in range(self._device.count())] != wanted:
            self._device.clear()
            for device in devices:
                self._device.addItem(device.name or device.id, device.id)
        device_index = self._device.findData(station.desired.audio_device_id)
        if device_index >= 0:
            self._device.setCurrentIndex(device_index)
        self._suppress = False
        self._refresh()

    def set_state(self, state: CommandState) -> None:
        self._state = state
        self._refresh()

    def _refresh(self) -> None:
        station = self._station
        if station is None:
            return
        running = station.desired.running
        enabled = can_toggle(self._state, station, datetime.now(timezone.utc))
        self._toggle.setEnabled(enabled)
        self._toggle.setText(tr("header.stop") if running else tr("header.start"))
        self._toggle.setProperty("mode", "stop" if running else "start")
        self._toggle.setIcon(
            phosphor_icon(
                "ph.stop" if running else "ph.play",
                color="#2D2106" if running else "#081012",
                active_color="#2D2106" if running else "#081012",
                scale_factor=0.9,
            )
        )
        self._toggle.style().unpolish(self._toggle)
        self._toggle.style().polish(self._toggle)

        view_only = self._state.phase == CommandPhase.VIEW_ONLY
        for widget in (self._language, self._mode, self._device, self._rescan):
            widget.setEnabled(not view_only and not self._state.busy)

        key = _PHASE_TEXT.get(self._state.phase)
        self._phase.setText(tr(key) if key else "")
        self._phase.setProperty("phase", self._state.phase.value)
        self._phase.style().unpolish(self._phase)
        self._phase.style().polish(self._phase)
        self._retry.setVisible(self._state.phase == CommandPhase.FAILED)

    def _retranslate(self, *_args) -> None:
        self._language_label.setText(tr("language.output"))
        self._mode_label.setText(tr("station.capture_mode"))
        self._device_label.setText(tr("station.capture_device"))
        self._rescan.setText(tr("station.rescan_devices"))
        self._retry.setText(tr("common.retry"))
        if self._station is not None:
            self._refresh()


__all__ = ["ControlBar"]
