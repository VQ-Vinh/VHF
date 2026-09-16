"""Wire models for the operator console.

These mirror the Dart models in `apps/android/lib/domain/` field for field, so
that the desktop console and the phone agree on what a Station is. Where the
wire name and the useful name differ (`transcript_restored`, `detected_language`)
the mapping happens here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Matches the Android client and Web Admin. The API's TX preconditions use 20s
# on purpose; see docs/architecture/operator-console.md.
STATION_ONLINE_SECONDS = 15


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


@dataclass(frozen=True)
class DesiredState:
    running: bool = False
    target_language: str = "en"
    capture_mode: str = "device"
    audio_device_id: str = ""
    tx_audio_device_id: str = ""
    timezone: str = ""
    capability_refresh_generation: int = 0
    retry_generation: int = 0
    generation: int = 0

    @classmethod
    def from_wire(cls, data: dict | None) -> "DesiredState":
        data = data or {}
        return cls(
            running=bool(data.get("running", False)),
            target_language=str(data.get("target_language") or "en"),
            capture_mode=str(data.get("capture_mode") or "device"),
            audio_device_id=str(data.get("audio_device_id") or ""),
            tx_audio_device_id=str(data.get("tx_audio_device_id") or ""),
            timezone=str(data.get("timezone") or ""),
            capability_refresh_generation=int(
                data.get("capability_refresh_generation") or 0
            ),
            retry_generation=int(data.get("retry_generation") or 0),
            generation=int(data.get("generation") or 0),
        )


@dataclass(frozen=True)
class StationAudioDevice:
    id: str = ""
    name: str = ""
    mode: str = "device"
    input_channels: int = 0
    output_channels: int = 0
    sample_rate: int = 0
    host_api: str = ""

    @classmethod
    def from_wire(cls, data: dict) -> "StationAudioDevice":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            mode=str(data.get("mode") or "device"),
            input_channels=int(data.get("input_channels") or 0),
            output_channels=int(data.get("output_channels") or 0),
            sample_rate=int(data.get("sample_rate") or 0),
            host_api=str(data.get("host_api") or ""),
        )


@dataclass(frozen=True)
class StationCapabilities:
    capability_hash: str = ""
    capture_modes: tuple[str, ...] = ()
    audio_devices: tuple[StationAudioDevice, ...] = ()
    storage_path: str = ""

    @classmethod
    def from_wire(cls, data: dict | None) -> "StationCapabilities | None":
        if not data:
            return None
        return cls(
            capability_hash=str(data.get("capability_hash") or ""),
            capture_modes=tuple(data.get("capture_modes") or ()),
            audio_devices=tuple(
                StationAudioDevice.from_wire(item)
                for item in data.get("audio_devices") or ()
            ),
            storage_path=str(data.get("storage_path") or ""),
        )

    def devices_for(self, mode: str) -> tuple[StationAudioDevice, ...]:
        return tuple(device for device in self.audio_devices if device.mode == mode)

    def output_devices(self) -> tuple[StationAudioDevice, ...]:
        return tuple(
            device
            for device in self.audio_devices
            if device.mode == "device" and device.output_channels > 0
        )


@dataclass(frozen=True)
class ControlLease:
    holder_uid: str = ""
    holder_kind: str = "owner"
    holder_label: str = ""
    acquired_at: datetime | None = None
    expires_at: datetime | None = None
    epoch: int = 0
    preempted_from_uid: str = ""
    preempted_at: datetime | None = None

    @classmethod
    def from_wire(cls, data: dict | None) -> "ControlLease | None":
        if not data:
            return None
        return cls(
            holder_uid=str(data.get("holder_uid") or ""),
            holder_kind=str(data.get("holder_kind") or "owner"),
            holder_label=str(data.get("holder_label") or ""),
            acquired_at=_parse_datetime(data.get("acquired_at")),
            expires_at=_parse_datetime(data.get("expires_at")),
            epoch=int(data.get("epoch") or 0),
            preempted_from_uid=str(data.get("preempted_from_uid") or ""),
            preempted_at=_parse_datetime(data.get("preempted_at")),
        )

    def is_active_at(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at > now

    def held_by(self, uid: str, now: datetime) -> bool:
        return self.is_active_at(now) and self.holder_uid == uid


@dataclass(frozen=True)
class StationSummary:
    station_id: str
    name: str = ""
    owner_uid: str = ""
    owner_email: str = ""
    storage_folder: str = ""
    platform: str = "unknown"
    active: bool = True
    capture_state: str = "idle"
    desired: DesiredState = field(default_factory=DesiredState)
    observed_generation: int = 0
    command_failed_generation: int = 0
    command_error: str | None = None
    session_id: str = ""
    sequence: int = 0
    last_seen_at: datetime | None = None
    capabilities: StationCapabilities | None = None
    active_capture_mode: str = "device"
    active_audio_device_id: str = ""
    last_error: str | None = None
    tx_state: str = "idle"
    tx_job_id: str = ""
    ptt_mode: str = "manual"
    ptt_ready: bool = True
    ptt_error: str | None = None
    control_lease: ControlLease | None = None

    @classmethod
    def from_wire(cls, data: dict) -> "StationSummary":
        return cls(
            station_id=str(data.get("station_id") or ""),
            name=str(data.get("name") or ""),
            owner_uid=str(data.get("owner_uid") or ""),
            owner_email=str(data.get("owner_email") or ""),
            storage_folder=str(data.get("storage_folder") or ""),
            platform=str(data.get("platform") or "unknown"),
            active=bool(data.get("active", True)),
            capture_state=str(data.get("capture_state") or "idle"),
            desired=DesiredState.from_wire(data.get("desired_state")),
            observed_generation=int(data.get("observed_generation") or 0),
            command_failed_generation=int(data.get("command_failed_generation") or 0),
            command_error=data.get("command_error"),
            session_id=str(data.get("session_id") or ""),
            sequence=int(data.get("sequence") or 0),
            last_seen_at=_parse_datetime(data.get("last_seen_at")),
            capabilities=StationCapabilities.from_wire(data.get("capabilities")),
            active_capture_mode=str(data.get("active_capture_mode") or "device"),
            active_audio_device_id=str(data.get("active_audio_device_id") or ""),
            last_error=data.get("last_error"),
            tx_state=str(data.get("tx_state") or "idle"),
            tx_job_id=str(data.get("tx_job_id") or ""),
            ptt_mode=str(data.get("ptt_mode") or "manual"),
            ptt_ready=bool(data.get("ptt_ready", True)),
            ptt_error=data.get("ptt_error"),
            control_lease=ControlLease.from_wire(data.get("control_lease")),
        )

    def is_online_at(self, now: datetime) -> bool:
        if not self.active or self.last_seen_at is None:
            return False
        return (now - self.last_seen_at).total_seconds() <= STATION_ONLINE_SECONDS

    @property
    def command_pending(self) -> bool:
        return self.observed_generation < self.desired.generation

    def command_failed(self) -> bool:
        return (
            self.command_error is not None
            and self.command_failed_generation >= self.desired.generation
        )

    def controlled_by_other(self, uid: str, now: datetime) -> bool:
        lease = self.control_lease
        return (
            lease is not None
            and lease.is_active_at(now)
            and lease.holder_uid != uid
        )


@dataclass(frozen=True)
class TranslationResult:
    request_id: str = ""
    session_id: str = ""
    sequence: int = 0
    transcript: str = ""
    translation: str = ""
    language: str = ""
    target_language: str = ""
    confidence: float = 0.0
    timestamp: datetime | None = None
    error: str | None = None

    @classmethod
    def from_wire(cls, data: dict) -> "TranslationResult":
        return cls(
            request_id=str(data.get("request_id") or ""),
            session_id=str(data.get("session_id") or ""),
            sequence=int(data.get("sequence") or 0),
            transcript=str(data.get("transcript_restored") or ""),
            translation=str(data.get("translation") or ""),
            language=str(data.get("detected_language") or ""),
            target_language=str(data.get("target_language") or ""),
            confidence=float(data.get("confidence") or 0.0),
            timestamp=_parse_datetime(data.get("timestamp")),
            error=data.get("error"),
        )

    @property
    def sort_key(self) -> tuple:
        return (
            self.timestamp or datetime.min.replace(tzinfo=timezone.utc),
            self.sequence,
            self.request_id,
        )


def sort_results(results: list[TranslationResult]) -> list[TranslationResult]:
    """Chronological order, de-duplicated by request id.

    Mirrors `compareTranslationChronologically` in the Flutter client: timestamp,
    then sequence, then request id, so two results inside the same second keep a
    stable order on both platforms.
    """
    unique: dict[str, TranslationResult] = {}
    for index, result in enumerate(results):
        unique[result.request_id or f"_{index}"] = result
    return sorted(unique.values(), key=lambda item: item.sort_key)


__all__ = [
    "STATION_ONLINE_SECONDS",
    "ControlLease",
    "DesiredState",
    "StationAudioDevice",
    "StationCapabilities",
    "StationSummary",
    "TranslationResult",
    "sort_results",
]
