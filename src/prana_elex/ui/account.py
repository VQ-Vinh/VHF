from __future__ import annotations

import threading
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

from prana_elex.backend.auth import FirebaseAuthError
from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.backend.google_oauth import (
    GoogleOAuthAuthorization,
    GoogleOAuthError,
    GoogleOAuthSession,
)


class AccountState(Enum):
    LOADING = auto()
    SIGNED_OUT = auto()
    RESTRICTED = auto()
    ACTIVE = auto()
    OFFLINE = auto()


class AccountController(QObject):
    state_changed = Signal(object, object, str)
    busy_changed = Signal(bool)
    notice = Signal(str, bool)
    details_changed = Signal(object, object, object)
    details_error = Signal(str)
    details_loading = Signal(bool)
    google_browser_requested = Signal(str)
    google_flow_changed = Signal(bool)
    plans_changed = Signal(object, object)
    plans_error = Signal(str)
    plans_loading = Signal(bool)

    def __init__(self, backend: BackendClient, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.state = AccountState.LOADING
        self.profile: dict | None = None
        self._busy = False
        self._lock = threading.Lock()
        self._details_busy = False
        self._details_lock = threading.Lock()
        self._google_session: GoogleOAuthSession | None = None
        self._google_lock = threading.Lock()
        self._plans_busy = False
        self._plans_lock = threading.Lock()

    def _emit_state(self, state: AccountState, profile: dict | None = None, message: str = "") -> None:
        self.state = state
        self.profile = profile
        self.state_changed.emit(state, profile or {}, message)

    def _start(self, worker) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True
        self.busy_changed.emit(True)

        def run() -> None:
            try:
                worker()
            finally:
                with self._lock:
                    self._busy = False
                self.busy_changed.emit(False)

        threading.Thread(target=run, daemon=True).start()

    def _start_details(self, worker) -> None:
        with self._details_lock:
            if self._details_busy:
                return
            self._details_busy = True
        self.details_loading.emit(True)

        def run() -> None:
            try:
                worker()
            finally:
                with self._details_lock:
                    self._details_busy = False
                self.details_loading.emit(False)

        threading.Thread(target=run, daemon=True).start()

    def _start_plans(self, worker) -> None:
        with self._plans_lock:
            if self._plans_busy:
                return
            self._plans_busy = True
        self.plans_loading.emit(True)

        def run() -> None:
            try:
                worker()
            finally:
                with self._plans_lock:
                    self._plans_busy = False
                self.plans_loading.emit(False)

        threading.Thread(target=run, daemon=True).start()

    def initialize(self) -> None:
        if not self.backend.auth.has_session:
            self._emit_state(AccountState.SIGNED_OUT)
            return
        self.refresh(show_loading=True)

    def _load_profile(self) -> None:
        try:
            profile = self.backend.me()
            self.profile = profile
            if profile.get("email_verified") and profile.get("status") == "active":
                self.backend.ensure_device()
                self._emit_state(AccountState.ACTIVE, profile)
            else:
                self._emit_state(AccountState.RESTRICTED, profile, self._status_message(profile))
        except BackendApiError as exc:
            if exc.code == "NETWORK_ERROR":
                self._emit_state(AccountState.OFFLINE, self.profile, str(exc))
            elif exc.code in {"DEVICE_REVOKED", "DEVICE_LIMIT_REACHED", "EMAIL_NOT_VERIFIED", "SUBSCRIPTION_INACTIVE"}:
                self._emit_state(AccountState.RESTRICTED, self.profile, f"{exc.code}: {exc}")
            else:
                self.backend.sign_out()
                self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
        except FirebaseAuthError as exc:
            if exc.code == "NETWORK_ERROR":
                self._emit_state(AccountState.OFFLINE, self.profile, str(exc))
            else:
                self.backend.sign_out()
                self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
        except Exception as exc:
            self._emit_state(AccountState.OFFLINE, self.profile, str(exc))

    @staticmethod
    def _status_message(profile: dict) -> str:
        if not profile.get("email_verified"):
            return "Verify your email before using PRANA ELEX."
        status = profile.get("status", "pending_payment")
        messages = {
            "pending_payment": "Your account is waiting for plan activation.",
            "expired": "Your subscription has expired.",
            "suspended": "Your subscription has been suspended.",
            "registered": "Verify your email before continuing.",
            "email_verified": "Your account is waiting for plan activation.",
        }
        return messages.get(status, "Your subscription is not active.")

    def refresh(self, show_loading: bool = False) -> None:
        if show_loading:
            self._emit_state(AccountState.LOADING, self.profile)
        self.backend.reset_registration()
        self._start(self._load_profile)

    def sign_in(self, email: str, password: str) -> None:
        def worker() -> None:
            try:
                self.backend.auth.sign_in(email, password)
                self.backend.reset_registration()
                self._load_profile()
            except Exception as exc:
                self.notice.emit(str(exc), True)

        self._start(worker)

    def sign_up(self, email: str, password: str) -> None:
        def worker() -> None:
            try:
                self.backend.auth.sign_up(email, password)
                self.backend.reset_registration()
                self.notice.emit("Account created. Check your inbox to verify your email.", False)
                self._load_profile()
            except Exception as exc:
                self.notice.emit(str(exc), True)

        self._start(worker)

    def sign_in_with_google(self) -> None:
        def worker() -> None:
            try:
                authorization = self._authorize_google()
                is_new = self.backend.sign_in_with_google(authorization)
                self.backend.reset_registration()
                if is_new:
                    self.notice.emit("GOOGLE:ACCOUNT_CREATED", False)
                self._load_profile()
            except (GoogleOAuthError, FirebaseAuthError, BackendApiError) as exc:
                code = getattr(exc, "code", "GOOGLE_AUTH_FAILED")
                self.notice.emit(f"GOOGLE:{code}", code != "GOOGLE_AUTH_CANCELLED")
            except Exception:
                self.notice.emit("GOOGLE:GOOGLE_AUTH_FAILED", True)

        self._start(worker)

    def link_google_account(self) -> None:
        def worker() -> None:
            try:
                authorization = self._authorize_google()
                self.backend.link_google(authorization)
                profile, devices, providers = self._load_account_details()
                self.details_changed.emit(profile, devices, providers)
                self.notice.emit("GOOGLE:GOOGLE_LINKED", False)
            except (GoogleOAuthError, FirebaseAuthError, BackendApiError) as exc:
                code = getattr(exc, "code", "GOOGLE_LINK_FAILED")
                self.notice.emit(f"GOOGLE:{code}", code != "GOOGLE_AUTH_CANCELLED")
            except Exception:
                self.notice.emit("GOOGLE:GOOGLE_LINK_FAILED", True)

        self._start_details(worker)

    def _authorize_google(self) -> GoogleOAuthAuthorization:
        session = self.backend.auth.begin_google_oauth()
        with self._google_lock:
            self._google_session = session
        self.google_flow_changed.emit(True)
        self.google_browser_requested.emit(session.authorization_url)
        try:
            return session.wait()
        finally:
            with self._google_lock:
                self._google_session = None
            self.google_flow_changed.emit(False)

    def cancel_google_oauth(
        self,
        code: str = "GOOGLE_AUTH_CANCELLED",
        message: str = "Google sign-in was cancelled",
    ) -> None:
        with self._google_lock:
            session = self._google_session
        if session is not None:
            session.cancel(code, message)

    def resend_verification(self) -> None:
        def worker() -> None:
            try:
                self.backend.auth.send_verification_email()
                self.notice.emit("A new verification email was sent.", False)
            except Exception as exc:
                self.notice.emit(str(exc), True)

        self._start(worker)

    def request_password_reset(self, email: str) -> None:
        def worker() -> None:
            try:
                self.backend.auth.request_password_reset(email)
                self.notice.emit("If the account exists, a password reset email has been sent.", False)
            except Exception:
                self.notice.emit("If the account exists, a password reset email has been sent.", False)

        self._start(worker)

    def load_account_center(self) -> None:
        def worker() -> None:
            try:
                profile, devices, providers = self._load_account_details()
                message = self._status_message(profile) if profile.get("status") != "active" else ""
                self.details_changed.emit(profile, devices, providers)
                if profile.get("email_verified") and profile.get("status") == "active":
                    self.backend.ensure_device()
                    self._emit_state(AccountState.ACTIVE, profile)
                else:
                    self._emit_state(AccountState.RESTRICTED, profile, message)
            except BackendApiError as exc:
                if exc.code == "NETWORK_ERROR":
                    self.details_error.emit(str(exc))
                elif exc.code == "AUTH_REQUIRED" or exc.status == 401:
                    self.backend.sign_out()
                    self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
                elif exc.code in {
                    "EMAIL_NOT_VERIFIED",
                    "SUBSCRIPTION_INACTIVE",
                    "DEVICE_REVOKED",
                    "DEVICE_LIMIT_REACHED",
                }:
                    self.details_error.emit(str(exc))
                    self._emit_state(AccountState.RESTRICTED, self.profile, str(exc))
                else:
                    self.details_error.emit(str(exc))
            except FirebaseAuthError as exc:
                if exc.code == "NETWORK_ERROR":
                    self.details_error.emit(str(exc))
                else:
                    self.backend.sign_out()
                    self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
            except Exception as exc:
                self.details_error.emit(str(exc))

        self._start_details(worker)

    def load_plans(self) -> None:
        def worker() -> None:
            try:
                plans = self.backend.list_plans()
                self.plans_changed.emit(dict(self.profile or {}), plans)
            except (BackendApiError, FirebaseAuthError) as exc:
                if getattr(exc, "code", "") == "AUTH_REQUIRED" or getattr(exc, "status", 0) == 401:
                    self.backend.sign_out()
                    self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
                else:
                    self.plans_error.emit(str(exc))
            except Exception as exc:
                self.plans_error.emit(str(exc))

        self._start_plans(worker)

    def select_plan(self, plan_id: str) -> None:
        def worker() -> None:
            try:
                profile = self.backend.select_plan(plan_id)
                plans = self.backend.list_plans()
                self.profile = profile
                self.plans_changed.emit(profile, plans)
                self.backend.reset_registration()
                if profile.get("email_verified") and profile.get("status") == "active":
                    self.backend.ensure_device()
                    self._emit_state(AccountState.ACTIVE, profile)
                else:
                    self._emit_state(
                        AccountState.RESTRICTED,
                        profile,
                        self._status_message(profile),
                    )
            except (BackendApiError, FirebaseAuthError) as exc:
                self.plans_error.emit(str(exc))
            except Exception as exc:
                self.plans_error.emit(str(exc))

        self._start_plans(worker)

    def _load_account_details(self) -> tuple[dict, list[dict], list[str]]:
        profile = self.backend.me()
        self.profile = profile
        devices = self.backend.list_devices() if profile.get("email_verified") else []
        providers = self.backend.auth.provider_ids()
        return profile, devices, providers

    def revoke_account_device(self, device_id: str) -> None:
        def worker() -> None:
            try:
                if device_id == self.backend.local_device_id:
                    self.notice.emit("The current device cannot be revoked here.", True)
                    return
                self.backend.revoke_device(device_id)
                profile, devices, providers = self._load_account_details()
                self.details_changed.emit(profile, devices, providers)
                self.notice.emit("Device revoked.", False)
            except BackendApiError as exc:
                self.details_error.emit(str(exc))
            except FirebaseAuthError as exc:
                if exc.code == "NETWORK_ERROR":
                    self.details_error.emit(str(exc))
                else:
                    self.backend.sign_out()
                    self._emit_state(AccountState.SIGNED_OUT, message=str(exc))
            except Exception as exc:
                self.details_error.emit(str(exc))

        self._start_details(worker)

    def sign_out_local(self) -> None:
        self.backend.sign_out()
        self._emit_state(AccountState.SIGNED_OUT)

    def restrict(self, code: str, message: str) -> None:
        self._emit_state(AccountState.RESTRICTED, self.profile, f"{code}: {message}")


__all__ = ["AccountController", "AccountState"]
