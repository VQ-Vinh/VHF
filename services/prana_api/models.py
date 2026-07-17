from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class Plan(BaseModel):
    id: str
    name: str
    monthly_audio_seconds: int = Field(gt=0)
    requests_per_minute: int = Field(gt=0)
    max_concurrency: int = Field(default=2, ge=1, le=10)
    max_devices: int = Field(default=2, ge=1, le=10)


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
        if self.status != "active" or self.subscription_expires_at is None:
            return False
        return self.subscription_expires_at > datetime.now(timezone.utc)


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


class Usage(BaseModel):
    period: str
    used_audio_seconds: int = 0
    reserved_audio_seconds: int = 0
    request_count: int = 0
    monthly_audio_seconds: int

    @computed_field
    @property
    def remaining_audio_seconds(self) -> int:
        return max(0, self.monthly_audio_seconds - self.used_audio_seconds - self.reserved_audio_seconds)


class MeResponse(BaseModel):
    uid: str
    email: str
    email_verified: bool
    status: str
    plan_id: str | None
    subscription_expires_at: datetime | None
    usage: Usage | None = None


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
