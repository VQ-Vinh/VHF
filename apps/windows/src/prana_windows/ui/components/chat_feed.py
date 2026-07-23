from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from prana_windows.ui.icons import phosphor_icon
from prana_windows.ui.i18n import language, tr


_STATE_COLORS = {
    "starting": "#A66B12",
    "listening": "#21835A",
    "recording": "#087F8C",
    "error": "#C34655",
    "stopped": "#607683",
    "stopping": "#A66B12",
}


class ChatBubble(QFrame):
    def __init__(
        self,
        source: str,
        transcript: str,
        translation: str,
        timestamp: datetime | None = None,
        confidence: float | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("ChatBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 16)
        layout.setSpacing(6)

        ts = timestamp.strftime("%H:%M:%S") if timestamp else datetime.now().strftime("%H:%M:%S")
        metadata = [ts, source.upper() or "?"]
        if confidence is not None and confidence > 0:
            metadata.append(f"{confidence:.0%}")
        self._source = QLabel("  ·  ".join(metadata))
        self._source.setObjectName("ChatSource")
        layout.addWidget(self._source)

        self._transcript = QLabel(transcript)
        self._transcript.setObjectName("ChatTranscript")
        self._transcript.setWordWrap(True)
        layout.addWidget(self._transcript)

        self._translation = QLabel(translation)
        self._translation.setObjectName("ChatTranslation")
        self._translation.setWordWrap(True)
        layout.addWidget(self._translation)


class ChatFeed(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatFeed")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 4, 0, 4)
        self._feed_label = QLabel()
        self._feed_label.setObjectName("FeedHeader")
        header_layout.addWidget(self._feed_label)
        header_layout.addStretch()

        self._history_btn = QPushButton()
        self._history_btn.setObjectName("HistoryButton")
        self._history_btn.setIcon(
            phosphor_icon("ph.clock-counter-clockwise", scale_factor=1.05)
        )
        self._history_btn.setIconSize(QSize(18, 18))
        self._history_btn.setCursor(Qt.PointingHandCursor)
        self._history_btn.setToolTip(tr("feed.history"))
        self._history_btn.setAccessibleName(tr("feed.history"))
        self._history_btn.clicked.connect(self._on_history)
        header_layout.addWidget(self._history_btn)
        layout.addLayout(header_layout)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("ChatScroll")
        self._scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_content.setObjectName("ChatContent")
        self._feed_layout = QVBoxLayout(scroll_content)
        self._feed_layout.setContentsMargins(0, 6, 8, 6)
        self._feed_layout.setSpacing(0)
        self._empty = QFrame()
        self._empty.setObjectName("FeedEmptyState")
        empty_layout = QVBoxLayout(self._empty)
        empty_layout.setAlignment(Qt.AlignCenter)
        self._empty_title = QLabel()
        self._empty_title.setObjectName("FeedEmptyTitle")
        self._empty_title.setAlignment(Qt.AlignCenter)
        self._empty_body = QLabel()
        self._empty_body.setObjectName("FeedEmptyBody")
        self._empty_body.setAlignment(Qt.AlignCenter)
        self._empty_body.setWordWrap(True)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_body)
        self._feed_layout.addWidget(self._empty, 1)
        self._feed_layout.addStretch()

        self._scroll.setWidget(scroll_content)
        layout.addWidget(self._scroll, stretch=1)

        self._status_bar = QFrame()
        self._status_bar.setObjectName("StatusBar")
        self._status_bar.setFixedHeight(36)
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self._listening_dot = QLabel("●")
        self._listening_dot.setObjectName("ListeningDot")
        self._listening_label = QLabel("IDLE")
        self._listening_label.setObjectName("ListeningLabel")
        status_layout.addWidget(self._listening_dot)
        status_layout.addWidget(self._listening_label)
        status_layout.addStretch()

        self._gcs_dot = QLabel("●")
        self._gcs_dot.setObjectName("GcsDot")
        self._gcs_label = QLabel("API OFF")
        self._gcs_label.setObjectName("GcsLabel")
        status_layout.addWidget(self._gcs_dot)
        status_layout.addWidget(self._gcs_label)
        layout.addWidget(self._status_bar)

        self._state = "stopped"
        self.set_state("stopped")
        self.set_gcs_status(False, False, None, 0, None)
        language.changed.connect(self._retranslate)
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        self._feed_label.setText(tr("feed.title"))
        self._history_btn.setToolTip(tr("feed.history"))
        self._history_btn.setAccessibleName(tr("feed.history"))
        self._empty_title.setText(tr("feed.empty_title"))
        self._empty_body.setText(tr("feed.empty_body"))
        self.set_state(self._state)

    def add_message(
        self,
        source: str,
        transcript: str,
        translation: str,
        timestamp: datetime | None = None,
        confidence: float | None = None,
    ) -> None:
        bubble = ChatBubble(source, transcript, translation, timestamp, confidence)
        self._empty.setVisible(False)
        self._feed_layout.insertWidget(self._feed_layout.count() - 1, bubble)
        scrollbar = self._scroll.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 20
        if at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def clear(self) -> None:
        for index in range(self._feed_layout.count() - 1, -1, -1):
            item = self._feed_layout.itemAt(index)
            widget = item.widget()
            if widget and widget is not self._empty:
                self._feed_layout.takeAt(index)
                widget.deleteLater()
        self._empty.setVisible(True)

    def get_state(self) -> str:
        return self._state

    def set_state(self, state: str, message: str = "") -> None:
        self._state = state
        color = _STATE_COLORS.get(state, "#777789")
        labels = {
            "listening": tr("feed.listening"),
            "recording": tr("feed.receiving"),
            "error": tr("feed.error"),
            "starting": tr("feed.starting"),
            "stopping": tr("feed.stopping"),
            "stopped": tr("feed.idle"),
        }
        self._listening_dot.setStyleSheet(f"color: {color};")
        self._listening_label.setText(labels.get(state, "IDLE"))
        self._listening_label.setToolTip(message if state == "error" else "")

    def set_gcs_status(
        self,
        enabled: bool,
        ready: bool,
        error: str | None,
        retry_queue: int,
        last_upload_ok: bool | None,
    ) -> None:
        if not enabled:
            color, text, tooltip = "#777789", "API OFF", "PRANA API is not configured"
        elif retry_queue:
            color, text = "#F2B84B", f"API RETRY ({retry_queue})"
            tooltip = error or f"{retry_queue} file(s) waiting to upload"
        elif error:
            color, text, tooltip = "#C34655", tr("feed.api_error"), error
        elif last_upload_ok is True:
            color, text, tooltip = "#21835A", tr("feed.api_ok"), "Latest translation request succeeded"
        elif last_upload_ok is False:
            color, text, tooltip = "#C34655", tr("feed.api_error"), "Latest translation request failed"
        elif ready:
            color, text, tooltip = "#087F8C", tr("feed.api_ready"), "Signed in and ready"
        else:
            color, text, tooltip = "#F2B84B", "API STARTING", "PRANA API is initializing"

        self._gcs_dot.setStyleSheet(f"color: {color};")
        self._gcs_label.setStyleSheet(f"color: {color};")
        self._gcs_label.setText(text)
        self._gcs_dot.setToolTip(tooltip)
        self._gcs_label.setToolTip(tooltip)

    def _on_history(self) -> None:
        window = self.window()
        if hasattr(window, "show_history"):
            window.show_history()
        else:
            from prana_windows.ui.dialogs.history import HistoryDialog
            dialog = HistoryDialog(window)
            dialog.exec()
