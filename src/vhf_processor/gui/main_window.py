from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from vhf_processor.gui.chat_feed import ChatFeed
from vhf_processor.gui.header_bar import HeaderBar
from vhf_processor.gui.history_dialog import HistoryDialog
from vhf_processor.gui.language_block import LanguageBlock
from vhf_processor.gui.settings_dialog import SettingsDialog
from vhf_processor.gui.tray import TrayManager
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)


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
        layout.addWidget(self._header)

        self._lang_block = LanguageBlock()
        layout.addWidget(self._lang_block)

        self._chat = ChatFeed()
        layout.addWidget(self._chat, stretch=1)

        if orchestrator:
            orchestrator.on_result = self._on_result
            orchestrator.on_detected_language = self._on_detected_language

    def _on_result(self, result):
        self._chat.add_message(
            source=result.detected_language,
            transcript=result.transcript_restored,
            translation=result.translation,
            timestamp=result.timestamp,
        )
        self._history_dialog().add_result(result)

    def _on_detected_language(self, code: str):
        self._lang_block.set_detected_language(code)

    def _history_dialog(self):
        if not hasattr(self, "_history"):
            self._history = HistoryDialog(self)
        return self._history

    def show_history(self):
        self._history_dialog().show()
        self._history_dialog().raise_()

    def open_settings(self):
        from vhf_processor.audio.recorder import AudioRecorder
        try:
            devices = AudioRecorder.list_devices()
        except Exception as e:
            logger.warning("Failed to list devices", exc_info=e)
            devices = []
        try:
            from vhf_processor.audio.wasapi_backend import WASAPIBackend
            loopbacks = WASAPIBackend.list_loopback_devices()
        except Exception:
            loopbacks = []

        dialog = SettingsDialog(
            current_device=self._config.audio.device_index,
            current_mode=self._config.audio.capture_mode,
            current_lang=self._config.translation.target_language,
            devices=devices,
            loopback_devices=loopbacks,
            parent=self,
        )
        if dialog.exec():
            mode, device, lang = dialog.get_values()
            changed = (
                mode != self._config.audio.capture_mode or
                device != self._config.audio.device_index or
                lang != self._config.translation.target_language
            )
            if not changed:
                return
            self._config.audio.capture_mode = mode
            self._config.audio.device_index = device
            self._config.translation.target_language = lang
            self._lang_block.set_target_language(lang)
            self._restart_pipeline()

    def _set_status(self, state: str, message: str = ""):
        pass

    def _restart_pipeline(self):
        if self._orchestrator is None:
            return
        logger.info("Restarting pipeline with new settings...")
        try:
            self._orchestrator.stop()
        except Exception:
            pass
        self._orchestrator.start()
