from __future__ import annotations

import threading
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

from prana_elex.backend.auth import FirebaseAuthError
from prana_elex.backend.client import BackendApiError, BackendClient


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

    def __init__(self, backend: BackendClient, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.state = AccountState.LOADING
        self.profile: dict | None = None
        self._busy = False
        self._lock = threading.Lock()

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

    def sign_out_local(self) -> None:
        self.backend.sign_out()
        self._emit_state(AccountState.SIGNED_OUT)

    def restrict(self, code: str, message: str) -> None:
        self._emit_state(AccountState.RESTRICTED, self.profile, f"{code}: {message}")


__all__ = ["AccountController", "AccountState"]
