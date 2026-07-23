from __future__ import annotations

import difflib
import string
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


_PUNCT = string.punctuation + "\u2026\u2014\u2013''\"\"\u00ab\u00bb"


def _clean(word: str) -> str:
    return word.lower().strip(_PUNCT)


@dataclass
class AudioSegment:
    session_id: str
    sequence: int
    file_path: Path
    duration_ms: int
    sample_rate: int
    timestamp: datetime = field(default_factory=datetime.now)
    vad_latency_ms: float = 0.0
    processed: bool = False


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
    queue_wait_ms: float = 0.0
    error: str | None = None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def json_path(self) -> str:
        stem = self.audio_file.removesuffix(".wav")
        return f"{stem}.json"

    @property
    def corrections(self) -> list[str]:
        if not self.transcript_raw or not self.transcript_restored:
            return []
        raw_words = self.transcript_raw.split()
        restored_words = self.transcript_restored.split()
        matcher = difflib.SequenceMatcher(None, raw_words, restored_words)
        result: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            raw_block = raw_words[i1:i2]
            restored_block = restored_words[j1:j2]
            raw_text = " ".join(raw_block)
            restored_text = " ".join(restored_block)
            if _clean(raw_text) == _clean(restored_text):
                continue
            if tag == "replace":
                result.append(f'"{raw_text}" -> "{restored_text}"')
            elif tag == "delete":
                result.append(f'"{raw_text}" -> (xóa)')
            elif tag == "insert":
                result.append(f'(thêm) -> "{restored_text}"')
        return result
