import math

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


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

        self._settings_icon = self._make_gear_icon()
        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("SettingsButton")
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.setIcon(self._settings_icon)
        self._settings_btn.setIconSize(QSize(20, 20))
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
        self._dot_visible = True

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
        self._pulse_timer.stop()
        if not running:
            self._rx_dot.setStyleSheet("color: #666666; font-size: 10px;")
            self._rx_dot.hide()
        elif recording:
            self._rx_dot.setStyleSheet("color: #FF3B30; font-size: 12px;")
            self._rx_dot.show()
        else:
            self._rx_dot.setStyleSheet("color: #00E566; font-size: 10px;")
            self._rx_dot.show()
            self._pulse_timer.start(1500)

    def _pulse(self):
        self._dot_visible = not self._dot_visible
        self._rx_dot.setVisible(self._dot_visible)

    @staticmethod
    def _make_gear_icon() -> QIcon:
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#C0C0D0"), 2.0)
        p.setPen(pen)
        cx, cy, r_outer, r_inner = 18, 18, 13, 8
        for a in range(0, 360, 30):
            ax = cx + r_outer * math.cos(math.radians(a))
            ay = cy + r_outer * math.sin(math.radians(a))
            bx = cx + r_inner * math.cos(math.radians(a))
            by = cy + r_inner * math.sin(math.radians(a))
            p.drawLine(int(ax), int(ay), int(bx), int(by))
        p.setBrush(QColor("#C0C0D0"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - 4, cy - 4, 8, 8)
        p.end()
        return QIcon(pix)
