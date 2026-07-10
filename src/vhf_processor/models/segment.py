from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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
