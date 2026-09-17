from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from prana_core.console.models import ControlLease
from prana_windows.ui.i18n import language, tr


class LeaseBanner(QFrame):
    """Says who holds control, and offers the one way to take it."""

    take_requested = Signal()
    force_requested = Signal()
    release_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LeaseBanner")
        self._lease: ControlLease | None = None
        self._operator_uid = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 10, 28, 10)
        layout.setSpacing(10)

        self._label = QLabel()
        self._label.setObjectName("LeaseLabel")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, stretch=1)

        self._take = QPushButton()
        self._take.setObjectName("PrimaryButton")
        self._take.setCursor(Qt.PointingHandCursor)
        self._take.clicked.connect(self._on_take)
        layout.addWidget(self._take)

        self._release = QPushButton()
        self._release.setCursor(Qt.PointingHandCursor)
        self._release.clicked.connect(self.release_requested)
        layout.addWidget(self._release)

        language.changed.connect(self._retranslate)
        self._retranslate()

    def set_operator_uid(self, uid: str) -> None:
        self._operator_uid = uid
        self._retranslate()

    def set_lease(self, lease: ControlLease | None) -> None:
        self._lease = lease
        self._retranslate()

    def _on_take(self) -> None:
        # Preemption is never implicit: an active lease held by somebody else
        # takes the force path, which the workspace confirms separately.
        if self._held_by_other():
            self.force_requested.emit()
        else:
            self.take_requested.emit()

    def _held_by_other(self) -> bool:
        lease = self._lease
        return (
            lease is not None
            and lease.is_active_at(datetime.now(timezone.utc))
            and lease.holder_uid != self._operator_uid
        )

    def _retranslate(self, *_args) -> None:
        lease = self._lease
        now = datetime.now(timezone.utc)
        active = lease is not None and lease.is_active_at(now)
        mine = active and lease.holder_uid == self._operator_uid
        expires = (
            lease.expires_at.astimezone().strftime("%H:%M:%S")
            if active and lease and lease.expires_at
            else ""
        )
        if mine:
            self._label.setText(tr("control.holding", time=expires))
            state = "self"
        elif active and lease:
            self._label.setText(
                tr(
                    "control.held_by",
                    holder=lease.holder_label or lease.holder_uid,
                    time=expires,
                )
            )
            state = "other"
        else:
            self._label.setText(tr("control.none"))
            state = "none"

        self._take.setVisible(not mine)
        self._take.setText(tr("control.force") if state == "other" else tr("control.take"))
        self._release.setVisible(mine)
        self._release.setText(tr("control.release"))
        self.setProperty("lease", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def holder_label(self) -> str:
        lease = self._lease
        if lease is None:
            return ""
        return lease.holder_label or lease.holder_uid


__all__ = ["LeaseBanner"]
