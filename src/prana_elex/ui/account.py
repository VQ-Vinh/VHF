from __future__ import annotations

import threading
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from prana_elex.backend.auth import FirebaseAuthError
from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.ui.icons import phosphor_icon
from prana_elex.ui.i18n import language, tr


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
                # Do not reveal whether an email address is registered.
                self.notice.emit("If the account exists, a password reset email has been sent.", False)

        self._start(worker)

    def sign_out_local(self) -> None:
        self.backend.sign_out()
        self._emit_state(AccountState.SIGNED_OUT)

    def restrict(self, code: str, message: str) -> None:
        self._emit_state(AccountState.RESTRICTED, self.profile, f"{code}: {message}")


class _CenteredPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.addStretch()
        self.card = QFrame()
        self.card.setObjectName("AccountCard")
        self.card.setMinimumWidth(680)
        self.card.setMaximumWidth(760)
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.content = QVBoxLayout(self.card)
        self.content.setContentsMargins(32, 30, 32, 30)
        self.content.setSpacing(14)
        locale_row = QHBoxLayout()
        locale_row.addStretch()
        self._locale = QComboBox()
        self._locale.setObjectName("LocaleSelector")
        self._locale.addItem("EN", "en")
        self._locale.addItem("VI", "vi")
        self._locale.setCurrentIndex(0 if language.locale == "en" else 1)
        self._locale.currentIndexChanged.connect(lambda: language.set_locale(self._locale.currentData()))
        language.changed.connect(self._sync_locale)
        locale_row.addWidget(self._locale)
        self.content.addLayout(locale_row)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.card)
        row.addStretch()
        outer.addLayout(row)
        outer.addStretch()

    def _sync_locale(self, locale: str) -> None:
        index = self._locale.findData(locale)
        if index >= 0 and index != self._locale.currentIndex():
            self._locale.blockSignals(True)
            self._locale.setCurrentIndex(index)
            self._locale.blockSignals(False)

    def add_title(self, title: str, subtitle: str = "") -> None:
        self._page_title = QLabel(title)
        self._page_title.setObjectName("AccountTitle")
        self.content.addWidget(self._page_title)
        if subtitle:
            self._page_subtitle = QLabel(subtitle)
            self._page_subtitle.setObjectName("AccountSubtitle")
            self._page_subtitle.setWordWrap(True)
            self.content.addWidget(self._page_subtitle)


class LoadingPage(_CenteredPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title("PRANA ELEX", tr("account.checking"))
        language.changed.connect(lambda: self._page_subtitle.setText(tr("account.checking")))


class AuthPage(_CenteredPage):
    sign_in_requested = Signal(str, str)
    sign_up_requested = Signal(str, str)
    reset_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card.setMinimumHeight(520)
        self.add_title(tr("account.welcome"), tr("account.subtitle"))
        self._tabs = QTabWidget()
        self._tabs.setMinimumHeight(310)
        self._tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.addWidget(self._tabs)

        login = QWidget()
        login_form = QFormLayout(login)
        login_form.setContentsMargins(18, 20, 18, 18)
        login_form.setHorizontalSpacing(18)
        login_form.setVerticalSpacing(14)
        self._login_email = QLineEdit()
        self._login_email.setPlaceholderText("name@example.com")
        self._login_password = QLineEdit()
        self._login_password.setEchoMode(QLineEdit.Password)
        self._login_password.setPlaceholderText("Password")
        self._login_email_label = QLabel()
        self._login_password_label = QLabel()
        login_form.addRow(self._login_email_label, self._login_email)
        login_form.addRow(self._login_password_label, self._login_password)
        self._show_login = QPushButton()
        self._configure_password_toggle(self._show_login, self._login_password)
        login_form.addRow("", self._show_login)
        login_actions = QHBoxLayout()
        self._forgot_password = QPushButton()
        self._forgot_password.clicked.connect(lambda: self.reset_requested.emit(self._login_email.text().strip()))
        self._sign_in = QPushButton()
        self._sign_in.setObjectName("PrimaryButton")
        self._sign_in.clicked.connect(self._emit_sign_in)
        login_actions.setContentsMargins(0, 8, 0, 0)
        login_actions.addWidget(self._forgot_password)
        login_actions.addStretch()
        login_actions.addWidget(self._sign_in)
        login_form.addRow(login_actions)
        self._tabs.addTab(login, "")

        register = QWidget()
        register_form = QFormLayout(register)
        register_form.setContentsMargins(18, 20, 18, 18)
        register_form.setHorizontalSpacing(18)
        register_form.setVerticalSpacing(14)
        self._register_email = QLineEdit()
        self._register_email.setPlaceholderText("name@example.com")
        self._register_password = QLineEdit()
        self._register_password.setEchoMode(QLineEdit.Password)
        self._register_password.setPlaceholderText("At least 6 characters")
        self._register_email_label = QLabel()
        self._register_password_label = QLabel()
        register_form.addRow(self._register_email_label, self._register_email)
        register_form.addRow(self._register_password_label, self._register_password)
        self._show_register = QPushButton()
        self._configure_password_toggle(self._show_register, self._register_password)
        register_form.addRow("", self._show_register)
        self._create = QPushButton()
        self._create.setObjectName("PrimaryButton")
        self._create.clicked.connect(self._emit_sign_up)
        register_form.addRow("", self._create)
        self._tabs.addTab(register, "")

        self._message = QLabel()
        self._message.setWordWrap(True)
        self.content.addWidget(self._message)
        language.changed.connect(self._retranslate)
        self._retranslate()

    @staticmethod
    def _configure_password_toggle(toggle: QPushButton, field: QLineEdit) -> None:
        toggle.setObjectName("PasswordToggle")
        toggle.setCheckable(True)
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.setIconSize(QSize(17, 17))

        def update(shown: bool) -> None:
            field.setEchoMode(QLineEdit.Normal if shown else QLineEdit.Password)
            toggle.setIcon(
                phosphor_icon(
                    "ph.eye-slash" if shown else "ph.eye",
                    color="#355762",
                    active_color="#007B87",
                    scale_factor=0.9,
                )
            )

        toggle.toggled.connect(update)
        update(False)

    def _retranslate(self, *_args) -> None:
        self._page_title.setText(tr("account.welcome"))
        self._page_subtitle.setText(tr("account.subtitle"))
        self._login_email_label.setText(tr("account.email"))
        self._login_password_label.setText(tr("account.password"))
        self._register_email_label.setText(tr("account.email"))
        self._register_password_label.setText(tr("account.password"))
        self._show_login.setText(tr("account.show_password"))
        self._show_register.setText(tr("account.show_password"))
        self._forgot_password.setText(tr("account.forgot"))
        self._sign_in.setText(tr("account.sign_in"))
        self._create.setText(tr("account.create"))
        self._tabs.setTabText(0, tr("account.sign_in"))
        self._tabs.setTabText(1, tr("account.create"))

    @staticmethod
    def _valid(email: str, password: str) -> bool:
        return bool(email and "@" in email and len(password) >= 6)

    def _emit_sign_in(self) -> None:
        email, password = self._login_email.text().strip(), self._login_password.text()
        if not self._valid(email, password):
            self.set_message(tr("account.invalid"), True)
            return
        self.sign_in_requested.emit(email, password)

    def _emit_sign_up(self) -> None:
        email, password = self._register_email.text().strip(), self._register_password.text()
        if not self._valid(email, password):
            self.set_message(tr("account.invalid"), True)
            return
        self.sign_up_requested.emit(email, password)

    def set_busy(self, busy: bool) -> None:
        self._tabs.setEnabled(not busy)
        self._sign_in.setText(tr("account.signing_in") if busy else tr("account.sign_in"))

    def set_message(self, message: str, error: bool = False) -> None:
        self._message.setText(message)
        self._message.setStyleSheet(f"color: {'#C34655' if error else '#21835A'};")

    def set_email(self, email: str) -> None:
        if email:
            self._login_email.setText(email)


class AccountStatusPage(_CenteredPage):
    refresh_requested = Signal()
    resend_requested = Signal()
    sign_out_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title(tr("account.status"))
        self._email = QLabel("—")
        self._status = QLabel("—")
        self._expiry = QLabel("—")
        self._usage = QLabel("—")
        form = QFormLayout()
        self._account_label = QLabel()
        self._status_label = QLabel()
        self._expires_label = QLabel()
        self._usage_label = QLabel()
        form.addRow(self._account_label, self._email)
        form.addRow(self._status_label, self._status)
        form.addRow(self._expires_label, self._expiry)
        form.addRow(self._usage_label, self._usage)
        self.content.addLayout(form)
        self._message = QLabel()
        self._message.setWordWrap(True)
        self.content.addWidget(self._message)
        actions = QHBoxLayout()
        self._resend = QPushButton()
        self._resend.clicked.connect(self.resend_requested)
        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.refresh_requested)
        self._sign_out = QPushButton()
        self._sign_out.clicked.connect(self.sign_out_requested)
        actions.addWidget(self._resend)
        actions.addStretch()
        actions.addWidget(self._sign_out)
        actions.addWidget(self._refresh)
        self.content.addLayout(actions)
        language.changed.connect(self._retranslate)
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        self._page_title.setText(tr("account.status"))
        self._account_label.setText(tr("settings.account"))
        self._status_label.setText(tr("common.status"))
        self._expires_label.setText(tr("settings.expires"))
        self._usage_label.setText(tr("settings.usage"))
        self._resend.setText(tr("account.resend"))
        self._refresh.setText(tr("common.refresh"))
        self._sign_out.setText(tr("common.sign_out"))

    def set_profile(self, profile: dict, message: str = "") -> None:
        usage = profile.get("usage") or {}
        used = int(usage.get("used_audio_seconds", 0)) / 60
        remaining = int(usage.get("remaining_audio_seconds", 0)) / 60
        self._email.setText(profile.get("email") or "—")
        self._status.setText(profile.get("status") or "restricted")
        self._expiry.setText(str(profile.get("subscription_expires_at") or "—"))
        self._usage.setText(f"{used:.1f} min used / {remaining:.1f} min remaining")
        self._message.setText(message)
        self._resend.setVisible(not bool(profile.get("email_verified")))


class OfflinePage(_CenteredPage):
    retry_requested = Signal()
    sign_out_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title(tr("account.offline"), tr("account.offline_body"))
        self._message = QLabel()
        self._message.setWordWrap(True)
        self.content.addWidget(self._message)
        row = QHBoxLayout()
        self._sign_out = QPushButton(tr("common.sign_out"))
        self._sign_out.clicked.connect(self.sign_out_requested)
        self._retry = QPushButton(tr("common.retry"))
        self._retry.setObjectName("PrimaryButton")
        self._retry.clicked.connect(self.retry_requested)
        row.addStretch()
        row.addWidget(self._sign_out)
        row.addWidget(self._retry)
        self.content.addLayout(row)
        language.changed.connect(self._retranslate)

    def _retranslate(self, *_args) -> None:
        self._page_title.setText(tr("account.offline"))
        self._page_subtitle.setText(tr("account.offline_body"))
        self._sign_out.setText(tr("common.sign_out"))
        self._retry.setText(tr("common.retry"))

    def set_message(self, message: str) -> None:
        self._message.setText(message)


class DataSetupPage(_CenteredPage):
    saved = Signal(str)

    def __init__(self, default_path: str, parent=None):
        super().__init__(parent)
        self.add_title(tr("account.data_title"), tr("account.data_body"))
        row = QHBoxLayout()
        self._path = QLineEdit(default_path)
        self._browse_button = QPushButton(tr("account.browse"))
        self._browse_button.clicked.connect(self._browse)
        row.addWidget(self._path)
        row.addWidget(self._browse_button)
        self.content.addLayout(row)
        self._save_button = QPushButton(tr("common.save"))
        self._save_button.setObjectName("PrimaryButton")
        self._save_button.clicked.connect(self._save)
        self.content.addWidget(self._save_button, alignment=Qt.AlignRight)
        self._message = QLabel()
        self.content.addWidget(self._message)
        language.changed.connect(self._retranslate)

    def _retranslate(self, *_args) -> None:
        self._page_title.setText(tr("account.data_title"))
        self._page_subtitle.setText(tr("account.data_body"))
        self._browse_button.setText(tr("account.browse"))
        self._save_button.setText(tr("common.save"))

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select data folder", self._path.text())
        if selected:
            self._path.setText(selected)

    def _save(self) -> None:
        try:
            path = Path(self._path.text().strip()).expanduser().resolve()
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".prana-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            self._message.setText(f"Cannot use this folder: {exc}")
            return
        self.saved.emit(str(path))


class ConfigErrorPage(_CenteredPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title(
            "Installation configuration missing",
            "Run the PRANA ELEX installer again and choose a Data folder.",
        )
