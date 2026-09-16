"""Confirmation state machine for remote Station commands.

A direct port of `LiveUxController.synchronize` in
`apps/android/lib/runtime/vhf/live_controller.dart`. The branch order is load
bearing and matches the Dart original so the two clients agree on what a Station
is doing; `VIEW_ONLY` is the one addition, for a console that has lost its lease.

Kept as a pure function over immutable state: no Qt, no I/O, so it can be
diffed against the Dart behaviour in a plain unit test.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from prana_core.console.models import StationSummary


class CommandPhase(Enum):
    IDLE = "idle"
    SENDING = "sending"
    AWAITING_STATION = "awaiting_station"
    APPLIED = "applied"
    FAILED = "failed"
    OFFLINE = "offline"
    VIEW_ONLY = "view_only"


@dataclass(frozen=True)
class CommandState:
    phase: CommandPhase = CommandPhase.IDLE
    error: str | None = None
    baseline_generation: int | None = None
    pending_running: bool | None = None
    optimistic_language: str | None = None

    @property
    def busy(self) -> bool:
        return self.phase in (CommandPhase.SENDING, CommandPhase.AWAITING_STATION)


def begin_send(
    state: CommandState,
    station: StationSummary,
    *,
    running: bool | None = None,
    language: str | None = None,
) -> CommandState:
    """Record the pre-command generation so `applied` can be detected later."""
    return replace(
        state,
        phase=CommandPhase.SENDING,
        error=None,
        baseline_generation=station.desired.generation,
        pending_running=running,
        optimistic_language=language,
    )


def sent(state: CommandState) -> CommandState:
    return replace(state, phase=CommandPhase.AWAITING_STATION)


def send_failed(state: CommandState, error: str) -> CommandState:
    return replace(
        state,
        phase=CommandPhase.FAILED,
        error=error,
        pending_running=None,
        optimistic_language=None,
    )


def reduce(
    state: CommandState,
    station: StationSummary,
    now: datetime,
    *,
    holder_uid: str = "",
) -> CommandState:
    """Fold the latest Station snapshot into the command state."""
    online = station.is_online_at(now)

    # View-only outranks everything: with the lease gone, nothing this console
    # has in flight can still land, and offering a retry would be a lie.
    if holder_uid and station.controlled_by_other(holder_uid, now):
        if state.phase != CommandPhase.VIEW_ONLY:
            return replace(
                state,
                phase=CommandPhase.VIEW_ONLY,
                pending_running=None,
                optimistic_language=None,
            )
        return state

    if not online:
        if state.phase != CommandPhase.OFFLINE:
            return replace(state, phase=CommandPhase.OFFLINE, pending_running=None)
        return state

    if station.command_failed():
        error = station.command_error or "rx_start_failed"
        if (
            state.phase != CommandPhase.FAILED
            or state.error != error
            or state.pending_running is not None
        ):
            return replace(
                state,
                phase=CommandPhase.FAILED,
                error=error,
                pending_running=None,
                optimistic_language=None,
            )
        return state

    if (
        state.phase == CommandPhase.AWAITING_STATION
        and station.observed_generation >= station.desired.generation
        and station.desired.generation > (state.baseline_generation or -1)
    ):
        return replace(
            state,
            phase=CommandPhase.APPLIED,
            error=None,
            pending_running=None,
            optimistic_language=None,
        )

    if state.phase in (
        CommandPhase.OFFLINE,
        CommandPhase.APPLIED,
        CommandPhase.VIEW_ONLY,
    ):
        return replace(
            state,
            phase=CommandPhase.IDLE,
            error=None,
            pending_running=None,
        )

    return state


def can_toggle(state: CommandState, station: StationSummary, now: datetime) -> bool:
    """Whether Start/Stop should be usable right now.

    Mirrors `canToggleLiveStation` in the Flutter client, including the case that
    looks wrong at first glance: an offline Station stays toggleable so that a
    stuck `running=true` can still be cleared.
    """
    if state.phase == CommandPhase.VIEW_ONLY:
        return False
    online = station.is_online_at(now)
    if not (online or station.desired.running):
        return False
    if state.busy:
        return False
    return (not station.command_pending) or station.command_failed() or (not online)


__all__ = [
    "CommandPhase",
    "CommandState",
    "begin_send",
    "can_toggle",
    "reduce",
    "send_failed",
    "sent",
]
