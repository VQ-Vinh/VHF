from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from prana_elex.ui.icons import phosphor_icon


class HeaderBar(QFrame):
    settings_requested = Signal()
    toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 8)
        layout.setSpacing(10)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        self._title = QLabel("PRANA ELEX")
        self._title.setObjectName("HeaderTitle")
        self._subtitle = QLabel("MARINE VHF")
        self._subtitle.setObjectName("HeaderSubtitle")
        title_block.addWidget(self._title)
        title_block.addWidget(self._subtitle)
        layout.addLayout(title_block)
        layout.addStretch()

        self._start_stop_btn = QPushButton("Start")
        self._start_stop_btn.setObjectName("StartStopButton")
        self._start_stop_btn.setFixedHeight(34)
        self._start_stop_btn.setIconSize(QSize(14, 14))
        self._start_stop_btn.setCursor(Qt.PointingHandCursor)
        self._start_stop_btn.clicked.connect(self.toggle_requested.emit)
        layout.addWidget(self._start_stop_btn)

        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("SettingsButton")
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.setIcon(
            phosphor_icon("ph.gear", scale_factor=1.05)
        )
        self._settings_btn.setIconSize(QSize(20, 20))
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.setAccessibleName("Settings")
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self._settings_btn)

        self._rx_badge = QFrame()
        self._rx_badge.setObjectName("RxBadge")
        self._rx_badge.setFixedHeight(34)
        rx_layout = QHBoxLayout(self._rx_badge)
        rx_layout.setContentsMargins(10, 0, 12, 0)
        rx_layout.setSpacing(6)
        self._rx_dot = QLabel("●")
        self._rx_dot.setObjectName("RxDot")
        self._rx_label = QLabel("RX OFF")
        self._rx_label.setObjectName("RxLabel")
        rx_layout.addWidget(self._rx_dot)
        rx_layout.addWidget(self._rx_label)
        layout.addWidget(self._rx_badge)

        self.set_pipeline_running(False)
        self.set_rx_mode("off")

    def _refresh(self, widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def set_pipeline_running(self, running: bool) -> None:
        self._start_stop_btn.setEnabled(True)
        self._start_stop_btn.setProperty("mode", "stop" if running else "start")
        self._start_stop_btn.setText("Stop" if running else "Start")
        self._start_stop_btn.setIcon(
            phosphor_icon(
                "ph.stop" if running else "ph.play",
                color="#F2B84B" if running else "#081012",
                active_color="#F2B84B" if running else "#081012",
                scale_factor=0.9,
            )
        )
        self._refresh(self._start_stop_btn)

    def set_pipeline_transitioning(self, transitioning: bool, text: str = "") -> None:
        self._start_stop_btn.setEnabled(not transitioning)
        self._start_stop_btn.setProperty("mode", "transition" if transitioning else "start")
        self._start_stop_btn.setText(text or "Start")
        self._start_stop_btn.setIcon(
            phosphor_icon(
                "ph.hourglass" if transitioning else "ph.play",
                color="#8E8EA0" if transitioning else "#081012",
                active_color="#8E8EA0" if transitioning else "#081012",
                scale_factor=0.9,
            )
        )
        self._refresh(self._start_stop_btn)

    def set_rx_state(self, recording: bool, running: bool) -> None:
        if not running:
            self.set_rx_mode("off")
        elif recording:
            self.set_rx_mode("receiving")
        else:
            self.set_rx_mode("active")

    def set_rx_mode(self, mode: str, message: str = "") -> None:
        states = {
            "off": ("RX OFF", "RX audio receiver is stopped"),
            "starting": ("RX STARTING", "RX audio receiver is starting"),
            "active": ("RX ACTIVE", "RX audio receiver is active"),
            "receiving": ("RX RECEIVING", "RX is receiving speech audio"),
            "error": ("RX ERROR", message or "RX audio receiver error"),
        }
        text, tooltip = states.get(mode, states["off"])
        self._rx_badge.setProperty("state", mode)
        self._rx_label.setText(text)
        self._rx_badge.setToolTip(tooltip)
        self._rx_dot.setToolTip(tooltip)
        self._rx_label.setToolTip(tooltip)
        self._refresh(self._rx_badge)
