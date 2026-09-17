"""Qt-facing controllers for the fleet operator console.

Built the same way as `AccountController`: every network call runs on a worker
thread with its own busy lock, and results reach the UI as Qt Signals. Nothing
here touches the qasync loop.

The console is REST-only by necessity, not preference: Firestore rules deny a
client any read outside `users/{uid}`, so an operator cannot subscribe to a
Station it does not own. All freshness comes from the pollers below.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from prana_core.backend.client import BackendApiError
from prana_core.console.command_phase import (
    CommandPhase,
    CommandState,
    begin_send,
    reduce,
    send_failed,
    sent,
)
from prana_core.console.models import ControlLease, StationSummary, TranslationResult
from prana_core.console.polling import ResilientPoller
from prana_core.console.station_client import CONTROL_RENEW_SECONDS, OperatorStationClient
from prana_core.console.tx_phase import (
    MAX_TX_SECONDS,
    MIN_TX_DURATION_SECONDS,
    StationReadiness,
    TxFailure,
    TxPhase,
    TxState,
    apply_draft,
    apply_readiness,
    begin_recording,
    can_retry,
    can_start_recording,
    cancelled,
    failed,
    recording_tick,
    uploading,
    validate_translation,
)
from prana_core.common.logger import get_logger

logger = get_logger(__name__)

FLEET_POLL_SECONDS = 10.0
STATION_POLL_SECONDS = 2.0
LIVE_POLL_SECONDS = 2.0
TX_POLL_SECONDS = 1.0
TX_TICK_SECONDS = 0.1


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FleetController(QObject):
    """Owns the Station list and its poll."""

    stations_changed = Signal(object, object)  # list[StationSummary], next_cursor
    error = Signal(str)
    loading = Signal(bool)

    def __init__(self, client: OperatorStationClient, parent=None):
        super().__init__(parent)
        self._client = client
        self._lock = threading.Lock()
        self._busy = False
        self._query = ""
        self._online_only = False
        self._poller: ResilientPoller | None = None

    def set_filter(self, query: str, online_only: bool) -> None:
        self._query = query
        self._online_only = online_only
        self.refresh()

    def start(self) -> None:
        if self._poller is None:
            self._poller = ResilientPoller(
                self._fetch,
                self._deliver,
                interval=FLEET_POLL_SECONDS,
                name="fleet-poll",
            )
            self._poller.start()
        else:
            self._poller.resume()

    def pause(self) -> None:
        if self._poller is not None:
            self._poller.pause()

    def stop(self) -> None:
        if self._poller is not None:
            self._poller.stop()
            self._poller = None

    def refresh(self) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True
        self.loading.emit(True)

        def run() -> None:
            try:
                self._deliver(self._fetch(), None, 0)
            finally:
                with self._lock:
                    self._busy = False
                self.loading.emit(False)

        threading.Thread(target=run, daemon=True, name="fleet-refresh").start()

    def _fetch(self):
        return self._client.list_stations(
            query=self._query, online_only=self._online_only
        )

    def _deliver(self, value, error: Exception | None, _failures: int) -> None:
        if error is not None:
            self.error.emit(_error_key(error))
            return
        if value is None:
            return
        stations, cursor = value
        self.stations_changed.emit(stations, cursor)


class StationController(QObject):
    """Owns one attached Station: its state poll, live feed and control lease.

    Exactly one of these is alive at a time. It holds every timer for the
    attached Station so that detaching is a single call and cannot leak a poll.
    """

    station_changed = Signal(object)          # StationSummary
    results_changed = Signal(object)          # list[TranslationResult]
    phase_changed = Signal(object)            # CommandState
    lease_changed = Signal(object)            # ControlLease | None
    error = Signal(str)
    notice = Signal(str)

    def __init__(self, client: OperatorStationClient, station_id: str, parent=None):
        super().__init__(parent)
        self._client = client
        self.station_id = station_id
        self.station: StationSummary | None = None
        self.lease: ControlLease | None = None
        self.state = CommandState()
        self._lock = threading.Lock()
        self._busy = False
        self._station_poll: ResilientPoller | None = None
        self._live_poll: ResilientPoller | None = None
        self._renew_poll: ResilientPoller | None = None

    # -- lifecycle --------------------------------------------------------

    def attach(self) -> None:
        self._station_poll = ResilientPoller(
            lambda: self._client.get_station(self.station_id),
            self._on_station,
            interval=STATION_POLL_SECONDS,
            name="station-poll",
        )
        self._live_poll = ResilientPoller(
            lambda: self._client.live_results(self.station_id),
            self._on_results,
            interval=LIVE_POLL_SECONDS,
            name="live-poll",
        )
        self._station_poll.start()
        self._live_poll.start()

    def pause_content(self) -> None:
        """Stop the two content polls while the workspace is not visible.

        The lease renewal deliberately keeps running: letting control lapse
        silently because the window was minimised is worse than never having
        taken it.
        """
        for poller in (self._station_poll, self._live_poll):
            if poller is not None:
                poller.pause()

    def resume_content(self) -> None:
        for poller in (self._station_poll, self._live_poll):
            if poller is not None:
                poller.resume()

    def detach(self) -> None:
        for poller in (self._station_poll, self._live_poll, self._renew_poll):
            if poller is not None:
                poller.stop()
        self._station_poll = self._live_poll = self._renew_poll = None
        self.release_control(blocking=True)

    # -- control lease ----------------------------------------------------

    @property
    def holds_control(self) -> bool:
        return self.lease is not None and self.lease.held_by(
            self._client.operator_uid, _now()
        )

    def acquire_control(self, force: bool = False) -> None:
        def work() -> None:
            lease = self._client.acquire_control(
                self.station_id, force=force, label=""
            )
            self.lease = lease
            self.lease_changed.emit(lease)
            self._start_renewal()

        self._run(work)

    def release_control(self, blocking: bool = False) -> None:
        lease = self.lease
        if lease is None:
            return
        self.lease = None
        self.lease_changed.emit(None)
        if self._renew_poll is not None:
            self._renew_poll.stop()
            self._renew_poll = None

        def work() -> None:
            try:
                self._client.release_control(self.station_id, lease.epoch)
            except BackendApiError:
                # Best effort. A lease we fail to release simply expires.
                logger.debug("Releasing control failed", exc_info=True)

        if blocking:
            work()
        else:
            threading.Thread(target=work, daemon=True, name="lease-release").start()

    def _start_renewal(self) -> None:
        if self._renew_poll is not None:
            self._renew_poll.stop()
        self._renew_poll = ResilientPoller(
            self._renew,
            self._on_renew,
            interval=CONTROL_RENEW_SECONDS,
            name="lease-renew",
        )
        self._renew_poll.start()

    def _renew(self):
        lease = self.lease
        if lease is None:
            return None
        return self._client.renew_control(self.station_id, lease.epoch)

    def _on_renew(self, value, error: Exception | None, _failures: int) -> None:
        if isinstance(error, BackendApiError) and error.code == "CONTROL_LOST":
            # Somebody forced a takeover. Drop to view-only rather than keep
            # renewing against a lease we no longer hold.
            self.lease = None
            self.lease_changed.emit(None)
            self.notice.emit("control.lost")
            if self._renew_poll is not None:
                self._renew_poll.pause()
            return
        if isinstance(value, ControlLease):
            self.lease = value
            self.lease_changed.emit(value)

    # -- commands ---------------------------------------------------------

    def set_running(self, running: bool) -> None:
        self._command(running=running)

    def set_target_language(self, code: str) -> None:
        self._command(target_language=code)

    def set_capture(self, mode: str, device_id: str) -> None:
        self._command(capture_mode=mode, audio_device_id=device_id)

    def refresh_capabilities(self) -> None:
        self._command(refresh_capabilities=True)

    def retry(self) -> None:
        self._command(retry=True)

    def _command(self, **kwargs) -> None:
        station, lease = self.station, self.lease
        if station is None or lease is None:
            self.error.emit("error.CONTROL_LOST")
            return
        self._set_state(
            begin_send(
                self.state,
                station,
                running=kwargs.get("running"),
                language=kwargs.get("target_language"),
            )
        )

        def work() -> None:
            try:
                self._client.set_desired_state(self.station_id, lease.epoch, **kwargs)
            except BackendApiError as exc:
                self._set_state(send_failed(self.state, _error_key(exc)))
                self.error.emit(_error_key(exc))
                if exc.code == "CONTROL_LOST":
                    self.lease = None
                    self.lease_changed.emit(None)
                return
            self._set_state(sent(self.state))

        threading.Thread(target=work, daemon=True, name="station-command").start()

    # -- poll sinks -------------------------------------------------------

    def _on_station(self, value, error: Exception | None, _failures: int) -> None:
        if error is not None:
            self.error.emit(_error_key(error))
            return
        if not isinstance(value, StationSummary):
            return
        self.station = value
        self.station_changed.emit(value)
        if value.control_lease is not None and self.lease is not None:
            # Keep the locally held lease in step with the server's view so a
            # takeover elsewhere shows up even between renewals.
            if value.control_lease.epoch != self.lease.epoch:
                self.lease = None
                self.lease_changed.emit(None)
        self._set_state(
            reduce(
                self.state,
                value,
                _now(),
                holder_uid=self._client.operator_uid,
            )
        )

    def _on_results(self, value, error: Exception | None, _failures: int) -> None:
        if error is not None or not isinstance(value, list):
            return
        self.results_changed.emit(value)

    def _set_state(self, state: CommandState) -> None:
        if state != self.state:
            self.state = state
            self.phase_changed.emit(state)

    def _run(self, work) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True

        def run() -> None:
            try:
                work()
            except BackendApiError as exc:
                self.error.emit(_error_key(exc))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Console operation failed", exc_info=exc)
                self.error.emit("error.NETWORK_ERROR")
            finally:
                with self._lock:
                    self._busy = False

        threading.Thread(target=run, daemon=True, name="station-op").start()



class TxController(QObject):
    """Drives one transmission against the attached Station.

    Owns no policy of its own: every gate comes from
    `prana_core.console.tx_phase`, which is a port of the phone's controller so
    both clients refuse the same things. The rules that matter most here are the
    ones about *not* transmitting: no automatic replay of a failed job, and no
    blind re-upload after a network error.
    """

    state_changed = Signal(object)   # TxState
    error = Signal(str)

    def __init__(
        self,
        client: OperatorStationClient,
        station_id: str,
        recorder,
        parent=None,
    ):
        super().__init__(parent)
        self._client = client
        self._station_id = station_id
        self._recorder = recorder
        self.state = TxState()
        self.readiness = StationReadiness()
        self.max_seconds = MAX_TX_SECONDS
        self._epoch = 0
        self._lock = threading.Lock()
        self._busy = False
        # Guards the draft poll against shutdown: an upload thread may reach
        # `_watch_draft` just as the operator detaches.
        self._poll_lock = threading.Lock()
        self._closed = False
        self._tick: ResilientPoller | None = None
        self._draft_poll: ResilientPoller | None = None

    # -- inputs -----------------------------------------------------------

    def set_epoch(self, epoch: int) -> None:
        """The control epoch every TX call must present; 0 when not holding it."""
        self._epoch = epoch

    def set_readiness(self, readiness: StationReadiness) -> None:
        if readiness == self.readiness:
            return
        self.readiness = readiness
        self._set(apply_readiness(self.state, readiness))

    def set_target_language(self, code: str) -> None:
        if self.state.can_change_language:
            self._set(replace_language(self.state, code))

    @property
    def can_record(self) -> bool:
        return can_start_recording(self.state, self.readiness)

    @property
    def can_retry(self) -> bool:
        return can_retry(self.state, self.readiness)

    # -- recording --------------------------------------------------------

    def start_recording(self) -> None:
        if not self.can_record:
            self.error.emit("tx.blocked")
            return
        request_id = str(uuid.uuid4())
        try:
            self._recorder.start()
        except Exception as exc:  # noqa: BLE001
            logger.warning("TX recording failed to start", exc_info=exc)
            self.error.emit("tx.blocked")
            return
        self._set(begin_recording(self.state, request_id))
        self._tick = ResilientPoller(
            lambda: self._recorder.duration_seconds,
            self._on_tick,
            interval=TX_TICK_SECONDS,
            name="tx-tick",
        )
        self._tick.start()

    def _on_tick(self, value, error: Exception | None, _failures: int) -> None:
        if error is not None or self.state.phase != TxPhase.RECORDING:
            return
        seconds = float(value or 0.0)
        nxt = recording_tick(self.state, seconds, self.max_seconds)
        if nxt.phase == TxPhase.PROCESSING:
            # Hit the plan ceiling; stop for the operator rather than let the
            # server reject the upload.
            self.stop_recording()
            return
        self._set(nxt)

    def stop_recording(self) -> None:
        if self.state.phase != TxPhase.RECORDING:
            return
        if self._tick is not None:
            self._tick.stop()
            self._tick = None
        audio = self._recorder.stop()
        duration = len(audio) / (2 * 16000) if audio else 0.0
        if duration < MIN_TX_DURATION_SECONDS:
            self._set(cancelled(self.state))
            return
        epoch = self._epoch
        if not epoch:
            # The lease went while the operator was still talking. Nothing has
            # been uploaded, so there is nothing to recover: drop the take.
            self._set(cancelled(self.state))
            self.error.emit("error.CONTROL_LOST")
            return
        self._set(uploading(self.state))
        request_id = self.state.request_id

        def work() -> None:
            try:
                draft, _ = self._client.create_tx_draft(
                    self._station_id,
                    epoch,
                    audio,
                    self.state.target_language,
                    request_id=request_id,
                )
            except BackendApiError as exc:
                if exc.code == "NETWORK_ERROR":
                    # Never re-upload blindly: the first attempt may have landed
                    # and a second would queue the same audio twice.
                    self._recover_draft(request_id)
                    return
                self._set(failed(self.state, TxFailure.TRANSMISSION_FAILED))
                self.error.emit(_error_key(exc))
                return
            self._set(apply_draft(self.state, draft))
            self._watch_draft()

        threading.Thread(target=work, daemon=True, name="tx-upload").start()

    def _recover_draft(self, request_id: str) -> None:
        try:
            draft = self._client.get_tx_draft(self._station_id, self._epoch, request_id)
        except BackendApiError:
            self._set(failed(self.state, TxFailure.TRANSMISSION_FAILED))
            self.error.emit("error.NETWORK_ERROR")
            return
        self._set(apply_draft(self.state, draft))
        self._watch_draft()

    # -- draft lifecycle --------------------------------------------------

    def _watch_draft(self) -> None:
        draft_id = self.state.draft_id
        if not draft_id:
            return
        with self._poll_lock:
            if self._closed:
                # Detached while this draft was being created; a poll started
                # now would outlive the controller and never be stopped.
                return
            previous = self._draft_poll
            self._draft_poll = ResilientPoller(
                lambda: self._client.get_tx_draft(self._station_id, self._epoch, draft_id),
                self._on_draft,
                interval=TX_POLL_SECONDS,
                name="tx-draft",
            )
            self._draft_poll.start()
        if previous is not None:
            previous.stop()

    def _on_draft(self, value, error: Exception | None, _failures: int) -> None:
        if error is not None or not isinstance(value, dict):
            return
        self._set(apply_draft(self.state, value))
        if self.state.phase in (TxPhase.REVIEW_READY, TxPhase.COMPLETED, TxPhase.FAILED):
            if self._draft_poll is not None:
                self._draft_poll.pause()

    def confirm(self, translation: str) -> None:
        if self.state.phase != TxPhase.REVIEW_READY:
            return
        if not validate_translation(translation):
            self.error.emit("tx.blocked")
            return
        draft_id = self.state.draft_id
        epoch = self._epoch
        if not epoch:
            self.error.emit("error.CONTROL_LOST")
            return

        def work() -> None:
            draft = self._client.confirm_tx_draft(
                self._station_id, epoch, draft_id, translation.strip()
            )
            self._set(apply_draft(self.state, draft))
            if self._draft_poll is not None:
                self._draft_poll.resume()
            else:
                self._watch_draft()

        self._run(work)

    def cancel(self) -> None:
        draft_id = self.state.draft_id
        if self._tick is not None:
            self._tick.stop()
            self._tick = None
        if self._draft_poll is not None:
            self._draft_poll.stop()
            self._draft_poll = None
        if self.state.phase == TxPhase.RECORDING:
            self._recorder.cancel()
        self._set(cancelled(self.state))
        epoch = self._epoch
        if not draft_id or not epoch:
            # Without the lease the server would refuse the cancel; an
            # unconfirmed draft is never transmitted, so leaving it is safe.
            return

        def work() -> None:
            try:
                self._client.cancel_tx_draft(self._station_id, epoch, draft_id)
            except BackendApiError:
                logger.debug("Cancelling TX draft failed", exc_info=True)

        threading.Thread(target=work, daemon=True, name="tx-cancel").start()

    def retry(self) -> None:
        if not self.can_retry:
            return
        draft_id = self.state.draft_id
        epoch = self._epoch
        if not epoch:
            self.error.emit("error.CONTROL_LOST")
            return

        def work() -> None:
            draft = self._client.retry_tx_draft(self._station_id, epoch, draft_id)
            self._set(apply_draft(self.state, draft))
            self._watch_draft()

        self._run(work)

    def shutdown(self) -> None:
        with self._poll_lock:
            self._closed = True
            pollers = (self._tick, self._draft_poll)
            self._tick = self._draft_poll = None
        for poller in pollers:
            if poller is not None:
                poller.stop()
        if self._recorder.is_recording:
            self._recorder.cancel()

    # -- plumbing ---------------------------------------------------------

    def _set(self, state: TxState) -> None:
        if state != self.state:
            self.state = state
            self.state_changed.emit(state)

    def _run(self, work) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True

        def run() -> None:
            try:
                work()
            except BackendApiError as exc:
                self._set(failed(self.state, TxFailure.TRANSMISSION_FAILED))
                self.error.emit(_error_key(exc))
            except Exception as exc:  # noqa: BLE001
                logger.warning("TX operation failed", exc_info=exc)
                self.error.emit("error.NETWORK_ERROR")
            finally:
                with self._lock:
                    self._busy = False

        threading.Thread(target=run, daemon=True, name="tx-op").start()


def replace_language(state: TxState, code: str) -> TxState:
    from dataclasses import replace as _replace

    return _replace(state, target_language=code)


def _error_key(error: Exception) -> str:
    """Map an API error to an i18n key, falling back to its message."""
    if isinstance(error, BackendApiError):
        return f"error.{error.code}"
    return "error.NETWORK_ERROR"


__all__ = [
    "CommandPhase",
    "CommandState",
    "FleetController",
    "StationController",
    "TranslationResult",
    "TxController",
]
