import sys
import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from prana_windows.ui.dialogs.settings import SettingsDialog
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.account import AccountController, AccountState
from prana_windows.ui.pages.account import (
    AuthPage,
    ConfigErrorPage,
    DataSetupPage,
    LoadingPage,
    OfflinePage,
)
from prana_windows.ui.pages.account_center import AccountCenterPage
from prana_windows.ui.pages.plans import PlansPage
from prana_windows.ui.pages.translation import TranslationPage
from prana_core.pipeline.orchestrator import PipelineState
from prana_core.pipeline.orchestrator import PipelineOrchestrator
from prana_core.audio.base import AudioBackend
from prana_windows.audio.wasapi import WASAPIBackend
from prana_core.storage.account import prepare_data_root
from prana_windows.settings import save_settings
from prana_core.common.logger import get_logger

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
        audio_backend_factory: Callable[[], AudioBackend] = WASAPIBackend,
    ):
        super().__init__()
        self._base_config = config
        self._config = config
        self._orchestrator = orchestrator
        self._account = account_controller
        self._data_root = data_root
        self._active_uid = ""
        self._audio_backend_factory = audio_backend_factory
        self._signing_out = False
        self._account_center_open = False
        self._plans_open = False

        self.setWindowTitle("PRANA ELEX")
        self.setMinimumSize(720, 600)
        self.resize(920, 760)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._translation_page = TranslationPage(self._config.translation.target_language)
        self._stack.addWidget(self._translation_page)
        self._header = self._translation_page.header
        self._header.settings_requested.connect(self.open_settings)
        self._header.account_requested.connect(self.open_account_center)
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
        self._account_refresh_timer.timeout.connect(self._refresh_visible_account_page)

        self._loading_page = LoadingPage()
        google_enabled = bool(
            self._account and self._account.backend.auth.google_enabled
        )
        self._auth_page = AuthPage(google_enabled=google_enabled)
        self._account_center = AccountCenterPage(google_enabled=google_enabled)
        self._plans_page = PlansPage()
        self._offline_page = OfflinePage()
        for page in (
            self._loading_page,
            self._auth_page,
            self._account_center,
            self._plans_page,
            self._offline_page,
        ):
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
        self._auth_page.google_requested.connect(
            lambda: self._account and self._account.sign_in_with_google()
        )
        self._auth_page.google_cancel_requested.connect(
            lambda: self._account and self._account.cancel_google_oauth()
        )
        self._account_center.refresh_requested.connect(
            lambda: self._account and self._account.load_account_center()
        )
        self._account_center.reset_requested.connect(
            lambda email: self._account and self._account.request_password_reset(email)
        )
        self._account_center.resend_requested.connect(
            lambda: self._account and self._account.resend_verification()
        )
        self._account_center.revoke_requested.connect(self._confirm_revoke_device)
        self._account_center.sign_out_requested.connect(self._request_sign_out)
        self._account_center.back_requested.connect(self._close_account_center)
        self._account_center.link_google_requested.connect(
            lambda: self._account and self._account.link_google_account()
        )
        self._account_center.google_cancel_requested.connect(
            lambda: self._account and self._account.cancel_google_oauth()
        )
        self._account_center.manage_plan_requested.connect(self.open_plans)
        self._plans_page.back_requested.connect(self._back_to_account_center)
        self._plans_page.refresh_requested.connect(
            lambda: self._account and self._account.load_plans()
        )
        self._plans_page.select_requested.connect(
            lambda plan_id: self._account and self._account.select_plan(plan_id)
        )
        self._offline_page.retry_requested.connect(lambda: self._account and self._account.refresh(True))
        self._offline_page.sign_out_requested.connect(self._request_sign_out)
        self._sign_out_ready.connect(self._finish_sign_out)
        language.changed.connect(self._retranslate)

        if self._account:
            self._account.state_changed.connect(self._on_account_state)
            self._account.busy_changed.connect(self._auth_page.set_busy)
            self._account.notice.connect(self._on_account_notice)
            self._account.details_changed.connect(self._on_account_details)
            self._account.details_error.connect(
                lambda message: self._account_center.set_message(message, True)
            )
            self._account.details_loading.connect(self._account_center.set_loading)
            self._account.google_browser_requested.connect(
                self._open_google_authorization
            )
            self._account.google_flow_changed.connect(
                self._auth_page.set_google_waiting
            )
            self._account.google_flow_changed.connect(
                self._account_center.set_google_waiting
            )
            self._account.plans_changed.connect(self._on_plans_changed)
            self._account.plans_error.connect(
                lambda message: self._plans_page.set_message(message, True)
            )
            self._account.plans_loading.connect(self._plans_page.set_loading)

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
        if self._account_center_open and self._account and self._account.profile:
            message = self._account_status_message(self._account.profile, "")
            if message:
                self._account_center.set_message(message, True)

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
        if message.startswith("GOOGLE:"):
            code = message.partition(":")[2]
            key = {
                "ACCOUNT_CREATED": "account.google_account_created",
                "GOOGLE_LINKED": "account.google_link_success",
                "GOOGLE_AUTH_CANCELLED": "account.google_cancelled",
                "GOOGLE_AUTH_TIMEOUT": "account.google_timeout",
                "GOOGLE_CALLBACK_UNAVAILABLE": "account.google_callback_unavailable",
                "GOOGLE_BROWSER_FAILED": "account.google_browser_failed",
                "GOOGLE_OAUTH_NOT_CONFIGURED": "account.google_not_configured",
                "EMAIL_EXISTS": "account.google_account_exists",
                "ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL": "account.google_account_exists",
                "FEDERATED_USER_ID_ALREADY_LINKED": "account.google_account_exists",
                "INVALID_IDP_RESPONSE": "account.google_provider_mismatch",
                "OPERATION_NOT_ALLOWED": "account.google_provider_disabled",
                "CONFIGURATION_NOT_FOUND": "account.google_provider_disabled",
                "GOOGLE_AUTH_NOT_CONFIGURED": "account.google_provider_disabled",
                "GOOGLE_AUTH_UNAVAILABLE": "account.google_network_error",
                "GOOGLE_EMAIL_MISMATCH": "account.google_email_mismatch",
                "NETWORK_ERROR": "account.google_network_error",
                "GOOGLE_LINK_FAILED": "account.google_link_failed",
            }.get(code, "account.google_failed")
            message = tr(key)
        if self._stack.currentWidget() is self._account_center:
            if message.startswith("If the account exists"):
                message = tr("account.reset_sent")
            elif message == "Device revoked.":
                message = tr("account.device_revoked_notice")
            self._account_center.set_message(message, error)
        elif self._account and self._account.state == AccountState.SIGNED_OUT:
            self._auth_page.set_message(message, error)
        elif self._account and self._account.state in (AccountState.RESTRICTED, AccountState.OFFLINE):
            self._account_center.set_profile(self._account.profile or {})
            self._account_center.set_message(message, error)
        else:
            self._auth_page.set_message(message, error)

    def _open_google_authorization(self, url: str) -> None:
        if QDesktopServices.openUrl(QUrl(url)):
            return
        if self._account:
            self._account.cancel_google_oauth(
                "GOOGLE_BROWSER_FAILED",
                "The system browser could not be opened",
            )
            return
        self._auth_page.set_message(
            tr("account.google_browser_failed"),
            True,
        )

    def _on_account_state(self, state: AccountState, profile: dict, message: str) -> None:
        if state == AccountState.LOADING:
            self._stack.setCurrentWidget(self._loading_page)
            return
        if state == AccountState.SIGNED_OUT:
            self._account_refresh_timer.stop()
            self._account_center_open = False
            self._plans_open = False
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
            first_open = not self._account_center_open
            self._account_center_open = True
            self._plans_open = False
            self._account_center.set_profile(profile)
            self._account_center.set_message(self._account_status_message(profile, message), True)
            self._stack.setCurrentWidget(self._account_center)
            if first_open and self._account:
                self._account.load_account_center()
            return
        if state == AccountState.ACTIVE:
            keep_account_page = self._account_center_open or self._plans_open
            if keep_account_page:
                self._account_refresh_timer.start()
            else:
                self._account_refresh_timer.stop()
            self._activate_account(profile, show_translation=not keep_account_page)

    def _activate_account(self, profile: dict, show_translation: bool = True) -> None:
        uid = str(profile.get("uid") or "")
        if not uid or not self._data_root:
            self._account_center.set_profile(profile)
            self._account_center.set_message("Account identity or Data folder is unavailable.", True)
            self._stack.setCurrentWidget(self._account_center)
            return
        if self._orchestrator is None or self._active_uid != uid:
            data_root = prepare_data_root(self._data_root, uid)
            config = self._base_config.model_copy(deep=True)
            config.general.data_dir = data_root
            config.resolve_paths()
            self._config = config
            self._orchestrator = PipelineOrchestrator(
                config,
                self._account.backend,
                self._audio_backend_factory,
            )
            self._active_uid = uid
            self._reset_translation_ui()
        self.account_active_changed.emit(True)
        if show_translation:
            self._stack.setCurrentWidget(self._translation_page)
        else:
            if self._plans_open:
                self._plans_page.set_profile(profile)
                self._stack.setCurrentWidget(self._plans_page)
            else:
                self._account_center.set_profile(
                    profile,
                    current_device_id=self._account.backend.local_device_id if self._account else "",
                )
                self._account_center.set_message("")
                self._stack.setCurrentWidget(self._account_center)

    def _reset_translation_ui(self) -> None:
        self._translation_page.reset()

    def _request_sign_out(self) -> None:
        if self._signing_out:
            return
        answer = QMessageBox.question(
            self,
            tr("account.sign_out_title"),
            tr("account.sign_out_body"),
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
        self._account_center_open = False
        self._plans_open = False
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

    def on_quota_exhausted(self, _code: str, message: str, resets_at: str) -> None:
        if self._orchestrator:
            self._orchestrator.stop()
        self._translation_page.show_quota_exhausted(resets_at)
        self._retry_button.setVisible(True)
        self._on_error(message)

    def _on_result(self, result):
        if result.error:
            detail = result.processing_notes[0] if result.processing_notes else result.error
            self._on_error(f"{result.error}: {detail}")
        else:
            self._translation_page.clear_quota_exhausted()
        self._chat.add_message(
            source=result.detected_language,
            transcript=result.transcript_restored,
            translation=result.translation,
            timestamp=result.timestamp,
            confidence=result.confidence,
        )
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

    def open_account_center(self) -> None:
        if not self._account or self._account.state not in (AccountState.ACTIVE, AccountState.RESTRICTED):
            return
        self._account_center_open = True
        self._plans_open = False
        self._account_center.set_profile(
            self._account.profile or {},
            current_device_id=self._account.backend.local_device_id,
        )
        self._account_center.set_message("")
        self._stack.setCurrentWidget(self._account_center)
        self._account_refresh_timer.start()
        self._account.load_account_center()

    def _close_account_center(self) -> None:
        if not self._account or self._account.state != AccountState.ACTIVE:
            return
        self._account_center_open = False
        self._plans_open = False
        self._account_refresh_timer.stop()
        self._stack.setCurrentWidget(self._translation_page)

    def _refresh_visible_account_page(self) -> None:
        if not self._account:
            return
        if self._stack.currentWidget() is self._account_center:
            self._account.load_account_center()
        elif self._stack.currentWidget() is self._plans_page:
            self._account.load_plans()
        else:
            self._account.refresh()

    def open_plans(self) -> None:
        if not self._account or self._account.state not in (AccountState.ACTIVE, AccountState.RESTRICTED):
            return
        self._account_center_open = False
        self._plans_open = True
        self._plans_page.set_profile(self._account.profile or {})
        self._plans_page.set_message("")
        self._stack.setCurrentWidget(self._plans_page)
        self._account_refresh_timer.start()
        self._account.load_plans()

    def _back_to_account_center(self) -> None:
        if not self._account:
            return
        self._plans_open = False
        self.open_account_center()

    def _on_plans_changed(self, profile: dict, plans: list[dict]) -> None:
        self._plans_page.set_data(profile, plans)
        self._plans_page.set_message("")
        if self._plans_open:
            self._stack.setCurrentWidget(self._plans_page)

    def _on_account_details(
        self,
        profile: dict,
        devices: list[dict],
        providers: list[str],
    ) -> None:
        current_device_id = ""
        if self._account and profile.get("email_verified"):
            current_device_id = self._account.backend.local_device_id
        self._account_center.set_profile(
            profile,
            devices,
            current_device_id,
            providers,
        )
        message = self._account_status_message(profile, "")
        self._account_center.set_message(message, bool(message))

    @staticmethod
    def _account_status_message(profile: dict, fallback: str) -> str:
        if not profile.get("email_verified"):
            return tr("account.verify_required")
        status = str(profile.get("status") or "registered")
        key = {
            "registered": "account.verify_required",
            "email_verified": "account.pending_message",
            "pending_payment": "account.pending_message",
            "expired": "account.expired_message",
            "suspended": "account.suspended_message",
        }.get(status)
        return tr(key) if key else fallback

    def _confirm_revoke_device(self, device_id: str) -> None:
        if not self._account or device_id == self._account.backend.local_device_id:
            return
        answer = QMessageBox.question(
            self,
            tr("account.revoke_title"),
            tr("account.revoke_body"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._account.revoke_account_device(device_id)

    def open_settings(self):
        try:
            devices = self._audio_backend_factory().list_devices()
        except Exception as e:
            logger.warning("Failed to list devices", exc_info=e)
            devices = []
        try:
            loopbacks = WASAPIBackend.list_loopback_devices()
        except Exception:
            loopbacks = []
        dialog = SettingsDialog(
            current_device=self._config.audio.device_index,
            current_mode=self._config.audio.capture_mode,
            devices=devices,
            loopback_devices=loopbacks,
            autostart_enabled=None,
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
