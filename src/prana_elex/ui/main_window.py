import logging as _logging
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from prana_elex.ui.chat_feed import ChatFeed
from prana_elex.ui.header_bar import HeaderBar
from prana_elex.ui.history_dialog import HistoryDialog
from prana_elex.ui.language_block import LanguageBlock
from prana_elex.ui.settings_dialog import SettingsDialog
from prana_elex.core.pipeline.orchestrator import PipelineState
from prana_elex.core.utils.logger import get_logger

logger = get_logger(__name__)


_LOGGER_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)-5s] [%(name)s] %(message)s"
_LOGGER_DATE = "%H:%M:%S"
_CONSOLE_MAX_LINES = 500


class _GuiLogHandler(_logging.Handler):
    def __init__(self, widget: QPlainTextEdit):
        super().__init__()
        self.widget = widget
        self.setFormatter(_logging.Formatter(_LOGGER_FORMAT, _LOGGER_DATE))

    def emit(self, record):
        try:
            msg = self.format(record)
            QTimer.singleShot(0, lambda m=msg: self.widget.appendPlainText(m))
        except Exception:
            self.handleError(record)


class MainWindow(QMainWindow):
    def __init__(self, config, orchestrator=None):
        super().__init__()
        self._config = config
        self._orchestrator = orchestrator

        self.setWindowTitle("PRANA ELEX")
        self.setMinimumSize(500, 600)
        self.resize(780, 720)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = HeaderBar()
        self._header.settings_requested.connect(self.open_settings)
        self._header.toggle_requested.connect(self._on_toggle_pipeline)
        layout.addWidget(self._header)

        self._lang_block = LanguageBlock()
        self._lang_block.set_target_language(self._config.translation.target_language)
        self._lang_block.language_changed.connect(self._on_lang_changed)
        layout.addWidget(self._lang_block)

        self._chat = ChatFeed()
        layout.addWidget(self._chat, stretch=1)

        self._console_visible = False
        self._console_output = QPlainTextEdit()
        self._console_output.setObjectName("ConsoleOutput")
        self._console_output.setReadOnly(True)
        self._console_output.setMaximumBlockCount(_CONSOLE_MAX_LINES)
        self._console_output.setVisible(False)

        self._console_toggle = QPushButton("\u25B6 Console")
        self._console_toggle.setObjectName("ConsoleToggle")
        self._console_toggle.setCursor(Qt.PointingHandCursor)
        self._console_toggle.clicked.connect(self._toggle_console)
        self._console_toggle.setFixedHeight(24)

        console_header = QHBoxLayout()
        console_header.setContentsMargins(20, 0, 20, 0)
        console_header.addWidget(self._console_toggle)
        console_header.addStretch()
        layout.addLayout(console_header)
        layout.addWidget(self._console_output)

        self._log_handler = _GuiLogHandler(self._console_output)
        self._log_handler.setLevel(_logging.DEBUG)
        _logging.getLogger().addHandler(self._log_handler)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(2000)

    def _on_result(self, result):
        self._chat.add_message(
            source=result.detected_language,
            transcript=result.transcript_restored,
            translation=result.translation,
            timestamp=result.timestamp,
        )
        self._history_dialog().add_result(result)
        self._log_console(result)

    def _on_detected_language(self, code: str):
        self._lang_block.set_detected_language(code)

    def _on_state_changed(self, state: PipelineState, message: str):
        if state == PipelineState.IDLE:
            self._header.set_pipeline_running(False)
            self._chat.set_state("stopped")
        elif state == PipelineState.STARTING:
            self._header.set_pipeline_transitioning(True, "Starting...")
            self._chat.set_state("starting", message)
        elif state == PipelineState.RUNNING:
            self._header.set_pipeline_running(True)
            self._chat.set_state("listening")
        elif state == PipelineState.STOPPING:
            self._header.set_pipeline_transitioning(True, "Stopping...")
            self._chat.set_state("stopping")
        elif state == PipelineState.ERROR:
            self._header.set_pipeline_running(False)
            self._chat.set_state("error", message)

    def _on_error(self, message: str):
        self._chat.set_state("error", message)

    def _on_lang_changed(self, code: str) -> None:
        if code == self._config.translation.target_language:
            return
        self._config.translation.target_language = code

    def _on_toggle_pipeline(self) -> None:
        if self._orchestrator is None:
            return
        if self._orchestrator.state == PipelineState.RUNNING:
            self._orchestrator.stop()
        elif self._orchestrator.state in (PipelineState.IDLE, PipelineState.ERROR):
            self._orchestrator.start()

    def _log_console(self, result) -> None:
        sep = "-" * 60
        lines = [f"\n{sep}"]
        lines.append(f"  [#{result.sequence}] {result.timestamp.strftime('%H:%M:%S')}")
        lines.append(f"  LANG: {result.detected_language.upper() or '?'}  |  CONF: {result.confidence:.0%}")
        if result.transcript_restored:
            lines.append(f"  TXT:  {result.transcript_restored}")
        if result.translation:
            lines.append(f"  TRN:  {result.translation}")
        if result.corrections:
            for c in result.corrections:
                lines.append(f"  ! {c}")
        if result.uncertain_segments:
            lines.append(f"  UNCERTAIN: {', '.join(result.uncertain_segments)}")
        if result.error:
            lines.append(f"  ERROR: {result.error}")
        if result.latency_ms:
            process_ms = result.latency_ms - result.queue_wait_ms
            if result.queue_wait_ms > 0:
                lines.append(f"  LATENCY: {result.latency_ms:.0f}ms (process: {process_ms:.0f}ms | queue: {result.queue_wait_ms:.0f}ms)")
            else:
                lines.append(f"  LATENCY: {result.latency_ms:.0f}ms")
        lines.append(f"{sep}\n")
        text = "\n".join(lines)
        self._console_output.appendPlainText(text)

    def _toggle_console(self) -> None:
        self._console_visible = not self._console_visible
        self._console_output.setVisible(self._console_visible)
        self._console_toggle.setText("\u25BC Console" if self._console_visible else "\u25B6 Console")

    def _poll_status(self) -> None:
        if self._orchestrator is None:
            return
        try:
            status = self._orchestrator.get_status()
        except Exception:
            logger.warning("Status poll failed", exc_info=True)
            return
        running = status.get("running", False)
        recording = status.get("recording", False)
        self._header.set_rx_state(recording, running)

        chat_state = self._chat.get_state()
        if running and recording and chat_state != "recording":
            self._chat.set_state("recording")
        elif running and not recording and chat_state == "recording":
            self._chat.set_state("listening")

    def _history_dialog(self):
        if not hasattr(self, "_history"):
            self._history = HistoryDialog(self)
        return self._history

    def show_history(self):
        self._history_dialog().show()
        self._history_dialog().raise_()

    def open_settings(self):
        from prana_elex.core.audio.recorder import AudioRecorder
        try:
            devices = AudioRecorder.list_devices()
        except Exception as e:
            logger.warning("Failed to list devices", exc_info=e)
            devices = []
        try:
            from prana_elex.core.audio.wasapi_backend import WASAPIBackend
            loopbacks = WASAPIBackend.list_loopback_devices()
        except Exception:
            loopbacks = []

        dialog = SettingsDialog(
            current_device=self._config.audio.device_index,
            current_mode=self._config.audio.capture_mode,
            devices=devices,
            loopback_devices=loopbacks,
            parent=self,
        )
        if dialog.exec():
            mode, device = dialog.get_values()
            changed = (
                mode != self._config.audio.capture_mode or
                device != self._config.audio.device_index
            )
            if not changed:
                return
            self._config.audio.capture_mode = mode
            self._config.audio.device_index = device

            if self._orchestrator.is_running:
                self._orchestrator.restart()

    def _set_status(self, state: str, message: str = ""):
        self._chat.set_state(state, message)
