"""TX state machine for the operator console.

A port of `apps/android/lib/runtime/vhf/tx_controller.dart` and its
`TxState`/`TxPhase`/`TxFailure` types. The phase names, the gating conditions
and the failure taxonomy are kept identical so the two clients behave the same
way on the same Station.

This module is pure state: no I/O, no audio, no Qt. The rules it encodes are
safety rules, and keeping them here means they can be tested exhaustively
without a microphone or a radio.

Rules that must not be relaxed:
  * a failed transmission is NEVER replayed automatically,
  * recording requires an online, started Station with PTT ready and no command
    in flight,
  * and for an operator, a held control lease as well.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

# The API caps a TX recording at the owner's plan; these are the absolute
# bounds it will accept regardless (services/prana_api/models.py Plan).
MIN_TX_SECONDS = 5
MAX_TX_SECONDS = 120
# Anything shorter is rejected server-side as AUDIO_TOO_SHORT.
MIN_TX_DURATION_SECONDS = 0.3
# Matches the Flutter review card; the API rejects longer translations.
MAX_TRANSLATION_CHARS = 2000


class TxPhase(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    REVIEW_READY = "review_ready"
    QUEUED = "queued"
    TRANSMITTING = "transmitting"
    COMPLETED = "completed"
    STATION_OFFLINE = "station_offline"
    FAILED = "failed"

    @property
    def is_draft_active(self) -> bool:
        return self in (TxPhase.RECORDING, TxPhase.PROCESSING, TxPhase.REVIEW_READY)

    @property
    def is_terminal(self) -> bool:
        return self in (TxPhase.COMPLETED, TxPhase.STATION_OFFLINE, TxPhase.FAILED)


class TxFailure(Enum):
    STATION_OFFLINE = "station_offline"
    STATION_OFFLINE_DURING_TX = "station_offline_during_tx"
    PTT_UNAVAILABLE = "ptt_unavailable"
    BUSY = "busy"
    EXPIRED = "expired"
    PROCESSING_FAILED = "processing_failed"
    RECORDING_TOO_LONG = "recording_too_long"
    TRANSMISSION_FAILED = "transmission_failed"
    CONTROL_LOST = "control_lost"


# Wire status -> phase, for a draft polled back from the API.
_STATUS_PHASE = {
    "processing": TxPhase.PROCESSING,
    "review_ready": TxPhase.REVIEW_READY,
    "synthesizing": TxPhase.QUEUED,
    "queued": TxPhase.QUEUED,
    "claimed": TxPhase.QUEUED,
    "transmitting": TxPhase.TRANSMITTING,
    "completed": TxPhase.COMPLETED,
    "failed": TxPhase.FAILED,
    "cancelled": TxPhase.IDLE,
}


@dataclass(frozen=True)
class TxState:
    phase: TxPhase = TxPhase.IDLE
    duration_seconds: float = 0.0
    target_language: str = "vi"
    draft: dict | None = None
    failure: TxFailure | None = None
    request_id: str = ""

    @property
    def can_change_language(self) -> bool:
        return self.phase == TxPhase.IDLE

    @property
    def requires_leave_confirmation(self) -> bool:
        if self.phase in (TxPhase.RECORDING, TxPhase.REVIEW_READY):
            return True
        return self.phase == TxPhase.PROCESSING and (
            self.draft is None or self.draft.get("status") == "review_ready"
        )

    @property
    def draft_id(self) -> str:
        return str((self.draft or {}).get("id") or "")


@dataclass(frozen=True)
class StationReadiness:
    """What the attached Station allows right now."""

    online: bool = False
    running: bool = False
    ptt_ready: bool = True
    command_pending: bool = False
    holds_control: bool = False

    @property
    def ready_to_transmit(self) -> bool:
        return (
            self.online
            and self.running
            and self.ptt_ready
            and not self.command_pending
            # The operator addition: you cannot key somebody's radio on a lease
            # you do not hold.
            and self.holds_control
        )

    @property
    def start_required(self) -> bool:
        return self.online and not self.running


def can_start_recording(state: TxState, readiness: StationReadiness) -> bool:
    return state.phase == TxPhase.IDLE and readiness.ready_to_transmit


def can_retry(state: TxState, readiness: StationReadiness) -> bool:
    """Retry is manual only, and never while the server draft is unsettled.

    A transmission that failed because the Station went away mid-TX may in fact
    have gone out. Retrying before the server has settled that draft to `failed`
    risks transmitting the same audio twice on a live channel.
    """
    if state.phase != TxPhase.FAILED or state.draft is None:
        return False
    if (
        state.failure == TxFailure.STATION_OFFLINE_DURING_TX
        and state.draft.get("status") != "failed"
    ):
        return False
    return readiness.ready_to_transmit


def begin_recording(state: TxState, request_id: str) -> TxState:
    return replace(
        state,
        phase=TxPhase.RECORDING,
        duration_seconds=0.0,
        failure=None,
        draft=None,
        request_id=request_id,
    )


def recording_tick(state: TxState, seconds: float, maximum: int) -> TxState:
    """Advance the recording clock, auto-stopping at the plan's ceiling."""
    if state.phase != TxPhase.RECORDING:
        return state
    if seconds >= maximum:
        return replace(state, phase=TxPhase.PROCESSING, duration_seconds=maximum)
    return replace(state, duration_seconds=seconds)


def uploading(state: TxState) -> TxState:
    return replace(state, phase=TxPhase.PROCESSING)


def cancelled(state: TxState) -> TxState:
    return TxState(target_language=state.target_language)


def failed(state: TxState, failure: TxFailure) -> TxState:
    return replace(state, phase=TxPhase.FAILED, failure=failure)


def apply_draft(state: TxState, draft: dict) -> TxState:
    """Fold a draft fetched from the API into the local state."""
    status = str(draft.get("status") or "")
    phase = _STATUS_PHASE.get(status, TxPhase.PROCESSING)
    failure = state.failure
    if phase == TxPhase.FAILED:
        failure = _failure_for(str(draft.get("error") or ""))
    elif phase != TxPhase.FAILED:
        failure = None
    return replace(state, phase=phase, draft=dict(draft), failure=failure)


def apply_readiness(state: TxState, readiness: StationReadiness) -> TxState:
    """React to the Station changing underneath an in-flight transmission."""
    if not readiness.holds_control and state.phase.is_draft_active:
        return replace(state, phase=TxPhase.FAILED, failure=TxFailure.CONTROL_LOST)
    if not readiness.online:
        if state.phase in (TxPhase.QUEUED, TxPhase.TRANSMITTING):
            # It may already have gone out. Settle it server-side before any
            # retry is offered.
            return replace(
                state,
                phase=TxPhase.FAILED,
                failure=TxFailure.STATION_OFFLINE_DURING_TX,
            )
        if state.phase == TxPhase.IDLE:
            return replace(
                state,
                phase=TxPhase.STATION_OFFLINE,
                failure=TxFailure.STATION_OFFLINE,
            )
        return state
    if not readiness.ptt_ready:
        if state.phase in (TxPhase.IDLE, TxPhase.QUEUED, TxPhase.TRANSMITTING):
            return replace(
                state, phase=TxPhase.FAILED, failure=TxFailure.PTT_UNAVAILABLE
            )
        return state
    if (
        state.failure in (TxFailure.PTT_UNAVAILABLE, TxFailure.STATION_OFFLINE)
        and state.draft is None
    ):
        return TxState(target_language=state.target_language)
    if state.phase == TxPhase.STATION_OFFLINE:
        return TxState(target_language=state.target_language)
    return state


def validate_translation(text: str) -> bool:
    stripped = (text or "").strip()
    return bool(stripped) and len(stripped) <= MAX_TRANSLATION_CHARS


def _failure_for(code: str) -> TxFailure:
    return {
        "TX_BUSY": TxFailure.BUSY,
        "TX_EXPIRED": TxFailure.EXPIRED,
        "TX_AUDIO_TOO_LONG": TxFailure.RECORDING_TOO_LONG,
        "TX_PROCESSING_FAILED": TxFailure.PROCESSING_FAILED,
        "PTT_UNAVAILABLE": TxFailure.PTT_UNAVAILABLE,
        "STATION_OFFLINE": TxFailure.STATION_OFFLINE_DURING_TX,
        "CONTROL_LOST": TxFailure.CONTROL_LOST,
    }.get(code, TxFailure.TRANSMISSION_FAILED)


__all__ = [
    "MAX_TRANSLATION_CHARS",
    "MAX_TX_SECONDS",
    "MIN_TX_DURATION_SECONDS",
    "MIN_TX_SECONDS",
    "StationReadiness",
    "TxFailure",
    "TxPhase",
    "TxState",
    "apply_draft",
    "apply_readiness",
    "begin_recording",
    "can_retry",
    "can_start_recording",
    "cancelled",
    "failed",
    "recording_tick",
    "uploading",
    "validate_translation",
]
