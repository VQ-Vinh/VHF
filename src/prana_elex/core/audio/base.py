from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

from prana_elex.core.config.schema import AudioConfig


class AudioBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def open_stream(self, config: AudioConfig, callback: Callable[[np.ndarray], None]) -> None: ...

    @abstractmethod
    def close_stream(self) -> None: ...

    @property
    @abstractmethod
    def is_running(self) -> bool: ...

    @property
    @abstractmethod
    def sample_rate(self) -> int: ...
