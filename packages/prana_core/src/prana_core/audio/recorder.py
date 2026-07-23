from __future__ import annotations

from typing import Callable

import numpy as np

from prana_core.audio.base import AudioBackend
from prana_core.config.schema import AudioConfig
from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    def __init__(
        self,
        config: AudioConfig,
        callback: Callable[[np.ndarray], None],
        backend_factory: Callable[[], AudioBackend],
    ):
        self._config = config
        self._callback = callback
        self._backend_factory = backend_factory
        self._backend: AudioBackend | None = None

    def start(self) -> None:
        self._backend = self._backend_factory()
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

    def list_devices(self) -> list[dict]:
        return self._backend_factory().list_devices()
