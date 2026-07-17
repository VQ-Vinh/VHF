from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from prana_elex.ui.icons import phosphor_icon
from prana_elex.ui.i18n import language, tr


class HeaderBar(QFrame):
    settings_requested = Signal()
    toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 10, 28, 10)
        layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        self._title = QLabel("PRANA ELEX")
        self._title.setObjectName("HeaderTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("HeaderSubtitle")
        title_block.addWidget(self._title)
        title_block.addWidget(self._subtitle)
        layout.addLayout(title_block)
        layout.addStretch()

        self._locale = QComboBox()
        self._locale.setObjectName("LocaleSelector")
        self._locale.addItem("EN", "en")
        self._locale.addItem("VI", "vi")
        self._locale.setCurrentIndex(0 if language.locale == "en" else 1)
        self._locale.currentIndexChanged.connect(lambda: language.set_locale(self._locale.currentData()))
        layout.addWidget(self._locale)

        self._start_stop_btn = QPushButton()
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
            phosphor_icon(
                "ph.gear",
                color="#C7DDE2",
                active_color="#FFFFFF",
                scale_factor=1.05,
            )
        )
        self._settings_btn.setIconSize(QSize(20, 20))
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.setToolTip(tr("header.settings"))
        self._settings_btn.setAccessibleName(tr("header.settings"))
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
        language.changed.connect(self._retranslate)
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        self._subtitle.setText(tr("app.subtitle"))
        self._settings_btn.setToolTip(tr("header.settings"))
        self._settings_btn.setAccessibleName(tr("header.settings"))
        index = self._locale.findData(language.locale)
        if index >= 0 and index != self._locale.currentIndex():
            self._locale.blockSignals(True)
            self._locale.setCurrentIndex(index)
            self._locale.blockSignals(False)
        self.set_pipeline_running(self._start_stop_btn.property("mode") == "stop")
        self.set_rx_mode(self._rx_badge.property("state") or "off")

    def _refresh(self, widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def set_pipeline_running(self, running: bool) -> None:
        self._start_stop_btn.setEnabled(True)
        self._start_stop_btn.setProperty("mode", "stop" if running else "start")
        self._start_stop_btn.setText(tr("header.stop") if running else tr("header.start"))
        self._start_stop_btn.setIcon(
            phosphor_icon(
                "ph.stop" if running else "ph.play",
                color="#2D2106" if running else "#081012",
                active_color="#2D2106" if running else "#081012",
                scale_factor=0.9,
            )
        )
        self._refresh(self._start_stop_btn)

    def set_pipeline_transitioning(self, transitioning: bool, text: str = "") -> None:
        self._start_stop_btn.setEnabled(not transitioning)
        self._start_stop_btn.setProperty("mode", "transition" if transitioning else "start")
        self._start_stop_btn.setText(text or tr("header.start"))
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
            "off": (tr("header.rx_off"), "RX audio receiver is stopped"),
            "starting": (tr("header.rx_starting"), "RX audio receiver is starting"),
            "active": (tr("header.rx_active"), "RX audio receiver is active"),
            "receiving": (tr("header.rx_receiving"), "RX is receiving speech audio"),
            "error": (tr("header.rx_error"), message or "RX audio receiver error"),
        }
        text, tooltip = states.get(mode, states["off"])
        self._rx_badge.setProperty("state", mode)
        self._rx_label.setText(text)
        self._rx_badge.setToolTip(tooltip)
        self._rx_dot.setToolTip(tooltip)
        self._rx_label.setToolTip(tooltip)
        self._refresh(self._rx_badge)
