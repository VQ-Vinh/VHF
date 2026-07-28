from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class Plan(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=40)
    audio_seconds_limit: int = Field(gt=0, le=86_400)
    quota_period: Literal["daily", "monthly"] = "daily"
    availability: Literal["available", "coming_soon"] = "available"
    sort_order: int = Field(default=0, ge=0, le=1_000)
    # Deprecated compatibility alias used by desktop 1.1.0 and old plan docs.
    monthly_audio_seconds: int | None = Field(default=None, gt=0, le=86_400)
    requests_per_minute: int = Field(gt=0, le=600)
    max_concurrency: int = Field(default=2, ge=1, le=10)
    max_devices: int = Field(default=2, ge=1, le=10)
    max_stations: int = Field(default=2, ge=1, le=20)
    # Zero means unlimited. Existing Firestore plan documents are normalized
    # by plan ID so the Free policy takes effect before an admin saves it.
    live_log_limit: int = Field(default=0, ge=0, le=1_000)
    history_unlock_delay_days: int = Field(default=0, ge=0, le=30)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_limit(cls, value):
        data = dict(value or {})
        if not data.get("audio_seconds_limit") and data.get("monthly_audio_seconds"):
            data["audio_seconds_limit"] = data["monthly_audio_seconds"]
            data.setdefault("quota_period", "monthly")
        if not data.get("monthly_audio_seconds") and data.get("audio_seconds_limit"):
            data["monthly_audio_seconds"] = data["audio_seconds_limit"]
        if "live_log_limit" not in data:
            data["live_log_limit"] = 10 if data.get("id") == "free" else 0
        if "history_unlock_delay_days" not in data:
            data["history_unlock_delay_days"] = 1 if data.get("id") == "free" else 0
        return data


class UserAccount(BaseModel):
    uid: str
    email: str
    email_verified: bool = False
    status: Literal[
        "registered", "email_verified", "pending_payment", "active", "expired", "suspended"
    ] = "registered"
    plan_id: str | None = None
    subscription_expires_at: datetime | None = None

    @property
    def subscription_active(self) -> bool:
        if self.status != "active" or not self.plan_id:
            return False
        return (
            self.subscription_expires_at is None
            or self.subscription_expires_at > datetime.now(timezone.utc)
        )


class Device(BaseModel):
    id: str
    uid: str
    name: str
    platform: str
    public_key: str
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime | None = None


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=16, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=50)
    public_key: str


class PlanSelectionRequest(BaseModel):
    plan_id: str = Field(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=50)


class Usage(BaseModel):
    period: str
    used_audio_seconds: int = 0
    reserved_audio_seconds: int = 0
    request_count: int = 0
    audio_seconds_limit: int
    quota_period: Literal["daily", "monthly"] = "daily"
    resets_at: datetime
    # Deprecated compatibility alias used by desktop 1.1.0.
    monthly_audio_seconds: int | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_limit(cls, value):
        data = dict(value or {})
        if not data.get("audio_seconds_limit") and data.get("monthly_audio_seconds"):
            data["audio_seconds_limit"] = data["monthly_audio_seconds"]
        if not data.get("monthly_audio_seconds") and data.get("audio_seconds_limit"):
            data["monthly_audio_seconds"] = data["audio_seconds_limit"]
        return data

    @computed_field
    @property
    def remaining_audio_seconds(self) -> int:
        return max(
            0,
            self.audio_seconds_limit
            - self.used_audio_seconds
            - self.reserved_audio_seconds,
        )


class PlanEntitlements(BaseModel):
    live_log_limit: int = Field(default=10, ge=0, le=1_000)
    history_unlock_delay_days: int = Field(default=1, ge=0, le=30)
    max_concurrency: int = Field(default=2, ge=1, le=10)


class MeResponse(BaseModel):
    uid: str
    email: str
    email_verified: bool
    status: str
    plan_id: str | None
    subscription_expires_at: datetime | None
    usage: Usage | None = None
    entitlements: PlanEntitlements = Field(default_factory=PlanEntitlements)


class GoogleAuthorizationRequest(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    code_verifier: str = Field(min_length=43, max_length=128)
    redirect_uri: str = Field(min_length=1, max_length=200)

    @field_validator("code_verifier")
    @classmethod
    def valid_verifier(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        if any(char not in allowed for char in value):
            raise ValueError("Invalid PKCE verifier")
        return value

    @field_validator("redirect_uri")
    @classmethod
    def valid_redirect_uri(cls, value: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or not parsed.port
            or parsed.path != "/oauth2/callback"
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid desktop OAuth redirect URI")
        return value


class FirebaseSessionResponse(BaseModel):
    id_token: str
    refresh_token: str
    expires_in: int
    email: str
    uid: str = ""
    is_new_user: bool = False


class ProcessingResponse(BaseModel):
    request_id: str = ""
    station_id: str = ""
    session_id: str
    sequence: int
    audio_file: str
    detected_language: str = ""
    transcript_raw: str = ""
    transcript_restored: str = ""
    translation: str = ""
    target_language: Literal["vi", "en", "zh", "ja", "ko"] | None = None
    confidence: float = 0.0
    uncertain_segments: list[str] = Field(default_factory=list)
    processing_notes: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0
    queue_wait_ms: float = 0.0
    error: str | None = None


class StationHistoryDay(BaseModel):
    date: date
    result_count: int = Field(ge=1)
    first_result_at: datetime
    last_result_at: datetime
    locked: bool


class StationHistoryPage(BaseModel):
    items: list[ProcessingResponse]
    next_cursor: str | None = None


class Reservation(BaseModel):
    request_id: str
    state: Literal["reserved", "completed", "in_progress"]
    cached_response: dict | None = None


SUPPORTED_LANGUAGES = {"vi", "en", "zh", "ja", "ko"}


class StationPairingRequest(BaseModel):
    station_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    name: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=80)
    public_key: str = Field(min_length=40, max_length=100)


class StationPairingResponse(BaseModel):
    pairing_id: str
    pairing_code: str
    qr_payload: str
    expires_at: datetime


class StationClaimRequest(BaseModel):
    pairing_code: str = Field(pattern=r"^[A-Z0-9]{8}$")


class StationProvisionRequest(StationPairingRequest):
    activation_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    activation_version: Literal[1] = 1


class StationProvisionResponse(BaseModel):
    station_id: str
    setup_id: str
    state: Literal["provisioned", "claimed"]


class StationActivationClaimRequest(BaseModel):
    setup_id: str = Field(pattern=r"^[A-HJ-NP-Z2-9]{10}$")
    activation_code: str = Field(pattern=r"^[A-HJ-NP-Z2-9]{16}$")


class StationDesiredState(BaseModel):
    running: bool = False
    target_language: Literal["vi", "en", "zh", "ja", "ko"] = "en"
    capture_mode: Literal["device", "loopback"] = "device"
    audio_device_id: str = Field(default="", max_length=64)
    capability_refresh_generation: int = Field(default=0, ge=0)
    retry_generation: int = Field(default=0, ge=0)
    generation: int = Field(default=0, ge=0)


class StationDesiredStatePatch(BaseModel):
    running: bool | None = None
    target_language: Literal["vi", "en", "zh", "ja", "ko"] | None = None
    capture_mode: Literal["device", "loopback"] | None = None
    audio_device_id: str | None = Field(default=None, max_length=64)
    refresh_capabilities: bool = False
    retry: bool = False


class StationAudioDevice(BaseModel):
    id: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["device", "loopback"]
    input_channels: int = Field(default=0, ge=0, le=64)
    output_channels: int = Field(default=0, ge=0, le=64)
    sample_rate: int = Field(default=0, ge=0, le=384_000)
    host_api: str = Field(default="", max_length=100)


class StationCapabilities(BaseModel):
    capability_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    capture_modes: list[Literal["device", "loopback"]] = Field(min_length=1, max_length=2)
    audio_devices: list[StationAudioDevice] = Field(default_factory=list, max_length=100)
    storage_path: str = Field(default="", max_length=500)


class StationHeartbeat(BaseModel):
    capture_state: Literal["idle", "listening", "recording", "error"]
    session_id: str = Field(default="", max_length=100)
    sequence: int = Field(default=0, ge=0)
    app_version: str = Field(default="", max_length=40)
    observed_generation: int = Field(default=0, ge=0)
    target_language: Literal["vi", "en", "zh", "ja", "ko"] = "en"
    # Kept only to verify signatures from older Station builds. It has no
    # persistence or capture behavior and new builds no longer send it.
    boot_id: str = Field(default="", max_length=64)
    active_capture_mode: Literal["device", "loopback"] = "device"
    active_audio_device_id: str = Field(default="", max_length=64)
    error: str | None = Field(default=None, max_length=500)
    retrying: bool = False
    retry_code: str | None = Field(default=None, max_length=80)
    retry_attempt: int = Field(default=0, ge=0, le=3)


class Station(BaseModel):
    station_id: str
    name: str
    platform: str
    active: bool = True
    online: bool = False
    capture_state: str = "idle"
    desired_state: StationDesiredState = Field(default_factory=StationDesiredState)
    observed_generation: int = 0
    session_id: str = ""
    sequence: int = 0
    last_seen_at: datetime | None = None
    capabilities: StationCapabilities | None = None
    active_capture_mode: Literal["device", "loopback"] = "device"
    active_audio_device_id: str = ""
    last_error: str | None = None
    retrying: bool = False
    retry_code: str | None = None
    retry_attempt: int = 0
