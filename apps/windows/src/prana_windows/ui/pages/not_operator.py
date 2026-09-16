from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from prana_windows.ui.i18n import language, tr
from prana_windows.ui.pages.account import _CenteredPage


class NotOperatorPage(_CenteredPage):
    """A valid account that simply lacks fleet operator rights.

    Reachable in normal use rather than an error state: the same binary and the
    same sign-in serve both an ordinary user and an operator.
    """

    sign_out_requested = Signal()
    retry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_title(tr("fleet.not_operator_title"), tr("fleet.not_operator_body"))
        row = QHBoxLayout()
        self._sign_out = QPushButton(tr("common.sign_out"))
        self._sign_out.setCursor(Qt.PointingHandCursor)
        self._sign_out.clicked.connect(self.sign_out_requested)
        self._retry = QPushButton(tr("common.retry"))
        self._retry.setObjectName("PrimaryButton")
        self._retry.setCursor(Qt.PointingHandCursor)
        self._retry.clicked.connect(self.retry_requested)
        row.addStretch()
        row.addWidget(self._sign_out)
        row.addWidget(self._retry)
        self.content.addLayout(row)
        language.changed.connect(self._retranslate)

    def _retranslate(self, *_args) -> None:
        self._page_title.setText(tr("fleet.not_operator_title"))
        self._page_subtitle.setText(tr("fleet.not_operator_body"))
        self._sign_out.setText(tr("common.sign_out"))
        self._retry.setText(tr("common.retry"))


__all__ = ["NotOperatorPage"]
