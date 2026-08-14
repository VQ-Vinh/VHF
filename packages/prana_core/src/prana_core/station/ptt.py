from __future__ import annotations

from typing import Protocol


class PttController(Protocol):
    """Platform boundary for controlling the radio push-to-talk line."""

    def engage(self) -> None: ...

    def release(self) -> None: ...

    def close(self) -> None: ...


class NullPttController:
    """No-op controller used by Stations without GPIO PTT hardware."""

    def engage(self) -> None:
        pass

    def release(self) -> None:
        pass

    def close(self) -> None:
        pass
