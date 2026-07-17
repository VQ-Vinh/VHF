from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from prana_elex.ui.components.chat_feed import ChatFeed
from prana_elex.ui.components.header_bar import HeaderBar
from prana_elex.ui.components.language_block import LanguageBlock
from prana_elex.ui.dialogs.history import HistoryDialog
from prana_elex.ui.icons import phosphor_icon
from prana_elex.ui.i18n import tr


_LOGGER_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)-5s] [%(name)s] %(message)s"
_LOGGER_DATE = "%H:%M:%S"
_CONSOLE_MAX_LINES = 500


class GuiLogHandler(logging.Handler):
    def __init__(self, widget: QPlainTextEdit):
        super().__init__()
        self.widget = widget
        self.setFormatter(logging.Formatter(_LOGGER_FORMAT, _LOGGER_DATE))

    def emit(self, record) -> None:
        try:
            message = self.format(record)
            QTimer.singleShot(0, lambda value=message: self.widget.appendPlainText(value))
        except Exception:
            self.handleError(record)


class TranslationPage(QWidget):
    """Translation workspace displayed for an active account."""

    def __init__(self, target_language: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = HeaderBar()
        layout.addWidget(self.header)

        self.language_block = LanguageBlock()
        self.language_block.set_target_language(target_language)
        layout.addWidget(self.language_block)

        self.chat = ChatFeed()
        layout.addWidget(self.chat, stretch=1)

        self.console_output = QPlainTextEdit()
        self.console_output.setObjectName("ConsoleOutput")
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumBlockCount(_CONSOLE_MAX_LINES)
        self.console_output.setMaximumHeight(120)
        self.console_output.setVisible(False)

        self.console_toggle = QPushButton(tr("console.title"))
        self.console_toggle.setObjectName("ConsoleToggle")
        self.console_toggle.setCursor(Qt.PointingHandCursor)
        self.console_toggle.setIcon(phosphor_icon("ph.terminal", scale_factor=0.9))
        self.console_toggle.setIconSize(QSize(15, 15))
        self.console_toggle.setFixedHeight(30)
        self.console_toggle.clicked.connect(self.toggle_console)

        self.retry_button = QPushButton(tr("console.retry"))
        self.retry_button.setObjectName("ConsoleToggle")
        self.retry_button.setVisible(False)

        self.console_clear = QPushButton()
        self.console_clear.setObjectName("ConsoleClearButton")
        self.console_clear.setIcon(phosphor_icon("ph.trash", scale_factor=0.9))
        self.console_clear.setIconSize(QSize(15, 15))
        self.console_clear.setFixedSize(30, 30)
        self.console_clear.setCursor(Qt.PointingHandCursor)
        self.console_clear.setToolTip("Clear developer console")
        self.console_clear.setAccessibleName("Clear developer console")
        self.console_clear.clicked.connect(self.console_output.clear)
        self.console_clear.setVisible(False)

        console_header = QHBoxLayout()
        console_header.setContentsMargins(20, 0, 20, 0)
        console_header.addWidget(self.console_toggle)
        console_header.addWidget(self.retry_button)
        console_header.addStretch()
        console_header.addWidget(self.console_clear)
        layout.addLayout(console_header)
        layout.addWidget(self.console_output)

        self.log_handler = GuiLogHandler(self.console_output)
        self.log_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self.log_handler)
        self._console_visible = False
        self._history: HistoryDialog | None = None

    def retranslate(self) -> None:
        self.console_toggle.setText(tr("console.title"))
        self.retry_button.setText(tr("console.retry"))

    def reset(self) -> None:
        self.chat.clear()
        self.chat.set_state("stopped")
        self.chat.set_latency(0)
        self.console_output.clear()
        self.retry_button.setVisible(False)
        if self._history is not None:
            self._history.clear()

    def log_result(self, result) -> None:
        status = f"ERROR {result.error}" if result.error else "OK"
        self.console_output.appendPlainText(
            f"{result.timestamp.strftime('%H:%M:%S')}  "
            f"#{result.sequence:04d}  "
            f"{result.detected_language.upper() or '?':<3}  "
            f"{result.confidence:>4.0%}  "
            f"{result.latency_ms:>6.0f}ms  "
            f"{status}"
        )

    def toggle_console(self) -> None:
        self._console_visible = not self._console_visible
        self.console_output.setVisible(self._console_visible)
        self.console_clear.setVisible(self._console_visible)
        self.console_toggle.setProperty("expanded", self._console_visible)
        self.console_toggle.style().unpolish(self.console_toggle)
        self.console_toggle.style().polish(self.console_toggle)

    def history_dialog(self) -> HistoryDialog:
        if self._history is None:
            self._history = HistoryDialog(self.window())
        return self._history

    def close_logging(self) -> None:
        logging.getLogger().removeHandler(self.log_handler)
