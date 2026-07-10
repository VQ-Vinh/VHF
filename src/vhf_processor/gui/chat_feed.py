from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class ChatBubble(QFrame):
    def __init__(self, source: str, transcript: str, translation: str, timestamp: datetime | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)

        self._source = QLabel(f"SOURCE \u00B7 {(timestamp.strftime('%H:%M:%S') if timestamp else datetime.now().strftime('%H:%M:%S'))}")
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
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self._feed_layout = QVBoxLayout(scroll_content)
        self._feed_layout.setContentsMargins(0, 8, 0, 8)
        self._feed_layout.setSpacing(0)
        self._feed_layout.addStretch()

        self._scroll.setWidget(scroll_content)
        layout.addWidget(self._scroll, stretch=1)

        status_layout = QHBoxLayout()
        self._listening_dot = QLabel("\u25CF")
        self._listening_dot.setObjectName("ListeningDot")
        self._listening_label = QLabel("LISTENING")
        self._listening_label.setObjectName("ListeningLabel")
        status_layout.addWidget(self._listening_dot)
        status_layout.addWidget(self._listening_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_listening)
        self._pulse_timer.start(1500)
        self._listening_visible = True

    def add_message(self, source: str, transcript: str, translation: str, timestamp: datetime | None = None):
        bubble = ChatBubble(source, transcript, translation, timestamp)
        self._feed_layout.insertWidget(self._feed_layout.count() - 1, bubble)
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())

    def clear(self):
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _pulse_listening(self):
        self._listening_visible = not self._listening_visible
        self._listening_dot.setVisible(self._listening_visible)

    def _on_history(self):
        w = self.window()
        if hasattr(w, "show_history"):
            w.show_history()
        else:
            from vhf_processor.gui.history_dialog import HistoryDialog
            dialog = HistoryDialog(w)
            dialog.exec()
