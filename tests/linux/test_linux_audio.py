from __future__ import annotations

import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from prana_core.config.schema import AudioConfig
from prana_linux.audio.pulse import PulseBackend


class _FakeStream:
    def __init__(self) -> None:
        self.read_calls = 0
        self.closed = threading.Event()

    def start_stream(self) -> None:
        pass

    def is_active(self) -> bool:
        return True

    def stop_stream(self) -> None:
        pass

    def close(self) -> None:
        self.closed.set()

    def read(self, frame_count: int, exception_on_overflow: bool = True) -> bytes:
        self.read_calls += 1
        if self.read_calls == 1:
            return np.ones(frame_count, dtype=np.int16).tobytes()
        self.closed.wait(timeout=0.01)
        return np.ones(frame_count, dtype=np.int16).tobytes()


class _FakePyAudio:
    def __init__(self) -> None:
        self.stream = _FakeStream()

    def get_device_count(self) -> int:
        return 1

    def get_device_info_by_index(self, _index: int) -> dict:
        return {
            "index": 0,
            "name": "USB Audio",
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }

    def open(self, **kwargs):
        self.open_kwargs = kwargs
        return self.stream


class LinuxAudioTests(unittest.TestCase):
    def test_capture_thread_does_not_wait_for_vad_processing(self) -> None:
        fake_pa = _FakePyAudio()
        entered = threading.Event()
        release = threading.Event()
        received = threading.Event()

        def slow_callback(_audio: np.ndarray) -> None:
            entered.set()
            release.wait(timeout=2)
            received.set()

        fake_module = SimpleNamespace(paInt16=8, paContinue=0)
        backend = PulseBackend()
        with (
            patch.object(PulseBackend, "_get_pa", return_value=fake_pa),
            patch.dict(sys.modules, {"pyaudio": fake_module}),
        ):
            backend.open_stream(AudioConfig(device_index=0), slow_callback)
            self.assertTrue(entered.wait(timeout=1))
            first_read_count = fake_pa.stream.read_calls
            time.sleep(0.05)
            self.assertGreater(fake_pa.stream.read_calls, first_read_count)
            release.set()
            self.assertTrue(received.wait(timeout=1))
            backend.close_stream()


if __name__ == "__main__":
    unittest.main()
