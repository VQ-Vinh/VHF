from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from prana_core.console.tx_phase import (
    MAX_TRANSLATION_CHARS,
    TxFailure,
    TxPhase,
    TxState,
)
from prana_windows.ui.i18n import language, tr

_PHASE_TEXT = {
    TxPhase.PROCESSING: "tx.processing",
    TxPhase.REVIEW_READY: "tx.review",
    TxPhase.QUEUED: "tx.queued",
    TxPhase.TRANSMITTING: "tx.transmitting",
    TxPhase.COMPLETED: "tx.completed",
}


class TxPanel(QFrame):
    """Push-to-talk, review, and transmit for the attached Station."""

    record_pressed = Signal()
    record_released = Signal()
    confirm_requested = Signal(str)
    cancel_requested = Signal()
    retry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TxPanel")
        self._state = TxState()
        self._can_record = False
        self._can_retry = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        self._title = QLabel()
        self._title.setObjectName("TxTitle")
        top.addWidget(self._title)

        self._record = QPushButton()
        self._record.setObjectName("TxRecordButton")
        self._record.setCursor(Qt.PointingHandCursor)
        # Press-and-hold, like the phone: releasing is what ends the recording,
        # so an operator cannot walk away from an open microphone.
        self._record.pressed.connect(self.record_pressed)
        self._record.released.connect(self.record_released)
        top.addWidget(self._record)

        self._status = QLabel()
        self._status.setObjectName("TxStatus")
        top.addWidget(self._status, stretch=1)

        self._retry = QPushButton()
        self._retry.setCursor(Qt.PointingHandCursor)
        self._retry.clicked.connect(self.retry_requested)
        top.addWidget(self._retry)

        self._cancel = QPushButton()
        self._cancel.setCursor(Qt.PointingHandCursor)
        self._cancel.clicked.connect(self.cancel_requested)
        top.addWidget(self._cancel)
        layout.addLayout(top)

        self._review = QFrame()
        self._review.setObjectName("TxReview")
        review_layout = QVBoxLayout(self._review)
        review_layout.setContentsMargins(14, 12, 14, 12)
        review_layout.setSpacing(8)
        self._transcript = QLabel()
        self._transcript.setObjectName("TxTranscript")
        self._transcript.setWordWrap(True)
        review_layout.addWidget(self._transcript)
        self._translation = QPlainTextEdit()
        self._translation.setObjectName("TxTranslation")
        self._translation.setMaximumHeight(90)
        review_layout.addWidget(self._translation)
        actions = QHBoxLayout()
        actions.addStretch()
        self._transmit = QPushButton()
        self._transmit.setObjectName("PrimaryButton")
        self._transmit.setCursor(Qt.PointingHandCursor)
        self._transmit.clicked.connect(
            lambda: self.confirm_requested.emit(self._translation.toPlainText())
        )
        actions.addWidget(self._transmit)
        review_layout.addLayout(actions)
        self._review.setVisible(False)
        layout.addWidget(self._review)

        language.changed.connect(self._retranslate)
        self._retranslate()

    def set_state(self, state: TxState, can_record: bool, can_retry: bool) -> None:
        entering_review = (
            state.phase == TxPhase.REVIEW_READY
            and self._state.phase != TxPhase.REVIEW_READY
        )
        self._state = state
        self._can_record = can_record
        self._can_retry = can_retry
        if entering_review:
            draft = state.draft or {}
            self._transcript.setText(str(draft.get("transcript") or ""))
            # Seed once, then leave the operator's edits alone: the draft poll
            # keeps running and would otherwise overwrite what they typed.
            self._translation.setPlainText(str(draft.get("translation") or ""))
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        state = self._state
        self._title.setText(tr("tx.title").upper())
        self._transmit.setText(tr("tx.transmit"))
        self._cancel.setText(tr("tx.cancel"))
        self._retry.setText(tr("tx.retry"))

        if state.phase == TxPhase.RECORDING:
            self._record.setText(
                tr("tx.recording", seconds=int(state.duration_seconds))
            )
        else:
            self._record.setText(tr("tx.record"))
        self._record.setEnabled(self._can_record or state.phase == TxPhase.RECORDING)
        self._record.setProperty(
            "recording", "true" if state.phase == TxPhase.RECORDING else "false"
        )
        self._record.style().unpolish(self._record)
        self._record.style().polish(self._record)

        if state.phase == TxPhase.FAILED and state.failure is not None:
            self._status.setText(_failure_text(state.failure))
        elif state.phase == TxPhase.IDLE and not self._can_record:
            self._status.setText(tr("tx.blocked"))
        else:
            key = _PHASE_TEXT.get(state.phase)
            self._status.setText(tr(key) if key else "")
        self._status.setProperty("phase", state.phase.value)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

        review = state.phase == TxPhase.REVIEW_READY
        self._review.setVisible(review)
        self._transmit.setEnabled(
            review
            and 0 < len(self._translation.toPlainText().strip()) <= MAX_TRANSLATION_CHARS
        )
        self._cancel.setVisible(state.phase.is_draft_active)
        self._retry.setVisible(self._can_retry)


def _failure_text(failure: TxFailure) -> str:
    return {
        TxFailure.STATION_OFFLINE: tr("phase.offline"),
        TxFailure.STATION_OFFLINE_DURING_TX: tr("phase.offline"),
        TxFailure.PTT_UNAVAILABLE: tr("tx.blocked"),
        TxFailure.CONTROL_LOST: tr("error.CONTROL_LOST"),
    }.get(failure, tr("phase.failed"))


__all__ = ["TxPanel"]
