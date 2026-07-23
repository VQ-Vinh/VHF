from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
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

from prana_windows.ui.icons import phosphor_icon
from prana_windows.ui.i18n import language, tr


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
    google_requested = Signal()
    google_cancel_requested = Signal()

    def __init__(self, google_enabled: bool = False, parent=None):
        super().__init__(parent)
        self.card.setMinimumHeight(680)
        self._google_enabled = google_enabled
        self._google_waiting = False
        self.add_title(tr("account.welcome"), tr("account.subtitle"))

        google_row = QHBoxLayout()
        google_row.setSpacing(10)
        self._google = QPushButton()
        self._google.setObjectName("GoogleButton")
        self._google.setCursor(Qt.PointingHandCursor)
        icon_path = Path(__file__).resolve().parents[1] / "resources" / "google-g.svg"
        self._google.setIcon(QIcon(str(icon_path)))
        self._google.setIconSize(QSize(20, 20))
        self._google.clicked.connect(self.google_requested)
        self._cancel_google = QPushButton()
        self._cancel_google.setObjectName("GoogleCancelButton")
        self._cancel_google.clicked.connect(self.google_cancel_requested)
        self._cancel_google.setVisible(False)
        google_row.addWidget(self._google, stretch=1)
        google_row.addWidget(self._cancel_google)
        self.content.addLayout(google_row)

        self._google_divider = QWidget()
        divider_layout = QHBoxLayout(self._google_divider)
        divider_layout.setContentsMargins(0, 0, 0, 0)
        divider_layout.setSpacing(12)
        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)
        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)
        self._divider_text = QLabel()
        self._divider_text.setObjectName("AuthDividerText")
        divider_layout.addWidget(left_line, stretch=1)
        divider_layout.addWidget(self._divider_text)
        divider_layout.addWidget(right_line, stretch=1)
        self.content.addWidget(self._google_divider)

        self._google.setVisible(google_enabled)
        self._google_divider.setVisible(google_enabled)
        self._tabs = QTabWidget()
        self._tabs.setMinimumHeight(390)
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
        self._register_password.setPlaceholderText(tr("account.password_placeholder"))
        self._register_email_label = QLabel()
        self._register_password_label = QLabel()
        register_form.addRow(self._register_email_label, self._register_email)
        register_form.addRow(self._register_password_label, self._register_password)
        self._password_requirements = QLabel()
        self._password_requirements.setObjectName("PasswordRequirements")
        self._password_requirements.setTextFormat(Qt.RichText)
        self._password_requirements.setWordWrap(True)
        register_form.addRow("", self._password_requirements)
        self._show_register = QPushButton()
        self._configure_password_toggle(self._show_register, self._register_password)
        register_form.addRow("", self._show_register)
        self._create = QPushButton()
        self._create.setObjectName("PrimaryButton")
        self._create.clicked.connect(self._emit_sign_up)
        register_form.addRow("", self._create)
        self._tabs.addTab(register, "")

        self._busy = False
        self._register_email.textChanged.connect(self._update_registration_state)
        self._register_password.textChanged.connect(self._update_registration_state)

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
        self._register_password.setPlaceholderText(tr("account.password_placeholder"))
        self._show_login.setText(tr("account.show_password"))
        self._show_register.setText(tr("account.show_password"))
        self._forgot_password.setText(tr("account.forgot"))
        self._sign_in.setText(tr("account.sign_in"))
        self._create.setText(tr("account.create"))
        self._google.setText(
            tr("account.google_waiting")
            if self._google_waiting
            else tr("account.continue_google")
        )
        self._cancel_google.setText(tr("common.cancel"))
        self._divider_text.setText(tr("account.continue_email"))
        self._tabs.setTabText(0, tr("account.sign_in"))
        self._tabs.setTabText(1, tr("account.create"))
        self._update_registration_state()

    @staticmethod
    def _valid_login(email: str, password: str) -> bool:
        return bool(email and "@" in email and len(password) >= 6)

    @staticmethod
    def _password_checks(password: str) -> dict[str, bool]:
        return {
            "length": len(password) >= 6,
            "letter": any(char.isalpha() for char in password),
            "uppercase": any(char.isalpha() and char.isupper() for char in password),
            "number": any(char.isdigit() for char in password),
            "special": any(not char.isalnum() and not char.isspace() for char in password),
        }

    @classmethod
    def _valid_registration(cls, email: str, password: str) -> bool:
        return bool(
            email
            and "@" in email
            and all(cls._password_checks(password).values())
        )

    def _update_registration_state(self, *_args) -> None:
        checks = self._password_checks(self._register_password.text())
        rows = []
        for key, passed in checks.items():
            color = "#21835A" if passed else "#A42A3A"
            marker = "&#10003;" if passed else "&#9675;"
            rows.append(
                f'<span style="color:{color}">{marker} {tr(f"account.password_{key}")}</span>'
            )
        self._password_requirements.setText("<br>".join(rows))
        valid = self._valid_registration(
            self._register_email.text().strip(), self._register_password.text()
        )
        self._create.setEnabled(not self._busy and valid)

    def _emit_sign_in(self) -> None:
        email, password = self._login_email.text().strip(), self._login_password.text()
        if not self._valid_login(email, password):
            self.set_message(tr("account.invalid"), True)
            return
        self.sign_in_requested.emit(email, password)

    def _emit_sign_up(self) -> None:
        email, password = self._register_email.text().strip(), self._register_password.text()
        if not self._valid_registration(email, password):
            self.set_message(tr("account.invalid_registration"), True)
            return
        self.sign_up_requested.emit(email, password)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._tabs.setEnabled(not busy)
        self._sign_in.setText(tr("account.signing_in") if busy else tr("account.sign_in"))
        self._google.setEnabled(self._google_enabled and not busy)
        self._cancel_google.setEnabled(self._google_waiting)
        self._update_registration_state()

    def set_google_waiting(self, waiting: bool) -> None:
        self._google_waiting = waiting
        self._google.setText(
            tr("account.google_waiting") if waiting else tr("account.continue_google")
        )
        self._cancel_google.setVisible(waiting)
        self._cancel_google.setEnabled(waiting)

    def set_message(self, message: str, error: bool = False) -> None:
        self._message.setText(message)
        self._message.setStyleSheet(f"color: {'#C34655' if error else '#21835A'};")

    def set_email(self, email: str) -> None:
        if email:
            self._login_email.setText(email)


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
