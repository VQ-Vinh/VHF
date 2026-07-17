from __future__ import annotations

import io
import math
import wave
from dataclasses import dataclass

from services.prana_api.errors import api_error


@dataclass(frozen=True)
class AudioInfo:
    seconds: int
    exact_seconds: float


def validate_wav(data: bytes, max_bytes: int, max_seconds: int) -> AudioInfo:
    if len(data) > max_bytes:
        raise api_error(413, "AUDIO_TOO_LARGE", f"Audio exceeds {max_bytes} bytes")
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
    except (wave.Error, EOFError) as exc:
        raise api_error(422, "INVALID_AUDIO", "Audio is not a valid WAV file") from exc
    if channels != 1 or sample_width != 2 or sample_rate != 16000 or frames <= 0:
        raise api_error(422, "INVALID_AUDIO", "Expected mono 16 kHz PCM16 WAV")
    exact = frames / sample_rate
    if exact < 0.1:
        raise api_error(422, "INVALID_AUDIO", "Audio must be at least 100 ms")
    if exact > max_seconds:
        raise api_error(413, "AUDIO_TOO_LARGE", f"Audio exceeds {max_seconds} seconds")
    return AudioInfo(seconds=max(1, math.ceil(exact)), exact_seconds=exact)
