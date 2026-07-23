from __future__ import annotations

import numpy as np


def split_audio_buffer(
    buffer: list[np.ndarray], max_samples: int
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Split buffered audio into exact non-overlapping chunks and a remainder."""
    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    if not buffer:
        return [], []

    combined = np.concatenate(buffer, axis=0)
    chunks: list[np.ndarray] = []
    offset = 0
    while len(combined) - offset >= max_samples:
        chunks.append(combined[offset : offset + max_samples])
        offset += max_samples
    remainder = combined[offset:]
    return chunks, [remainder] if len(remainder) else []


def resample_audio(audio: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
    """Resample mono audio while preserving its input dtype."""
    if original_rate == target_rate:
        return audio
    if audio.ndim > 1:
        audio = audio.squeeze()
    ratio = target_rate / original_rate
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio).astype(audio.dtype)


def trim_trailing_silence(
    audio: np.ndarray,
    sample_rate: int,
    *,
    threshold: float = 50,
    frame_seconds: float = 0.032,
) -> np.ndarray:
    """Remove only complete silent frames from the end of a segment."""
    if len(audio) == 0:
        return audio
    frame_length = int(sample_rate * frame_seconds)
    if len(audio) <= frame_length:
        return audio
    audio_float = audio.astype(np.float32)
    end = len(audio)
    while end > frame_length:
        frame = audio_float[end - frame_length:end]
        if np.sqrt(np.mean(frame ** 2)) >= threshold:
            break
        end -= frame_length
    return audio[:end]
