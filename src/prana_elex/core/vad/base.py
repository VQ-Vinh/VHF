from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np


class VADState(Enum):
    SILENCE = auto()
    SPEECH = auto()


@dataclass
class SpeechSegment:
    start_frame: int
    end_frame: int
    duration_ms: float
    confidence: float = 0.0


class VADBackend(ABC):
    @abstractmethod
    def process(self, audio: np.ndarray, sample_rate: int) -> VADState:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
