from __future__ import annotations

from typing import Protocol


class PttController(Protocol):
    """Platform boundary for controlling the radio push-to-talk line."""

    def engage(self) -> None: ...

    def release(self) -> None: ...

    def close(self) -> None: ...

    @property
    def mode(self) -> str: ...

    @property
    def ready(self) -> bool: ...

    @property
    def error(self) -> str | None: ...


class NullPttController:
    """No-op controller used by Stations without GPIO PTT hardware."""

    def engage(self) -> None:
        pass

    def release(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def mode(self) -> str:
        return "manual"

    @property
    def ready(self) -> bool:
        return True

    @property
    def error(self) -> str | None:
        return None


class UnavailablePttController:
    """Keep RX alive while preventing TX when GPIO initialization fails."""

    def __init__(self, error: str = "PTT_UNAVAILABLE") -> None:
        self._error = error

    def engage(self) -> None:
        raise RuntimeError(self._error)

    def release(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def mode(self) -> str:
        return "unavailable"

    @property
    def ready(self) -> bool:
        return False

    @property
    def error(self) -> str | None:
        return self._error
