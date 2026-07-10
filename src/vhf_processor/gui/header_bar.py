from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class HeaderBar(QFrame):
    settings_requested = Signal()

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

        self._settings_btn = QPushButton("\u2699")
        self._settings_btn.setObjectName("SettingsButton")
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self._settings_btn)

        rx_layout = QHBoxLayout()
        self._rx_dot = QLabel("\u25CF")
        self._rx_dot.setObjectName("RxDot")
        rx_label = QLabel("RX")
        rx_label.setObjectName("RxBadge")
        rx_layout.addWidget(self._rx_dot)
        rx_layout.addWidget(rx_label)
        layout.addLayout(rx_layout)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start(1000)
        self._dot_visible = True

    def _pulse(self):
        self._dot_visible = not self._dot_visible
        self._rx_dot.setVisible(self._dot_visible)
