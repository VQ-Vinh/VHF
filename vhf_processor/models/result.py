from __future__ import annotations

import difflib
import string
from datetime import datetime

from pydantic import BaseModel, Field


_PUNCT = string.punctuation + "…—–''\"\"«»"


def _clean(w: str) -> str:
    return w.lower().strip(_PUNCT)


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
        r_words = self.transcript_raw.split()
        t_words = self.transcript_restored.split()
        matcher = difflib.SequenceMatcher(None, r_words, t_words)
        result: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            r_block, t_block = r_words[i1:i2], t_words[j1:j2]
            r_joined = " ".join(r_block)
            t_joined = " ".join(t_block)
            if _clean(r_joined) == _clean(t_joined):
                continue
            if tag == "replace":
                result.append(f'"{r_joined}" -> "{t_joined}"')
            elif tag == "delete":
                result.append(f'"{r_joined}" -> (xóa)')
            elif tag == "insert":
                result.append(f"(thêm) -> \"{t_joined}\"")
        return result
