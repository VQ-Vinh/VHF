from __future__ import annotations

import numpy as np

from vhf_processor.vad.base import VADBackend, VADState
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)


class WebRTCVAD(VADBackend):
    def __init__(self, threshold: float = 0.5):
        self._threshold = threshold
        self._vad = None
        self._init_vad()

    def _init_vad(self) -> None:
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad()
            aggressiveness = self._map_threshold(self._threshold)
            self._vad.set_mode(aggressiveness)
        except ImportError:
            logger.warning("webrtcvad not installed, WebRTC VAD unavailable")
            self._vad = None

    def process(self, audio: np.ndarray, sample_rate: int) -> VADState:
        if self._vad is None:
            return VADState.SILENCE

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        if sample_rate not in (8000, 16000, 32000, 48000):
            if sample_rate > 48000:
                audio = self._downsample(audio, sample_rate, 48000)
                sample_rate = 48000
            else:
                audio = self._downsample(audio, sample_rate, 16000)
                sample_rate = 16000

        audio_int16 = (audio * 32767).astype(np.int16) if audio.dtype == np.float32 else audio
        frame_size = int(sample_rate * 0.03)
        if len(audio_int16) < frame_size:
            return VADState.SILENCE

        pcm = audio_int16[:frame_size].tobytes()
        try:
            is_speech = self._vad.is_speech(pcm, sample_rate)
            return VADState.SPEECH if is_speech else VADState.SILENCE
        except Exception:
            return VADState.SILENCE

    def reset(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "webrtc"

    @staticmethod
    def _map_threshold(threshold: float) -> int:
        if threshold < 0.3:
            return 3
        if threshold < 0.5:
            return 2
        if threshold < 0.7:
            return 1
        return 0

    @staticmethod
    def _downsample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        ratio = orig_sr // target_sr
        return audio[::ratio]
