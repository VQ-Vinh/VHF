from __future__ import annotations

from datetime import datetime, timezone
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

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_limit(cls, value):
        data = dict(value or {})
        if not data.get("audio_seconds_limit") and data.get("monthly_audio_seconds"):
            data["audio_seconds_limit"] = data["monthly_audio_seconds"]
            data.setdefault("quota_period", "monthly")
        if not data.get("monthly_audio_seconds") and data.get("audio_seconds_limit"):
            data["monthly_audio_seconds"] = data["audio_seconds_limit"]
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


class MeResponse(BaseModel):
    uid: str
    email: str
    email_verified: bool
    status: str
    plan_id: str | None
    subscription_expires_at: datetime | None
    usage: Usage | None = None


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
    session_id: str
    sequence: int
    audio_file: str
    detected_language: str = ""
    transcript_raw: str = ""
    transcript_restored: str = ""
    translation: str = ""
    confidence: float = 0.0
    uncertain_segments: list[str] = Field(default_factory=list)
    processing_notes: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0
    queue_wait_ms: float = 0.0
    error: str | None = None


class Reservation(BaseModel):
    request_id: str
    state: Literal["reserved", "completed", "in_progress"]
    cached_response: dict | None = None
