"""The Control tab's simulation, ported from the Flutter app.

Nothing here reaches a Station. The phone's Control tab runs on generated
readings (`apps/android/lib/telemetry/data/mock_telemetry_generator.dart`) and a
steering wheel with no write interface
(`apps/android/lib/features/station/control/application/steering_state.dart`),
and the API has no telemetry at all. The desktop shows the same thing, labelled
as a simulation in the same places, so the two apps cannot disagree about what
an operator is looking at.

Kept free of Qt widgets so every rule can be tested without a display, and free
of the operator client so the simulation can never grow a path to a radio.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# One sample a second, so this is the last half minute or so of track.
HISTORY_LENGTH = 40
STALE_AFTER = timedelta(seconds=5)

# The chart shows one 0.003 degree cell, divided into sixths so a grid square is
# a fixed distance and the scale bar means something.
CHART_CELL = 0.003
CHART_DIVISIONS = 6
CHART_INSET = 20.0
_CHART_ORIGIN_LAT = 10.7615
_CHART_ORIGIN_LON = 106.6505
_METRES_PER_DEGREE = 111320

RUDDER_LIMIT = 180.0
NUDGE_DEGREES = 5.0


def _round_half_up(value: float) -> int:
    """Dart's `round()`, which Python's banker's rounding is not."""
    return math.floor(value + 0.5)


@dataclass(frozen=True)
class TelemetrySnapshot:
    speed_knots: float
    depth_metres: float
    heading_degrees: float
    latitude: float
    longitude: float
    timestamp: datetime


def generate(elapsed_seconds: float, timestamp: datetime) -> TelemetrySnapshot:
    """The Flutter generator, term for term: slow sine waves and a steady drift."""
    s = elapsed_seconds
    return TelemetrySnapshot(
        speed_knots=10.2 + math.sin(s / 17) * 1.8,
        depth_metres=8.2 + math.sin(s / 23) * 0.7,
        heading_degrees=(315 + math.sin(s / 31) * 12) % 360,
        latitude=10.76230 + s * 0.000012,
        longitude=106.65110 + s * 0.000017,
        timestamp=timestamp,
    )


class Freshness(Enum):
    MISSING = "missing"
    FRESH = "fresh"
    STALE = "stale"


class TelemetryTrack:
    """The latest reading and the short history the chart draws as a track."""

    def __init__(self) -> None:
        self.history: list[TelemetrySnapshot] = []

    @property
    def snapshot(self) -> TelemetrySnapshot | None:
        return self.history[-1] if self.history else None

    def push(self, sample: TelemetrySnapshot) -> None:
        self.history.append(sample)
        del self.history[:-HISTORY_LENGTH]

    def clear(self) -> None:
        self.history.clear()

    def freshness(self, now: datetime) -> Freshness:
        sample = self.snapshot
        if sample is None:
            return Freshness.MISSING
        return Freshness.STALE if now - sample.timestamp > STALE_AFTER else Freshness.FRESH


class ControlMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"


class SteeringState:
    """Workspace-local simulation. It has no Station or telemetry write interface."""

    def __init__(self) -> None:
        self.mode = ControlMode.MANUAL
        self.angle = 0.0
        self._previous_bearing: float | None = None

    @property
    def manual(self) -> bool:
        return self.mode is ControlMode.MANUAL

    def reset(self) -> None:
        self.__init__()

    def select_mode(self, mode: ControlMode) -> None:
        self.end_drag()
        self.mode = mode
        if mode is ControlMode.AUTO:
            self.angle = 0.0

    def adjust(self, delta: float) -> None:
        if self.manual:
            self.angle = max(-RUDDER_LIMIT, min(RUDDER_LIMIT, self.angle + delta))

    def center(self) -> None:
        self.end_drag()
        if self.manual:
            self.angle = 0.0

    def begin_drag(self, bearing: float) -> None:
        if self.manual:
            self._previous_bearing = bearing

    def drag(self, bearing: float) -> None:
        previous = self._previous_bearing
        if previous is None or not self.manual:
            return
        # Unwrap across the +/-pi seam, or crossing due west would swing the
        # helm a full turn the other way.
        delta = bearing - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        self.adjust(math.degrees(delta))
        self._previous_bearing = bearing

    def end_drag(self) -> None:
        self._previous_bearing = None


def direction(angle: float) -> str:
    """"straight", "left" or "right": an i18n key suffix, not display text."""
    if abs(angle) < 0.5:
        return "straight"
    return "left" if angle < 0 else "right"


def rudder_fraction(angle: float) -> float:
    """-1 hard to port, 0 amidships, 1 hard to starboard, clamped to the bar."""
    return max(-RUDDER_LIMIT, min(RUDDER_LIMIT, angle)) / RUDDER_LIMIT


def format_dms(value: float, *, positive: str, negative: str) -> str:
    """Degrees, minutes and seconds, the way a fix is read off a GPS.

    The hemisphere comes from the sign rather than a minus sign, and the seconds
    are rounded before the minutes are carried, so 10.99999 reads as 11°00'00"
    and never as 10°59'60".
    """
    hemisphere = negative if value < 0 else positive
    total = _round_half_up(abs(value) * 3600)
    degrees, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{degrees}°{minutes:02d}'{seconds:02d}\"{hemisphere}"


def compass_point(degrees: float) -> str:
    points = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return points[_round_half_up((degrees % 360) / 45) % 8]


def chart_point(latitude: float, longitude: float, width: float, height: float) -> tuple[float, float]:
    """Where a fix sits on the chart. The viewport rebases after a full cell."""
    east = (longitude - _CHART_ORIGIN_LON) % CHART_CELL
    north = (latitude - _CHART_ORIGIN_LAT) % CHART_CELL
    return (
        CHART_INSET + east / CHART_CELL * (width - CHART_INSET * 2),
        height - CHART_INSET - north / CHART_CELL * (height - CHART_INSET * 2),
    )


def chart_division_metres(latitude: float | None) -> float:
    latitude = _CHART_ORIGIN_LAT if latitude is None else latitude
    return CHART_CELL / CHART_DIVISIONS * _METRES_PER_DEGREE * math.cos(math.radians(latitude))


def track_segments(
    fixes: list[tuple[float, float]], width: float, height: float
) -> list[list[tuple[float, float]]]:
    """The track split wherever the viewport rebased.

    Joining across a rebase would draw a line straight back across the chart
    that the vessel never sailed.
    """
    limit = min(width, height) / 2
    segments: list[list[tuple[float, float]]] = []
    last: tuple[float, float] | None = None
    for latitude, longitude in fixes:
        point = chart_point(latitude, longitude, width, height)
        if last is None or math.dist(point, last) > limit:
            segments.append([point])
        else:
            segments[-1].append(point)
        last = point
    return [segment for segment in segments if len(segment) > 1]


__all__ = [
    "HISTORY_LENGTH",
    "NUDGE_DEGREES",
    "ControlMode",
    "Freshness",
    "SteeringState",
    "TelemetrySnapshot",
    "TelemetryTrack",
    "chart_division_metres",
    "chart_point",
    "compass_point",
    "direction",
    "format_dms",
    "generate",
    "rudder_fraction",
    "track_segments",
]
