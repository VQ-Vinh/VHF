import threading
from datetime import datetime, timezone

from PySide6.QtCore import QEvent, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from prana_windows.ui.i18n import language, tr
from prana_windows.ui.account import AccountController, AccountState
from prana_windows.ui.console import FleetController, StationController, TxController
from prana_windows.ui.pages.account import (
    AuthPage,
    LoadingPage,
    OfflinePage,
)
from prana_windows.ui.pages.account_center import AccountCenterPage
from prana_windows.ui.pages.fleet import FleetPage
from prana_windows.ui.pages.not_operator import NotOperatorPage
from prana_windows.ui.pages.plans import PlansPage
from prana_windows.ui.pages.station_workspace import StationWorkspacePage
from prana_core.backend.client import BackendApiError
from prana_core.console.station_client import OperatorStationClient
from prana_core.console.tx_phase import StationReadiness, TxPhase
from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Fleet operator console.

    This app used to capture audio locally and translate it. It now drives
    remote Stations and owns no pipeline of its own; everything on screen is
    polled from the API, because Firestore rules deny a client any read outside
    its own `users/{uid}` subtree.
    """

    account_active_changed = Signal(bool)
    _sign_out_ready = Signal()

    def __init__(
        self,
        config,
        account_controller: AccountController | None = None,
        station_client: OperatorStationClient | None = None,
    ):
        super().__init__()
        self._config = config
        self._account = account_controller
        self._client = station_client
        self._fleet: FleetController | None = None
        self._station: StationController | None = None
        self._tx: TxController | None = None
        self._tx_confirmed_once = False
        self._signing_out = False
        self._account_center_open = False
        self._plans_open = False
        self._operator_uid = ""

        self.setWindowTitle("PRANA ELEX")
        self.setMinimumSize(900, 620)
        self.resize(1180, 820)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._loading_page = LoadingPage()
        google_enabled = bool(self._account and self._account.backend.auth.google_enabled)
        self._auth_page = AuthPage(google_enabled=google_enabled)
        self._account_center = AccountCenterPage(google_enabled=google_enabled)
        self._plans_page = PlansPage()
        self._offline_page = OfflinePage()
        self._not_operator_page = NotOperatorPage()
        self._fleet_page = FleetPage()
        self._workspace_page = StationWorkspacePage()
        for page in (
            self._loading_page,
            self._auth_page,
            self._account_center,
            self._plans_page,
            self._offline_page,
            self._not_operator_page,
            self._fleet_page,
            self._workspace_page,
        ):
            self._stack.addWidget(page)

        self._wire_account_pages()
        self._wire_console_pages()
        language.changed.connect(self._retranslate)
        self._stack.currentChanged.connect(self._on_page_changed)

        if self._account:
            self._stack.setCurrentWidget(self._loading_page)
        else:
            self._stack.setCurrentWidget(self._fleet_page)

    # -- wiring -----------------------------------------------------------

    def _wire_account_pages(self) -> None:
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
        self._offline_page.retry_requested.connect(
            lambda: self._account and self._account.refresh(True)
        )
        self._offline_page.sign_out_requested.connect(self._request_sign_out)
        self._not_operator_page.sign_out_requested.connect(self._request_sign_out)
        self._not_operator_page.retry_requested.connect(
            lambda: self._account and self._account.refresh(True)
        )
        self._sign_out_ready.connect(self._finish_sign_out)

        if not self._account:
            return
        self._account.state_changed.connect(self._on_account_state)
        self._account.busy_changed.connect(self._auth_page.set_busy)
        self._account.notice.connect(self._on_account_notice)
        self._account.details_changed.connect(self._on_account_details)
        self._account.details_error.connect(
            lambda message: self._account_center.set_message(message, True)
        )
        self._account.details_loading.connect(self._account_center.set_loading)
        self._account.google_browser_requested.connect(self._open_google_authorization)
        self._account.google_flow_changed.connect(self._auth_page.set_google_waiting)
        self._account.google_flow_changed.connect(self._account_center.set_google_waiting)
        self._account.plans_changed.connect(self._on_plans_changed)
        self._account.plans_error.connect(
            lambda message: self._plans_page.set_message(message, True)
        )
        self._account.plans_loading.connect(self._plans_page.set_loading)

    def _wire_console_pages(self) -> None:
        self._fleet_page.attach_requested.connect(self.attach_station)
        self._fleet_page.refresh_requested.connect(self._refresh_fleet)
        self._fleet_page.filter_changed.connect(self._on_fleet_filter)
        self._fleet_page.account_requested.connect(self.open_account_center)
        self._workspace_page.back_requested.connect(self.detach_station)
        self._workspace_page.take_control_requested.connect(
            lambda: self._station and self._station.acquire_control(force=False)
        )
        self._workspace_page.force_control_requested.connect(self._confirm_force_takeover)
        self._workspace_page.release_control_requested.connect(
            lambda: self._station and self._station.release_control()
        )
        self._workspace_page.control_bar.toggle_requested.connect(
            lambda running: self._station and self._station.set_running(running)
        )
        self._workspace_page.control_bar.language_changed.connect(
            lambda code: self._station and self._station.set_target_language(code)
        )
        self._workspace_page.control_bar.capture_changed.connect(
            lambda mode, device: self._station and self._station.set_capture(mode, device)
        )
        self._workspace_page.control_bar.rescan_requested.connect(
            lambda: self._station and self._station.refresh_capabilities()
        )
        self._workspace_page.control_bar.retry_requested.connect(
            lambda: self._station and self._station.retry()
        )
        panel = self._workspace_page.tx_panel
        panel.record_pressed.connect(lambda: self._tx and self._tx.start_recording())
        panel.record_released.connect(lambda: self._tx and self._tx.stop_recording())
        panel.confirm_requested.connect(self._confirm_transmit)
        panel.cancel_requested.connect(lambda: self._tx and self._tx.cancel())
        panel.retry_requested.connect(lambda: self._tx and self._tx.retry())

    def _retranslate(self, *_args) -> None:
        if self._account_center_open and self._account and self._account.profile:
            message = self._account_status_message(self._account.profile, "")
            if message:
                self._account_center.set_message(message, True)

    # -- account ----------------------------------------------------------

    def start_account_flow(self) -> None:
        if self._account:
            self._account.initialize()

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
        elif self._account and self._account.state in (
            AccountState.RESTRICTED,
            AccountState.OFFLINE,
        ):
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
        self._auth_page.set_message(tr("account.google_browser_failed"), True)

    def _on_account_state(self, state: AccountState, profile: dict, message: str) -> None:
        if state == AccountState.LOADING:
            self._stack.setCurrentWidget(self._loading_page)
            return
        if state == AccountState.SIGNED_OUT:
            self._teardown_console()
            self._account_center_open = False
            self._plans_open = False
            self.account_active_changed.emit(False)
            self._auth_page.set_email(
                self._account.backend.auth.email if self._account else ""
            )
            if message:
                self._auth_page.set_message(message, True)
            self._stack.setCurrentWidget(self._auth_page)
            return
        if state == AccountState.OFFLINE:
            self.account_active_changed.emit(False)
            self._offline_page.set_message(message)
            self._stack.setCurrentWidget(self._offline_page)
            return
        if state == AccountState.RESTRICTED:
            self.account_active_changed.emit(False)
            self._teardown_console()
            first_open = not self._account_center_open
            self._account_center_open = True
            self._plans_open = False
            self._account_center.set_profile(profile)
            self._account_center.set_message(
                self._account_status_message(profile, message), True
            )
            self._stack.setCurrentWidget(self._account_center)
            if first_open and self._account:
                self._account.load_account_center()
            return
        if state == AccountState.ACTIVE:
            self._activate(profile)

    def _activate(self, profile: dict) -> None:
        uid = str(profile.get("uid") or "")
        self._operator_uid = uid
        if self._client is not None:
            self._client.operator_uid = uid
        self.account_active_changed.emit(True)

        if not profile.get("fleet_operator"):
            # A perfectly valid account that simply is not an operator.
            self._teardown_console()
            self._stack.setCurrentWidget(self._not_operator_page)
            return

        if self._account_center_open:
            self._stack.setCurrentWidget(self._account_center)
            return
        if self._plans_open:
            self._plans_page.set_profile(profile)
            self._stack.setCurrentWidget(self._plans_page)
            return

        self._ensure_fleet()
        self._stack.setCurrentWidget(self._fleet_page)

    # -- console ----------------------------------------------------------

    def _ensure_fleet(self) -> None:
        if self._fleet is not None or self._client is None:
            return
        self._fleet = FleetController(self._client, self)
        self._fleet.stations_changed.connect(
            lambda stations, _cursor: self._fleet_page.set_stations(stations)
        )
        self._fleet.loading.connect(self._fleet_page.set_loading)
        self._fleet.error.connect(lambda key: self._fleet_page.set_message(tr(key)))
        self._fleet.start()

    def _refresh_fleet(self) -> None:
        if self._fleet is not None:
            self._fleet.refresh()

    def _on_fleet_filter(self, query: str, online_only: bool) -> None:
        if self._fleet is not None:
            self._fleet.set_filter(query, online_only)

    def attach_station(self, station_id: str) -> None:
        if self._client is None:
            return
        self.detach_station(return_to_fleet=False)
        self._workspace_page.reset()
        self._station = StationController(self._client, station_id, self)
        self._station.station_changed.connect(self._workspace_page.set_station)
        self._station.results_changed.connect(self._workspace_page.set_results)
        self._station.phase_changed.connect(self._workspace_page.set_state)
        self._station.lease_changed.connect(
            lambda lease: self._workspace_page.set_lease(lease, self._operator_uid)
        )
        self._station.error.connect(
            lambda key: self._workspace_page.set_message(tr(key))
        )
        self._station.notice.connect(
            lambda key: self._workspace_page.set_message(tr(key))
        )
        self._station.station_changed.connect(self._sync_tx_readiness)
        self._station.lease_changed.connect(lambda _lease: self._sync_tx_readiness())

        from prana_windows.audio.tx_recorder import TxRecorder

        self._tx = TxController(self._client, station_id, TxRecorder(), self)
        self._tx.state_changed.connect(self._on_tx_state)
        self._tx.error.connect(lambda key: self._workspace_page.set_message(tr(key)))
        self._tx_confirmed_once = False

        self._station.attach()
        self._workspace_page.set_lease(None, self._operator_uid)
        self._on_tx_state(self._tx.state)
        if self._fleet is not None:
            self._fleet.pause()
        self._stack.setCurrentWidget(self._workspace_page)

    def detach_station(self, return_to_fleet: bool = True) -> None:
        if self._tx is not None:
            self._tx.shutdown()
            self._tx.deleteLater()
            self._tx = None
        if self._station is not None:
            self._station.detach()
            self._station.deleteLater()
            self._station = None
        if return_to_fleet:
            if self._fleet is not None:
                self._fleet.start()
                self._fleet.refresh()
            self._stack.setCurrentWidget(self._fleet_page)

    def _confirm_force_takeover(self) -> None:
        """Preemption always asks. Seizing a running radio is not a click."""
        if self._station is None:
            return
        answer = QMessageBox.question(
            self,
            tr("control.force_title"),
            tr(
                "control.force_body",
                holder=self._workspace_page.holder_label(),
                name=self._workspace_page.station_name(),
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._station.acquire_control(force=True)


    # -- TX ---------------------------------------------------------------

    def _sync_tx_readiness(self, *_args) -> None:
        if self._tx is None or self._station is None:
            return
        station = self._station.station
        if station is None:
            return
        self._tx.set_epoch(self._station.lease.epoch if self._station.lease else 0)
        self._tx.set_readiness(
            StationReadiness(
                online=station.is_online_at(datetime.now(timezone.utc)),
                running=station.desired.running,
                ptt_ready=station.ptt_ready,
                command_pending=station.command_pending,
                holds_control=self._station.holds_control,
            )
        )
        self._on_tx_state(self._tx.state)

    def _on_tx_state(self, state) -> None:
        if self._tx is None:
            return
        self._workspace_page.tx_panel.set_state(
            state, self._tx.can_record, self._tx.can_retry
        )

    def _confirm_transmit(self, translation: str) -> None:
        """Keying somebody else's transmitter asks once per attachment.

        Not once per transmission: an operator working a channel would click
        through a per-message dialog without reading it, which is worse than no
        dialog at all. Once, naming the Station and its owner, is the point
        where the consequence is actually considered.
        """
        if self._tx is None:
            return
        if not self._tx_confirmed_once:
            answer = QMessageBox.question(
                self,
                tr("tx.confirm_title"),
                tr(
                    "tx.confirm_body",
                    name=self._workspace_page.station_name(),
                    owner=self._workspace_page.owner_email(),
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            self._tx_confirmed_once = True
        self._tx.confirm(translation)

    def _teardown_console(self) -> None:
        self.detach_station(return_to_fleet=False)
        if self._fleet is not None:
            self._fleet.stop()
            self._fleet.deleteLater()
            self._fleet = None

    def _on_page_changed(self, _index: int) -> None:
        if self._station is None:
            return
        if self._stack.currentWidget() is self._workspace_page:
            self._station.resume_content()
        else:
            self._station.pause_content()

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt override
        # Minimising pauses the content polls but never lease renewal; losing
        # control because a window was tucked away would be worse than an
        # explicit release.
        if event.type() == QEvent.WindowStateChange and self._station is not None:
            if self.isMinimized():
                self._station.pause_content()
            elif self._stack.currentWidget() is self._workspace_page:
                self._station.resume_content()
        super().changeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._teardown_console()
        super().closeEvent(event)

    # -- sign out ---------------------------------------------------------

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

    def _begin_sign_out(self) -> None:
        if self._signing_out:
            return
        self._signing_out = True
        self._stack.setCurrentWidget(self._loading_page)
        station = self._station

        def worker() -> None:
            # Release the lease before dropping the session, so the Station is
            # not left pinned to an operator who has gone away.
            if station is not None:
                try:
                    station.detach()
                except Exception:  # noqa: BLE001
                    logger.debug("Detaching during sign out failed", exc_info=True)
            self._sign_out_ready.emit()

        threading.Thread(target=worker, daemon=True, name="sign-out").start()

    def _finish_sign_out(self) -> None:
        self._station = None
        self._teardown_console()
        self._signing_out = False
        self._account_center_open = False
        self._plans_open = False
        self._workspace_page.reset()
        self._operator_uid = ""
        if self._account:
            self._account.sign_out_local()

    def on_access_denied(self, code: str, message: str) -> None:
        del message
        if not self._account:
            return
        if code == "AUTH_REQUIRED":
            self._begin_sign_out()

    # -- account pages ----------------------------------------------------

    def open_account_center(self) -> None:
        if not self._account or self._account.state not in (
            AccountState.ACTIVE,
            AccountState.RESTRICTED,
        ):
            return
        self._account_center_open = True
        self._plans_open = False
        self._account_center.set_profile(
            self._account.profile or {},
            current_device_id=self._account.backend.local_device_id,
        )
        self._account_center.set_message("")
        self._stack.setCurrentWidget(self._account_center)
        self._account.load_account_center()

    def _close_account_center(self) -> None:
        if not self._account or self._account.state != AccountState.ACTIVE:
            return
        self._account_center_open = False
        self._plans_open = False
        if self._station is not None:
            self._stack.setCurrentWidget(self._workspace_page)
        else:
            self._ensure_fleet()
            self._stack.setCurrentWidget(self._fleet_page)

    def open_plans(self) -> None:
        if not self._account or self._account.state not in (
            AccountState.ACTIVE,
            AccountState.RESTRICTED,
        ):
            return
        self._account_center_open = False
        self._plans_open = True
        self._plans_page.set_profile(self._account.profile or {})
        self._plans_page.set_message("")
        self._stack.setCurrentWidget(self._plans_page)
        self._account.load_plans()

    def _back_to_account_center(self) -> None:
        if not self._account:
            return
        self._plans_open = False
        self.open_account_center()

    def _on_plans_changed(self, profile: dict, plans: list) -> None:
        self._plans_page.set_data(profile, plans)
        self._plans_page.set_message("")
        if self._plans_open:
            self._stack.setCurrentWidget(self._plans_page)

    def _on_account_details(self, profile: dict, devices: list, providers: list) -> None:
        current_device_id = ""
        if self._account and profile.get("email_verified"):
            current_device_id = self._account.backend.local_device_id
        self._account_center.set_profile(profile, devices, current_device_id, providers)
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


__all__ = ["MainWindow"]
