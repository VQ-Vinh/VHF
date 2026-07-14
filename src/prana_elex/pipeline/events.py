from __future__ import annotations

import logging
import threading
from typing import Any, Callable

Listener = Callable[..., Any]


class EventBus:
    def __init__(self):
        self._lock = threading.RLock()
        self._listeners: dict[str, list[Listener]] = {}

    def on(self, event: str, callback: Listener) -> None:
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)

    def off(self, event: str, callback: Listener) -> None:
        with self._lock:
            if event in self._listeners:
                self._listeners[event].remove(callback)
                if not self._listeners[event]:
                    del self._listeners[event]

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            listeners = list(self._listeners.get(event, []))
        for listener in listeners:
            try:
                listener(*args, **kwargs)
            except Exception:
                logging.getLogger(__name__).exception(
                    f"EventBus listener failed for event '{event}'"
                )


event_bus = EventBus()
