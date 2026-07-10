from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from vhf_processor.vad.base import VADBackend, VADState
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)


class SileroVAD(VADBackend):
    def __init__(
        self,
        threshold: float = 0.5,
        model_path: str | Path | None = None,
    ):
        self._threshold = threshold
        self._model = None
        self._init_model(model_path)

    def _init_model(self, model_path: str | Path | None) -> None:
        try:
            import silero_vad
            self._model = silero_vad.load_silero_vad()
            logger.info("Silero VAD model loaded")
        except ImportError:
            logger.warning("silero-vad not installed, attempting torch hub fallback")
            try:
                self._model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    force_reload=False,
                    onnx=False,
                    trust_repo=True,
                )
            except Exception as e:
                logger.error(f"Failed to load Silero VAD model: {e}")
                self._model = None

    def process(self, audio: np.ndarray, sample_rate: int) -> VADState:
        if self._model is None:
            return VADState.SILENCE

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32) / 32768.0

        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)
            sample_rate = 16000

        window_size = 512
        if len(audio) < window_size:
            return VADState.SILENCE

        if len(audio) <= window_size:
            audio_tensor = torch.from_numpy(audio).unsqueeze(0)
            audio_tensor = torch.nn.functional.pad(audio_tensor, (0, window_size - len(audio)))
            with torch.no_grad():
                speech_prob = self._model(audio_tensor, sample_rate).item()
            return VADState.SPEECH if speech_prob >= self._threshold else VADState.SILENCE

        probs = []
        step = window_size // 2
        for start in range(0, len(audio) - window_size + 1, step):
            frame = audio[start:start + window_size]
            audio_tensor = torch.from_numpy(frame).unsqueeze(0)
            with torch.no_grad():
                prob = self._model(audio_tensor, sample_rate).item()
            probs.append(prob)

        max_prob = max(probs) if probs else 0.0
        return VADState.SPEECH if max_prob >= self._threshold else VADState.SILENCE

    def get_speech_timestamps(
        self,
        audio: np.ndarray,
        sample_rate: int,
        min_speech_duration_ms: float = 250,
        min_silence_duration_ms: float = 100,
    ) -> list[dict]:
        if self._model is None:
            return []

        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)
            sample_rate = 16000

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32) / 32768.0

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        audio_tensor = torch.from_numpy(audio)
        window_size = int(sample_rate * 0.032)
        step = int(window_size * 0.5)
        threshold = self._threshold

        probs = []
        for i in range(0, len(audio_tensor) - window_size, step):
            frame = audio_tensor[i : i + window_size].unsqueeze(0)
            with torch.no_grad():
                prob = self._model(frame, sample_rate).item()
            probs.append(prob)

        speech_frames = [i for i, p in enumerate(probs) if p >= threshold]
        if not speech_frames:
            return []

        segments = []
        start = speech_frames[0]
        prev = speech_frames[0]
        min_speech_frames = int(min_speech_duration_ms / (step * 1000 / sample_rate))
        min_silence_frames = int(min_silence_duration_ms / (step * 1000 / sample_rate))

        for i in range(1, len(speech_frames)):
            gap = speech_frames[i] - prev
            if gap > min_silence_frames:
                if prev - start >= min_speech_frames:
                    segments.append({
                        "start": int(start * step),
                        "end": int(prev * step + window_size),
                    })
                start = speech_frames[i]
            prev = speech_frames[i]

        if prev - start >= min_speech_frames:
            segments.append({
                "start": int(start * step),
                "end": int(prev * step + window_size),
            })

        return segments

    def reset(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "silero"

    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return audio
        ratio = target_sr / orig_sr
        new_len = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(audio.dtype)
