from pathlib import Path

import qtawesome
from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from qtawesome.iconic_font import IconicFont


_phosphor_icons: IconicFont | None = None


def _get_phosphor_icons() -> IconicFont:
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
    return _phosphor_icons


class HeaderBar(QFrame):
    settings_requested = Signal()
    toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)

        title_block = QVBoxLayout()
        self._title = QLabel("PRANA ELEX")
        self._title.setObjectName("HeaderTitle")
        self._subtitle = QLabel("VHF MARINE")
        self._subtitle.setObjectName("HeaderSubtitle")
        title_block.addWidget(self._title)
        title_block.addWidget(self._subtitle)
        layout.addLayout(title_block)

        layout.addStretch()

        self._start_stop_btn = QPushButton("\u25B6 Start")
        self._start_stop_btn.setObjectName("StartStopButton")
        self._start_stop_btn.setFixedHeight(32)
        self._start_stop_btn.clicked.connect(self.toggle_requested.emit)
        layout.addWidget(self._start_stop_btn)

        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("SettingsButton")
        self._settings_btn.setFixedSize(36, 36)
        self._set_settings_icon()
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.setAccessibleName("Settings")
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self._settings_btn)

        rx_layout = QHBoxLayout()
        self._rx_dot = QLabel("\u25CF")
        self._rx_dot.setObjectName("RxDot")
        self._rx_label = QLabel("RX")
        self._rx_label.setObjectName("RxBadge")
        rx_layout.addWidget(self._rx_dot)
        rx_layout.addWidget(self._rx_label)
        layout.addLayout(rx_layout)

        self.set_rx_state(recording=False, running=False)

    def set_pipeline_running(self, running: bool) -> None:
        self._start_stop_btn.setEnabled(True)
        if running:
            self._start_stop_btn.setText("\u25A0 Stop")
        else:
            self._start_stop_btn.setText("\u25B6 Start")

    def set_pipeline_transitioning(self, transitioning: bool, text: str = "") -> None:
        self._start_stop_btn.setEnabled(not transitioning)
        if transitioning:
            self._start_stop_btn.setText(text)
        else:
            self._start_stop_btn.setText("\u25B6 Start")

    def set_rx_state(self, recording: bool, running: bool) -> None:
        del recording  # Speech activity is shown by the RECORDING status below.
        if not running:
            self._rx_dot.setStyleSheet("color: #4B4B58; font-size: 10px;")
            self._rx_dot.show()
            tooltip = "RX audio receiver is stopped"
        else:
            self._rx_dot.setStyleSheet("color: #00E566; font-size: 10px;")
            self._rx_dot.show()
            tooltip = "RX audio receiver is active"
        self._rx_dot.setToolTip(tooltip)
        self._rx_label.setToolTip(tooltip)

    def _set_settings_icon(self) -> None:
        icon = _get_phosphor_icons().icon(
            "ph.gear",
            color="#B8B8C8",
            color_active="#00E5FF",
            scale_factor=1.05,
        )
        self._settings_btn.setIcon(icon)
        self._settings_btn.setIconSize(QSize(20, 20))
