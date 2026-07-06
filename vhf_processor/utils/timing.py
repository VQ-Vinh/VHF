from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class LatencyTracker:
    markers: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.markers[name] = time.perf_counter()

    def elapsed(self, from_name: str, to_name: str | None = None) -> float:
        t0 = self.markers.get(from_name)
        if t0 is None:
            return 0.0
        t1 = self.markers.get(to_name) if to_name else time.perf_counter()
        if t1 is None:
            return 0.0
        return (t1 - t0) * 1000  # ms

    def total_ms(self) -> float:
        if not self.markers:
            return 0.0
        times = list(self.markers.values())
        return (times[-1] - times[0]) * 1000

    def reset(self) -> None:
        self.markers.clear()

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.markers[name] = time.perf_counter() - start
