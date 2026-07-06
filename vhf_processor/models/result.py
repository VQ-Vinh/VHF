from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProcessingResult(BaseModel):
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
    timestamp: datetime = Field(default_factory=datetime.now)
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def json_path(self) -> str:
        stem = self.audio_file.removesuffix(".wav")
        return f"{stem}.json"
