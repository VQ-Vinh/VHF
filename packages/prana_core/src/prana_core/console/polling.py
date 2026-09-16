"""Background polling with backoff.

The Firestore rules deny clients any read outside `users/{uid}`, so an operator
console cannot use a realtime listener for Stations it does not own. Everything
it shows is polled, which makes the polling behaviour — backoff, last-good
retention, clean pausing — part of the product rather than an implementation
detail.

Thread-based rather than asyncio, matching how the desktop app's account layer
already does its network work, and so that it is testable without an event loop.
"""

from __future__ import annotations

import threading
from typing import Callable

DEFAULT_INTERVAL = 2.0
MIN_BACKOFF = 1.0
MAX_BACKOFF = 5.0


class ResilientPoller:
    """Calls `fetch` on an interval and hands results to `on_result`.

    On failure it backs off 1s -> 5s and keeps serving the last good value, so a
    blip in connectivity does not blank a screen an operator is watching.
    """

    def __init__(
        self,
        fetch: Callable[[], object],
        on_result: Callable[[object, Exception | None, int], None],
        interval: float = DEFAULT_INTERVAL,
        name: str = "poller",
    ):
        self._fetch = fetch
        self._on_result = on_result
        self._interval = interval
        self._name = name
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._paused = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_value: object = None
        self._failures = 0

    @property
    def last_value(self) -> object:
        return self._last_value

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name=self._name, daemon=True
        )
        self._thread.start()

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            was_paused = self._paused
            self._paused = False
        if was_paused:
            # Refresh immediately rather than making the operator wait out the
            # remainder of an interval after they come back to the page.
            self._wake.set()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self._thread = None

    def _delay(self) -> float:
        if self._failures == 0:
            return self._interval
        return min(MAX_BACKOFF, MIN_BACKOFF * (2 ** (self._failures - 1)))

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                paused = self._paused
            if not paused:
                try:
                    value = self._fetch()
                except Exception as exc:  # noqa: BLE001 - surfaced to the sink
                    self._failures += 1
                    self._emit(self._last_value, exc, self._failures)
                else:
                    self._failures = 0
                    self._last_value = value
                    self._emit(value, None, 0)
            self._wake.wait(self._delay())
            self._wake.clear()

    def _emit(self, value: object, error: Exception | None, failures: int) -> None:
        try:
            self._on_result(value, error, failures)
        except Exception:  # noqa: BLE001
            # A failing sink must not kill the poll loop; the next tick still runs.
            pass


__all__ = ["DEFAULT_INTERVAL", "MAX_BACKOFF", "MIN_BACKOFF", "ResilientPoller"]
