import sys
import threading
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from prana_elex.ui.dialogs.settings import SettingsDialog
from prana_elex.ui.i18n import language, tr
from prana_elex.ui.account import AccountController, AccountState
from prana_elex.ui.pages.account import (
    AccountStatusPage,
    AuthPage,
    ConfigErrorPage,
    DataSetupPage,
    LoadingPage,
    OfflinePage,
)
from prana_elex.ui.pages.translation import TranslationPage
from prana_elex.pipeline.orchestrator import PipelineState
from prana_elex.pipeline.orchestrator import PipelineOrchestrator
from prana_elex.storage.account import prepare_account_data_root
from prana_elex.config.user_settings import save_settings
from prana_elex.common.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    account_active_changed = Signal(bool)
    _sign_out_ready = Signal()

    def __init__(
        self,
        config,
        orchestrator=None,
        account_controller: AccountController | None = None,
        data_root: str = "",
        require_installer_data: bool = False,
    ):
        super().__init__()
        self._base_config = config
        self._config = config
        self._orchestrator = orchestrator
        self._account = account_controller
        self._data_root = data_root
        self._active_uid = ""
        self._signing_out = False

        self.setWindowTitle("PRANA ELEX")
        self.setMinimumSize(720, 600)
        self.resize(920, 760)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._translation_page = TranslationPage(self._config.translation.target_language)
        self._stack.addWidget(self._translation_page)
        self._header = self._translation_page.header
        self._header.settings_requested.connect(self.open_settings)
        self._header.toggle_requested.connect(self._on_toggle_pipeline)
        self._lang_block = self._translation_page.language_block
        self._lang_block.language_changed.connect(self._on_lang_changed)
        self._chat = self._translation_page.chat
        self._console_output = self._translation_page.console_output
        self._console_toggle = self._translation_page.console_toggle
        self._retry_button = self._translation_page.retry_button
        self._retry_button.clicked.connect(self._retry_failed_audio)
        self._log_handler = self._translation_page.log_handler

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(2000)

        self._account_refresh_timer = QTimer(self)
        self._account_refresh_timer.setInterval(30_000)
        self._account_refresh_timer.timeout.connect(lambda: self._account and self._account.refresh())

        self._loading_page = LoadingPage()
        self._auth_page = AuthPage()
        self._status_page = AccountStatusPage()
        self._offline_page = OfflinePage()
        for page in (self._loading_page, self._auth_page, self._status_page, self._offline_page):
            self._stack.addWidget(page)

        self._data_setup_page = None
        self._config_error_page = None
        if not self._data_root:
            if require_installer_data:
                self._config_error_page = ConfigErrorPage()
                self._stack.addWidget(self._config_error_page)
            else:
                self._data_setup_page = DataSetupPage(str(Path.home() / "PRANA_ELEX_Data"))
                self._data_setup_page.saved.connect(self._on_data_saved)
                self._stack.addWidget(self._data_setup_page)

        self._auth_page.sign_in_requested.connect(self._on_sign_in)
        self._auth_page.sign_up_requested.connect(self._on_sign_up)
        self._auth_page.reset_requested.connect(self._on_password_reset)
        self._status_page.refresh_requested.connect(lambda: self._account and self._account.refresh(True))
        self._status_page.resend_requested.connect(lambda: self._account and self._account.resend_verification())
        self._status_page.sign_out_requested.connect(self._request_sign_out)
        self._offline_page.retry_requested.connect(lambda: self._account and self._account.refresh(True))
        self._offline_page.sign_out_requested.connect(self._request_sign_out)
        self._sign_out_ready.connect(self._finish_sign_out)
        language.changed.connect(self._retranslate)

        if self._account:
            self._account.state_changed.connect(self._on_account_state)
            self._account.busy_changed.connect(self._auth_page.set_busy)
            self._account.notice.connect(self._on_account_notice)

        if self._config_error_page:
            self._stack.setCurrentWidget(self._config_error_page)
        elif self._data_setup_page:
            self._stack.setCurrentWidget(self._data_setup_page)
        elif self._account:
            self._stack.setCurrentWidget(self._loading_page)
        else:
            self._stack.setCurrentWidget(self._translation_page)

    def _retranslate(self, *_args) -> None:
        self._translation_page.retranslate()

    def start_account_flow(self) -> None:
        if self._account and self._data_root:
            self._account.initialize()

    def _on_data_saved(self, path: str) -> None:
        save_settings(path)
        self._data_root = path
        self._stack.setCurrentWidget(self._loading_page)
        self.start_account_flow()

    def _on_sign_in(self, email: str, password: str) -> None:
        if self._account:
            self._auth_page.set_message("")
            self._account.sign_in(email, password)

    def _on_sign_up(self, email: str, password: str) -> None:
        if self._account:
            self._auth_page.set_message("")
            self._account.sign_up(email, password)

    def _on_password_reset(self, email: str) -> None:
        if not email or "@" not in email:
            self._auth_page.set_message("Enter your email address first.", True)
            return
        if self._account:
            self._account.request_password_reset(email)

    def _on_account_notice(self, message: str, error: bool) -> None:
        if self._account and self._account.state == AccountState.SIGNED_OUT:
            self._auth_page.set_message(message, error)
        elif self._account and self._account.state in (AccountState.RESTRICTED, AccountState.OFFLINE):
            self._status_page.set_profile(self._account.profile or {}, message)
        else:
            self._auth_page.set_message(message, error)

    def _on_account_state(self, state: AccountState, profile: dict, message: str) -> None:
        if state == AccountState.LOADING:
            self._stack.setCurrentWidget(self._loading_page)
            return
        if state == AccountState.SIGNED_OUT:
            self._account_refresh_timer.stop()
            self.account_active_changed.emit(False)
            self._auth_page.set_email(self._account.backend.auth.email if self._account else "")
            if message:
                self._auth_page.set_message(message, True)
            self._stack.setCurrentWidget(self._auth_page)
            return
        if state == AccountState.OFFLINE:
            self._account_refresh_timer.start()
            self.account_active_changed.emit(False)
            self._offline_page.set_message(message)
            self._stack.setCurrentWidget(self._offline_page)
            return
        if state == AccountState.RESTRICTED:
            self._account_refresh_timer.start()
            self.account_active_changed.emit(False)
            if self._orchestrator:
                # Keep the stopped instance attached so Sign out can wait for
                # its workers and an Admin reactivation can safely reuse it.
                self._orchestrator.stop()
            self._status_page.set_profile(profile, message)
            self._stack.setCurrentWidget(self._status_page)
            return
        if state == AccountState.ACTIVE:
            self._account_refresh_timer.stop()
            self._activate_account(profile)

    def _activate_account(self, profile: dict) -> None:
        uid = str(profile.get("uid") or "")
        if not uid or not self._data_root:
            self._status_page.set_profile(profile, "Account identity or Data folder is unavailable.")
            self._stack.setCurrentWidget(self._status_page)
            return
        if self._orchestrator is None or self._active_uid != uid:
            account_root = prepare_account_data_root(self._data_root, uid)
            config = self._base_config.model_copy(deep=True)
            config.general.data_dir = account_root
            config.resolve_paths()
            self._config = config
            self._orchestrator = PipelineOrchestrator(config, self._account.backend)
            self._active_uid = uid
            self._reset_translation_ui()
        self.account_active_changed.emit(True)
        self._stack.setCurrentWidget(self._translation_page)

    def _reset_translation_ui(self) -> None:
        self._translation_page.reset()

    def _request_sign_out(self) -> None:
        if self._signing_out:
            return
        answer = QMessageBox.question(
            self,
            "Sign out",
            "Sign out of PRANA ELEX on this computer? Local data and device registration will be kept.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._begin_sign_out()

    def _begin_sign_out(self, confirm: bool = False) -> None:
        del confirm
        if self._signing_out:
            return
        self._signing_out = True
        self._stack.setCurrentWidget(self._loading_page)
        orchestrator = self._orchestrator

        def worker() -> None:
            if orchestrator:
                orchestrator.shutdown()
            self._sign_out_ready.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _finish_sign_out(self) -> None:
        self._orchestrator = None
        self._active_uid = ""
        self._signing_out = False
        self._reset_translation_ui()
        if self._account:
            self._account.sign_out_local()

    def on_access_denied(self, code: str, message: str) -> None:
        if not self._account:
            return
        if code == "AUTH_REQUIRED":
            self._begin_sign_out()
            return
        if self._orchestrator:
            self._orchestrator.stop()
        self._account.restrict(code, message)

    def _on_result(self, result):
        if result.error:
            detail = result.processing_notes[0] if result.processing_notes else result.error
            self._on_error(f"{result.error}: {detail}")
        self._chat.add_message(
            source=result.detected_language,
            transcript=result.transcript_restored,
            translation=result.translation,
            timestamp=result.timestamp,
            confidence=result.confidence,
        )
        self._chat.set_latency(result.latency_ms)
        self._history_dialog().add_result(result)
        self._log_console(result)
        self._retry_button.setVisible(bool(result.error))

    def _on_detected_language(self, code: str):
        self._lang_block.set_detected_language(code)

    def _on_state_changed(self, state: PipelineState, message: str):
        if state == PipelineState.IDLE:
            self._header.set_pipeline_running(False)
            self._header.set_rx_mode("off")
            self._chat.set_state("stopped")
        elif state == PipelineState.STARTING:
            self._header.set_pipeline_transitioning(True, tr("header.starting"))
            self._header.set_rx_mode("starting")
            self._chat.set_state("starting", message)
        elif state == PipelineState.RUNNING:
            self._header.set_pipeline_running(True)
            self._header.set_rx_mode("active")
            self._chat.set_state("listening")
        elif state == PipelineState.STOPPING:
            self._header.set_pipeline_transitioning(True, tr("header.stopping"))
            self._chat.set_state("stopping")
        elif state == PipelineState.ERROR:
            self._header.set_pipeline_running(False)
            self._header.set_rx_mode("error", message)
            self._chat.set_state("error", message)

    def _on_error(self, message: str):
        self._header.set_rx_mode("error", message)
        self._chat.set_state("error", message)

    def _retry_failed_audio(self) -> None:
        if self._orchestrator and self._orchestrator.retry_last_failed():
            self._retry_button.setEnabled(False)
            QTimer.singleShot(3000, lambda: self._retry_button.setEnabled(True))

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
        self._translation_page.log_result(result)

    def _toggle_console(self) -> None:
        self._translation_page.toggle_console()

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

        self._chat.set_gcs_status(
            enabled=status.get("backend_enabled", False),
            ready=status.get("backend_ready", False),
            error=status.get("backend_error"),
            retry_queue=0,
            last_upload_ok=status.get("backend_last_request_ok"),
        )

    def _history_dialog(self):
        return self._translation_page.history_dialog()

    def show_history(self):
        self._history_dialog().show()
        self._history_dialog().raise_()

    def open_settings(self):
        from prana_elex.config.autostart import is_enabled as autostart_is_enabled
        from prana_elex.config.autostart import set_enabled as set_autostart_enabled
        from prana_elex.audio.recorder import AudioRecorder
        try:
            devices = AudioRecorder.list_devices()
        except Exception as e:
            logger.warning("Failed to list devices", exc_info=e)
            devices = []
        try:
            from prana_elex.audio.wasapi import WASAPIBackend
            loopbacks = WASAPIBackend.list_loopback_devices()
        except Exception:
            loopbacks = []
        try:
            account = self._orchestrator.get_account()
        except Exception as exc:
            logger.warning("Failed to load account status", exc_info=True)
            account = {"email": "Unavailable", "status": str(exc)}
        try:
            account_devices = self._orchestrator.list_devices()
        except Exception:
            logger.info("Account devices are unavailable for the current subscription state")
            account_devices = []

        dialog = SettingsDialog(
            current_device=self._config.audio.device_index,
            current_mode=self._config.audio.capture_mode,
            devices=devices,
            loopback_devices=loopbacks,
            autostart_enabled=autostart_is_enabled() if sys.platform.startswith("linux") else None,
            account=account,
            account_devices=account_devices,
            parent=self,
        )
        if dialog.exec():
            if dialog.get_sign_out_requested():
                self._request_sign_out()
                return
            mode, device = dialog.get_values()
            autostart = dialog.get_autostart_enabled()
            revoke_device_id = dialog.get_revoke_device_id()
            if revoke_device_id:
                try:
                    self._orchestrator.revoke_device(revoke_device_id)
                except Exception:
                    logger.warning("Failed to revoke device", exc_info=True)
            if autostart is not None:
                try:
                    set_autostart_enabled(autostart)
                except OSError:
                    logger.warning("Failed to update autostart", exc_info=True)
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
