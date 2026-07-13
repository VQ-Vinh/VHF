from __future__ import annotations

import sys
from typing import Callable

import numpy as np

from prana_elex.core.audio.base import AudioBackend
from prana_elex.core.config.schema import AudioConfig
from prana_elex.core.utils.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    def __init__(self, config: AudioConfig, callback: Callable[[np.ndarray], None]):
        self._config = config
        self._callback = callback
        self._backend: AudioBackend | None = None

    @staticmethod
    def _resolve_backend() -> type[AudioBackend]:
        if sys.platform == "win32":
            from prana_elex.core.audio.wasapi_backend import WASAPIBackend
            return WASAPIBackend
        else:
            from prana_elex.core.audio.pulse_backend import PulseBackend
            return PulseBackend

    def start(self) -> None:
        backend_cls = self._resolve_backend()
        self._backend = backend_cls()
        self._backend.open_stream(self._config, self._callback)
        logger.info("AudioRecorder started", extra={"backend": self._backend.name})

    def stop(self) -> None:
        if self._backend is not None:
            self._backend.close_stream()
            self._backend = None

    @property
    def is_running(self) -> bool:
        return self._backend is not None and self._backend.is_running

    @property
    def sample_rate(self) -> int:
        if self._backend is not None:
            return self._backend.sample_rate
        return 0

    @staticmethod
    def list_devices() -> list[dict]:
        backend_cls = AudioRecorder._resolve_backend()
        return backend_cls.list_devices()
