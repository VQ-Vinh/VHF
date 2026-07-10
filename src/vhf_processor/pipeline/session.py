from __future__ import annotations

import threading
from datetime import datetime


class SessionManager:
    _counter_lock = threading.Lock()
    _counter = 0

    def __init__(self, prefix: str = "session"):
        self._prefix = prefix
        self._session_id: str = ""
        self._sequence: int = 0
        self._start_time: datetime | None = None

    def start_session(self) -> str:
        with SessionManager._counter_lock:
            SessionManager._counter += 1
            seq = SessionManager._counter

        self._session_id = f"{self._prefix}{seq:03d}"
        self._sequence = 0
        self._start_time = datetime.now()
        return self._session_id

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def start_time(self) -> datetime | None:
        return self._start_time

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    def reset(self) -> None:
        self._session_id = ""
        self._sequence = 0
        self._start_time = None
