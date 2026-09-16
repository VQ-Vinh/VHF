"""Microphone capture for operator TX.

The console does not run an RX pipeline any more, but transmitting still needs
the local microphone. This produces exactly the WAV the API expects — 16 kHz,
mono, PCM16 — matching `apps/android/lib/data/radio/tx_recorder.dart` so a
transmission composed on the desktop is byte-compatible with one composed on
the phone.
"""

from __future__ import annotations

import io
import threading
import wave

import numpy as np

from prana_core.config.schema import AudioConfig
from prana_core.pipeline.audio_utils import resample_audio
from prana_windows.audio.wasapi import WASAPIBackend

TX_SAMPLE_RATE = 16000
_CAPTURE_RATE = 48000


class TxRecorder:
    """Records mono PCM from a capture device into a 16 kHz WAV."""

    def __init__(self, backend_factory=WASAPIBackend):
        self._backend_factory = backend_factory
        self._backend = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, device_index: int = -1) -> None:
        if self._recording:
            return
        with self._lock:
            self._frames = []
        backend = self._backend_factory()
        config = AudioConfig(
            capture_mode="device",
            sample_rate=_CAPTURE_RATE,
            channels=1,
            dtype="int16",
            device_index=device_index,
        )
        backend.open_stream(config, self._on_frame)
        self._backend = backend
        self._recording = True

    def _on_frame(self, audio: np.ndarray) -> None:
        with self._lock:
            self._frames.append(np.asarray(audio, dtype=np.int16).reshape(-1))

    def stop(self) -> bytes:
        """Stop capture and return the recording as WAV bytes."""
        backend, self._backend = self._backend, None
        self._recording = False
        if backend is not None:
            try:
                backend.close_stream()
            except Exception:  # noqa: BLE001 - a failed close must still yield audio
                pass
        with self._lock:
            frames, self._frames = self._frames, []
        if not frames:
            return b""
        audio = np.concatenate(frames)
        audio = resample_audio(audio, _CAPTURE_RATE, TX_SAMPLE_RATE)
        return encode_wav(audio)

    def cancel(self) -> None:
        self.stop()

    @property
    def duration_seconds(self) -> float:
        with self._lock:
            samples = sum(len(frame) for frame in self._frames)
        return samples / _CAPTURE_RATE


def encode_wav(audio: np.ndarray, sample_rate: int = TX_SAMPLE_RATE) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(np.asarray(audio, dtype=np.int16).tobytes())
    return buffer.getvalue()


__all__ = ["TX_SAMPLE_RATE", "TxRecorder", "encode_wav"]
