from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


_STATE_COLORS = {
    "starting":  "#FFD600",
    "listening": "#00E566",
    "recording": "#FF3B30",
    "error":     "#FF3B30",
    "stopped":   "#666666",
    "stopping":  "#FFD600",
}


class ChatBubble(QFrame):
    def __init__(self, source: str, transcript: str, translation: str, timestamp: datetime | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)

        ts = timestamp.strftime('%H:%M:%S') if timestamp else datetime.now().strftime('%H:%M:%S')
        self._source = QLabel(f"SOURCE \u00B7 {ts}")
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        header_layout = QHBoxLayout()
        feed_label = QLabel("LIVE TRANSLATION")
        feed_label.setObjectName("FeedHeader")
        header_layout.addWidget(feed_label)
        header_layout.addStretch()

        self._history_btn = QPushButton("\uD83D\uDCCB")
        self._history_btn.setObjectName("HistoryButton")
        self._history_btn.clicked.connect(self._on_history)
        header_layout.addWidget(self._history_btn)
        layout.addLayout(header_layout)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("ChatScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.viewport().setStyleSheet("background: #0D0D0F;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: #0D0D0F;")
        self._feed_layout = QVBoxLayout(scroll_content)
        self._feed_layout.setContentsMargins(0, 8, 0, 8)
        self._feed_layout.setSpacing(0)
        self._feed_layout.addStretch()

        self._scroll.setWidget(scroll_content)
        layout.addWidget(self._scroll, stretch=1)

        status_layout = QHBoxLayout()
        self._listening_dot = QLabel("\u25CF")
        self._listening_dot.setObjectName("ListeningDot")
        self._listening_label = QLabel("IDLE")
        self._listening_label.setObjectName("ListeningLabel")
        status_layout.addWidget(self._listening_dot)
        status_layout.addWidget(self._listening_label)
        status_layout.addStretch()
        self._gcs_label = QLabel()
        self._gcs_label.setObjectName("GcsLabel")
        self._gcs_label.hide()
        status_layout.addWidget(self._gcs_label)
        layout.addLayout(status_layout)

        self._state = "stopped"

    def add_message(self, source: str, transcript: str, translation: str, timestamp: datetime | None = None):
        bubble = ChatBubble(source, transcript, translation, timestamp)
        self._feed_layout.insertWidget(self._feed_layout.count() - 1, bubble)
        sb = self._scroll.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 20
        if at_bottom:
            QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

    def clear(self):
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def get_state(self) -> str:
        return self._state

    def set_state(self, state: str, message: str = "") -> None:
        self._state = state
        color = _STATE_COLORS.get(state, "#666666")

        self._listening_dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._listening_dot.show()

        if state == "listening":
            self._listening_label.setText("LISTENING")
        elif state == "recording":
            self._listening_label.setText("RECORDING")
        elif state == "error":
            self._listening_label.setText(f"ERROR: {message}" if message else "ERROR")
        elif state == "starting":
            self._listening_label.setText("STARTING...")
        elif state == "stopping":
            self._listening_label.setText("STOPPING...")
        else:
            self._listening_label.setText("IDLE")

    def set_gcs_status(
        self,
        enabled: bool,
        ready: bool,
        error: str | None,
        retry_queue: int,
        last_upload_ok: bool | None,
    ) -> None:
        if not enabled:
            color, text, tooltip = "#6A6A7E", "GCS OFF", "Cloud upload is disabled"
        elif retry_queue:
            color = "#FFD600"
            text = f"GCS RETRY ({retry_queue})"
            tooltip = error or f"{retry_queue} file(s) waiting to upload"
        elif error:
            color, text, tooltip = "#FF5A52", "GCS ERROR", error
        elif last_upload_ok is True:
            color, text, tooltip = "#00E566", "GCS SYNCED", "Latest audio and result uploaded"
        elif last_upload_ok is False:
            color, text, tooltip = "#FF5A52", "GCS UPLOAD ERROR", "Latest upload failed"
        elif ready:
            color, text, tooltip = "#00B8D4", "GCS READY", "Cloud client is ready; no upload yet"
        else:
            color, text, tooltip = "#FFD600", "GCS STARTING", "Cloud client is initializing"

        self._gcs_label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        self._gcs_label.setText(text)
        self._gcs_label.setToolTip(tooltip)
        self._gcs_label.show()

    def _on_history(self):
        w = self.window()
        if hasattr(w, "show_history"):
            w.show_history()
        else:
            from prana_elex.ui.history_dialog import HistoryDialog
            dialog = HistoryDialog(w)
            dialog.exec()
