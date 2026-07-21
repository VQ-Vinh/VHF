from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prana_elex.ui.i18n import language, tr


class PlansPage(QWidget):
    back_requested = Signal()
    refresh_requested = Signal()
    select_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlansPage")
        self._profile: dict = {}
        self._plans: list[dict] = []
        self._card_widgets: list[QFrame] = []
        self._column_count = 0
        self._message_text = ""
        self._message_error = False

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(16)

        top = QHBoxLayout()
        self._back = QPushButton()
        self._back.clicked.connect(self.back_requested)
        top.addWidget(self._back)
        top.addStretch()
        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.refresh_requested)
        top.addWidget(self._refresh)
        root.addLayout(top)

        self._title = QLabel()
        self._title.setObjectName("PlansTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("PlansSubtitle")
        self._subtitle.setWordWrap(True)
        root.addWidget(self._title)
        root.addWidget(self._subtitle)

        self._message = QLabel()
        self._message.setObjectName("PlansMessage")
        self._message.setWordWrap(True)
        self._message.setVisible(False)
        root.addWidget(self._message)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("PlansScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_content = QWidget()
        self._scroll_content.setObjectName("PlansScrollContent")
        self._cards = QGridLayout(self._scroll_content)
        self._cards.setContentsMargins(0, 0, 0, 0)
        self._cards.setHorizontalSpacing(14)
        self._cards.setVerticalSpacing(14)
        self._cards.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._scroll_content)
        root.addWidget(self._scroll, 1)

        language.changed.connect(self._retranslate)
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        self._back.setText(tr("plans.back"))
        self._refresh.setText(tr("common.refresh"))
        self._title.setText(tr("plans.title"))
        self._subtitle.setText(tr("plans.subtitle"))
        self._rebuild()
        self.set_message(self._message_text, self._message_error)

    def set_data(self, profile: dict, plans: list[dict]) -> None:
        self._profile = dict(profile or {})
        self._plans = sorted(
            (dict(plan) for plan in plans),
            key=lambda plan: (int(plan.get("sort_order", 0)), str(plan.get("id", ""))),
        )
        self._rebuild()

    def set_profile(self, profile: dict) -> None:
        self._profile = dict(profile or {})
        self._rebuild()

    def set_loading(self, loading: bool) -> None:
        self._refresh.setEnabled(not loading)
        self._refresh.setText(tr("account.refreshing") if loading else tr("common.refresh"))

    def set_message(self, message: str, error: bool = False) -> None:
        self._message_text = message
        self._message_error = error
        self._message.setText(message)
        self._message.setVisible(bool(message))
        self._message.setProperty("kind", "error" if error else "success")
        self._message.style().unpolish(self._message)
        self._message.style().polish(self._message)

    def _rebuild(self) -> None:
        for card in self._card_widgets:
            card.deleteLater()
        self._card_widgets.clear()
        while self._cards.count():
            self._cards.takeAt(0)
        current_plan = str(self._profile.get("plan_id") or "")
        self._card_widgets = [
            self._plan_card(plan, current_plan) for plan in self._plans
        ]
        self._column_count = 0
        self._reflow_cards()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._reflow_cards()

    def _responsive_columns(self) -> int:
        # The scroll viewport is resized one layout pass after the page on some
        # Qt platforms. Use the page content width so reflow is deterministic.
        width = max(0, self.width() - 56)
        if width >= 1_000:
            return 3
        if width >= 650:
            return 2
        return 1

    def _reflow_cards(self) -> None:
        columns = self._responsive_columns()
        if columns == self._column_count and self._cards.count() == len(self._card_widgets):
            return
        while self._cards.count():
            self._cards.takeAt(0)
        for index, card in enumerate(self._card_widgets):
            self._cards.addWidget(card, index // columns, index % columns)
        for column in range(3):
            self._cards.setColumnStretch(column, 1 if column < columns else 0)
        self._column_count = columns

    def _plan_card(self, plan: dict, current_plan: str) -> QFrame:
        plan_id = str(plan.get("id") or "")
        current = plan_id == current_plan
        available = plan.get("availability") == "available"
        eligible = bool(self._profile.get("email_verified")) and self._profile.get("status") != "suspended"
        card = QFrame()
        card.setObjectName("PlanCard")
        card.setProperty("current", current)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        name = QLabel(str(plan.get("name") or plan_id.title()))
        name.setObjectName("PlanName")
        heading.addWidget(name)
        heading.addStretch()
        badges = QVBoxLayout()
        badges.setSpacing(5)
        availability_badge = QLabel(
            tr("plans.available") if available else tr("plans.coming_soon")
        )
        availability_badge.setObjectName("PlanAvailabilityBadge")
        availability_badge.setProperty(
            "availability", "available" if available else "coming_soon"
        )
        availability_badge.setAlignment(Qt.AlignCenter)
        badges.addWidget(availability_badge, 0, Qt.AlignRight)
        if current:
            badge = QLabel(tr("plans.current"))
            badge.setObjectName("PlanBadge")
            badge.setAlignment(Qt.AlignCenter)
            badges.addWidget(badge, 0, Qt.AlignRight)
        heading.addLayout(badges)
        layout.addLayout(heading)

        seconds = int(plan.get("audio_seconds_limit") or plan.get("monthly_audio_seconds") or 0)
        minutes = seconds // 60
        quota = QLabel(tr("plans.daily_minutes", minutes=minutes))
        quota.setObjectName("PlanQuota")
        layout.addWidget(quota)
        details = QGridLayout()
        details.setHorizontalSpacing(16)
        details.setVerticalSpacing(9)
        detail_values = (
            ("requests_per_minute", tr("plans.requests_per_minute"), plan.get("requests_per_minute", 0)),
            ("max_concurrency", tr("plans.concurrent_requests"), plan.get("max_concurrency", 0)),
            ("max_devices", tr("plans.max_devices"), plan.get("max_devices", 0)),
        )
        for row, (field, label_text, value) in enumerate(detail_values):
            label = QLabel(label_text)
            label.setObjectName("PlanDetailLabel")
            value_label = QLabel(str(int(value or 0)))
            value_label.setObjectName("PlanDetailValue")
            value_label.setProperty("field", field)
            value_label.setProperty("plan_id", plan_id)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            details.addWidget(label, row, 0)
            details.addWidget(value_label, row, 1)
        details.setColumnStretch(0, 1)
        layout.addLayout(details)
        layout.addStretch()

        action = QPushButton()
        if current:
            action.setText(tr("plans.current_button"))
            action.setEnabled(False)
        elif not available:
            action.setText(tr("plans.coming_soon"))
            action.setEnabled(False)
        elif not eligible:
            action.setText(tr("plans.choose"))
            action.setEnabled(False)
        else:
            action.setText(tr("plans.choose"))
            action.setObjectName("PrimaryButton")
            action.clicked.connect(
                lambda _checked=False, selected=plan_id: self.select_requested.emit(selected)
            )
        layout.addWidget(action)
        card.setMinimumSize(250, 320)
        return card


__all__ = ["PlansPage"]
