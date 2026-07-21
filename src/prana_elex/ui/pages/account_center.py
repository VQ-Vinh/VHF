from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prana_elex.ui.i18n import language, tr


def _format_datetime(value: object) -> str:
    if not value:
        return "—"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


class AccountCenterPage(QWidget):
    refresh_requested = Signal()
    reset_requested = Signal(str)
    resend_requested = Signal()
    revoke_requested = Signal(str)
    sign_out_requested = Signal()
    back_requested = Signal()
    link_google_requested = Signal()
    google_cancel_requested = Signal()
    manage_plan_requested = Signal()

    def __init__(self, google_enabled: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("AccountCenterPage")
        self._profile: dict = {}
        self._devices: list[dict] = []
        self._current_device_id = ""
        self._providers: list[str] = []
        self._google_enabled = google_enabled
        self._google_waiting = False
        self._message_text = ""
        self._message_error = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        top = QHBoxLayout()
        self._back = QPushButton()
        self._back.setObjectName("AccountBackButton")
        self._back.clicked.connect(self.back_requested)
        top.addWidget(self._back)
        top.addStretch()
        self._locale = QComboBox()
        self._locale.setObjectName("LocaleSelector")
        self._locale.addItem("EN", "en")
        self._locale.addItem("VI", "vi")
        self._locale.setCurrentIndex(0 if language.locale == "en" else 1)
        self._locale.currentIndexChanged.connect(
            lambda: language.set_locale(self._locale.currentData())
        )
        top.addWidget(self._locale)
        root.addLayout(top)

        scroll = QScrollArea()
        scroll.setObjectName("AccountCenterScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("AccountCenterBody")
        self._content = QVBoxLayout(body)
        self._content.setContentsMargins(0, 0, 0, 8)
        self._content.setSpacing(14)

        self._title = QLabel()
        self._title.setObjectName("AccountCenterTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("AccountCenterSubtitle")
        self._content.addWidget(self._title)
        self._content.addWidget(self._subtitle)

        self._message = QLabel()
        self._message.setObjectName("AccountCenterMessage")
        self._message.setWordWrap(True)
        self._message.setVisible(False)
        self._content.addWidget(self._message)

        profile_card = QFrame()
        profile_card.setObjectName("AccountCenterCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(20, 18, 20, 18)
        profile_layout.setSpacing(10)
        self._profile_heading = QLabel()
        self._profile_heading.setObjectName("AccountCenterSectionTitle")
        profile_layout.addWidget(self._profile_heading)
        self._email = self._detail_row(profile_layout)
        self._verified = self._detail_row(profile_layout)
        self._subscription = self._detail_row(profile_layout)
        self._plan = self._detail_row(profile_layout)
        self._expires = self._detail_row(profile_layout)
        self._content.addWidget(profile_card)

        self._login_methods_card = QFrame()
        self._login_methods_card.setObjectName("AccountCenterCard")
        login_methods_layout = QVBoxLayout(self._login_methods_card)
        login_methods_layout.setContentsMargins(20, 18, 20, 18)
        login_methods_layout.setSpacing(10)
        self._login_methods_heading = QLabel()
        self._login_methods_heading.setObjectName("AccountCenterSectionTitle")
        login_methods_layout.addWidget(self._login_methods_heading)
        password_row = QHBoxLayout()
        self._password_method = QLabel()
        self._password_method.setObjectName("AccountCenterValue")
        self._password_status = QLabel()
        self._password_status.setObjectName("DeviceBadge")
        password_row.addWidget(self._password_method)
        password_row.addStretch()
        password_row.addWidget(self._password_status)
        login_methods_layout.addLayout(password_row)
        google_row = QHBoxLayout()
        self._google_method = QLabel("Google")
        self._google_method.setObjectName("AccountCenterValue")
        self._google_status = QLabel()
        self._google_status.setObjectName("DeviceBadge")
        self._link_google = QPushButton()
        self._link_google.setObjectName("GoogleLinkButton")
        self._link_google.clicked.connect(self.link_google_requested)
        self._cancel_google = QPushButton()
        self._cancel_google.clicked.connect(self.google_cancel_requested)
        self._cancel_google.setVisible(False)
        google_row.addWidget(self._google_method)
        google_row.addStretch()
        google_row.addWidget(self._google_status)
        google_row.addWidget(self._link_google)
        google_row.addWidget(self._cancel_google)
        login_methods_layout.addLayout(google_row)
        self._login_methods_card.setVisible(google_enabled)
        self._content.addWidget(self._login_methods_card)

        usage_card = QFrame()
        usage_card.setObjectName("AccountCenterCard")
        usage_layout = QVBoxLayout(usage_card)
        usage_layout.setContentsMargins(20, 18, 20, 18)
        usage_layout.setSpacing(10)
        self._usage_heading = QLabel()
        self._usage_heading.setObjectName("AccountCenterSectionTitle")
        usage_layout.addWidget(self._usage_heading)
        self._usage_progress = QProgressBar()
        self._usage_progress.setObjectName("UsageProgress")
        self._usage_progress.setTextVisible(False)
        usage_layout.addWidget(self._usage_progress)
        self._usage_text = QLabel("—")
        self._usage_text.setObjectName("AccountCenterMuted")
        usage_layout.addWidget(self._usage_text)
        self._usage_reset = QLabel("—")
        self._usage_reset.setObjectName("AccountCenterMuted")
        usage_layout.addWidget(self._usage_reset)
        self._content.addWidget(usage_card)

        devices_card = QFrame()
        devices_card.setObjectName("AccountCenterCard")
        devices_layout = QVBoxLayout(devices_card)
        devices_layout.setContentsMargins(20, 18, 20, 18)
        devices_layout.setSpacing(10)
        self._devices_heading = QLabel()
        self._devices_heading.setObjectName("AccountCenterSectionTitle")
        devices_layout.addWidget(self._devices_heading)
        self._device_list = QVBoxLayout()
        self._device_list.setSpacing(8)
        devices_layout.addLayout(self._device_list)
        self._content.addWidget(devices_card)
        self._content.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        actions = QHBoxLayout()
        self._reset_password = QPushButton()
        self._reset_password.clicked.connect(self._request_password_reset)
        self._resend = QPushButton()
        self._resend.clicked.connect(self.resend_requested)
        self._sign_out = QPushButton()
        self._sign_out.clicked.connect(self.sign_out_requested)
        self._manage_plan = QPushButton()
        self._manage_plan.setObjectName("PrimaryButton")
        self._manage_plan.clicked.connect(self.manage_plan_requested)
        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.refresh_requested)
        actions.addWidget(self._reset_password)
        actions.addWidget(self._resend)
        actions.addWidget(self._sign_out)
        actions.addStretch()
        actions.addWidget(self._manage_plan)
        actions.addWidget(self._refresh)
        root.addLayout(actions)

        language.changed.connect(self._retranslate)
        self._retranslate()

    @staticmethod
    def _detail_row(layout: QVBoxLayout) -> tuple[QLabel, QLabel]:
        row = QHBoxLayout()
        label = QLabel()
        label.setObjectName("AccountCenterMuted")
        value = QLabel("—")
        value.setObjectName("AccountCenterValue")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(label)
        row.addStretch()
        row.addWidget(value)
        layout.addLayout(row)
        return label, value

    def _retranslate(self, *_args) -> None:
        self._title.setText(tr("account.center_title"))
        self._subtitle.setText(tr("account.center_subtitle"))
        self._back.setText(tr("account.back_translation"))
        self._profile_heading.setText(tr("account.profile"))
        self._login_methods_heading.setText(tr("account.login_methods"))
        self._password_method.setText(tr("account.password_method"))
        self._email[0].setText(tr("account.email"))
        self._verified[0].setText(tr("account.verification"))
        self._subscription[0].setText(tr("settings.subscription"))
        self._plan[0].setText(tr("account.plan"))
        self._expires[0].setText(tr("settings.expires"))
        self._usage_heading.setText(tr("account.monthly_usage"))
        self._devices_heading.setText(tr("settings.devices"))
        self._reset_password.setText(tr("account.reset_password"))
        self._resend.setText(tr("account.resend"))
        self._sign_out.setText(tr("common.sign_out"))
        self._manage_plan.setText(tr("account.manage_plan"))
        self._refresh.setText(tr("common.refresh"))
        self._cancel_google.setText(tr("common.cancel"))
        self._sync_locale(language.locale)
        self.set_profile(
            self._profile,
            self._devices,
            self._current_device_id,
            self._providers,
        )
        self.set_message(self._message_text, self._message_error)

    def _sync_locale(self, locale: str) -> None:
        index = self._locale.findData(locale)
        if index >= 0 and index != self._locale.currentIndex():
            self._locale.blockSignals(True)
            self._locale.setCurrentIndex(index)
            self._locale.blockSignals(False)

    def set_profile(
        self,
        profile: dict,
        devices: list[dict] | None = None,
        current_device_id: str = "",
        providers: list[str] | None = None,
    ) -> None:
        self._profile = dict(profile or {})
        if devices is not None:
            self._devices = list(devices)
        if current_device_id:
            self._current_device_id = current_device_id
        if providers is not None:
            self._providers = list(providers)

        verified = bool(self._profile.get("email_verified"))
        status = str(self._profile.get("status") or "registered")
        self._email[1].setText(str(self._profile.get("email") or "—"))
        self._verified[1].setText(tr("account.verified") if verified else tr("account.unverified"))
        self._subscription[1].setText(tr(f"account.state_{status}"))
        self._plan[1].setText(str(self._profile.get("plan_id") or "—"))
        self._expires[1].setText(_format_datetime(self._profile.get("subscription_expires_at")))
        self._back.setVisible(verified and status == "active")
        self._resend.setVisible(not verified)
        google_linked = "google.com" in self._providers
        password_linked = "password" in self._providers
        self._password_status.setText(
            tr("account.method_available")
            if password_linked
            else tr("account.method_unavailable")
        )
        self._password_status.setProperty(
            "state", "active" if password_linked else "revoked"
        )
        self._password_status.style().unpolish(self._password_status)
        self._password_status.style().polish(self._password_status)
        self._google_status.setText(
            tr("account.google_linked")
            if google_linked
            else tr("account.google_not_linked")
        )
        self._google_status.setProperty("state", "active" if google_linked else "revoked")
        self._google_status.style().unpolish(self._google_status)
        self._google_status.style().polish(self._google_status)
        self._link_google.setVisible(not google_linked)
        self._link_google.setEnabled(not self._google_waiting)
        self._link_google.setText(
            tr("account.google_waiting")
            if self._google_waiting
            else tr("account.link_google")
        )

        usage = self._profile.get("usage") or {}
        used = max(0, int(usage.get("used_audio_seconds", 0)))
        total = max(
            0,
            int(
                usage.get("audio_seconds_limit")
                or usage.get("monthly_audio_seconds")
                or 0
            ),
        )
        remaining = max(0, int(usage.get("remaining_audio_seconds", max(0, total - used))))
        self._usage_progress.setMaximum(max(1, total))
        self._usage_progress.setValue(min(used, total) if total else 0)
        self._usage_text.setText(
            tr(
                "account.usage_summary",
                used=f"{used / 60:.1f}",
                remaining=f"{remaining / 60:.1f}",
                total=f"{total / 60:.1f}",
            )
        )
        reset_value = usage.get("resets_at")
        self._usage_reset.setText(
            tr("account.usage_resets", time=_format_datetime(reset_value))
            if reset_value
            else "—"
        )
        self._rebuild_devices()

    def _rebuild_devices(self) -> None:
        while self._device_list.count():
            item = self._device_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._devices:
            empty = QLabel(tr("account.no_devices"))
            empty.setObjectName("AccountCenterMuted")
            self._device_list.addWidget(empty)
            return
        ordered = sorted(self._devices, key=lambda item: (not bool(item.get("active")), str(item.get("name"))))
        for device in ordered:
            row = QFrame()
            row.setObjectName("DeviceRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            info = QVBoxLayout()
            name = QLabel(str(device.get("name") or device.get("id") or "—"))
            name.setObjectName("DeviceName")
            info.addWidget(name)
            details = QLabel(
                f"{device.get('platform') or '—'}  ·  "
                f"{tr('account.created')} {_format_datetime(device.get('created_at'))}  ·  "
                f"{tr('account.last_seen')} {_format_datetime(device.get('last_seen_at'))}"
            )
            details.setObjectName("AccountCenterMuted")
            details.setWordWrap(True)
            info.addWidget(details)
            row_layout.addLayout(info, stretch=1)

            device_id = str(device.get("id") or "")
            active = bool(device.get("active"))
            current = bool(device_id and device_id == self._current_device_id)
            badge = QLabel(
                tr("account.this_device") if current else
                (tr("account.device_active") if active else tr("account.device_revoked"))
            )
            badge.setObjectName("DeviceBadge")
            badge.setProperty("state", "current" if current else ("active" if active else "revoked"))
            row_layout.addWidget(badge)
            if active and not current:
                button = QPushButton(tr("settings.revoke"))
                button.setProperty("device_id", device_id)
                button.clicked.connect(lambda _checked=False, value=device_id: self.revoke_requested.emit(value))
                row_layout.addWidget(button)
            self._device_list.addWidget(row)

    def set_loading(self, loading: bool) -> None:
        self._refresh.setEnabled(not loading)
        self._refresh.setText(tr("account.refreshing") if loading else tr("common.refresh"))

    def set_google_waiting(self, waiting: bool) -> None:
        self._google_waiting = waiting
        linked = "google.com" in self._providers
        self._link_google.setVisible(not linked)
        self._link_google.setEnabled(not waiting)
        self._link_google.setText(
            tr("account.google_waiting") if waiting else tr("account.link_google")
        )
        self._cancel_google.setVisible(waiting)
        self._cancel_google.setEnabled(waiting)

    def set_message(self, message: str, error: bool = False) -> None:
        self._message_text = message
        self._message_error = error
        self._message.setText(message)
        self._message.setProperty("kind", "error" if error else "success")
        self._message.style().unpolish(self._message)
        self._message.style().polish(self._message)
        self._message.setVisible(bool(message))

    def _request_password_reset(self) -> None:
        email = str(self._profile.get("email") or "")
        if email:
            self.reset_requested.emit(email)
