from __future__ import annotations

import io
import struct
import sys
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from prana_core.audio.exceptions import AudioDeviceNotFoundError
from prana_linux.audio.pulse import PulseBackend


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(struct.pack("<1600h", *([1000] * 1600)))
    return output.getvalue()


class _FakeStream:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.stopped = False
        self.closed = False

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    def stop_stream(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _FakePyAudio:
    def __init__(self, output_channels: int = 2, sample_rate: int = 44100) -> None:
        self.output_channels = output_channels
        self.sample_rate = sample_rate
        self.stream = _FakeStream()
        self.open_kwargs = None
        self.terminated = False

    def get_format_from_width(self, width: int) -> int:
        return width

    def get_device_info_by_index(self, index: int) -> dict:
        return {
            "index": index,
            "maxOutputChannels": self.output_channels,
            "defaultSampleRate": self.sample_rate,
        }

    def get_default_output_device_info(self) -> dict:
        return self.get_device_info_by_index(0)

    def open(self, **kwargs):
        self.open_kwargs = kwargs
        return self.stream

    def terminate(self) -> None:
        self.terminated = True


class LinuxAudioPlaybackTests(unittest.TestCase):
    def test_play_wav_writes_audio_to_selected_output(self) -> None:
        fake = _FakePyAudio()
        module = SimpleNamespace(PyAudio=lambda: fake)

        with patch.dict(sys.modules, {"pyaudio": module}):
            PulseBackend.play_wav(_wav_bytes(), device_index=4)

        self.assertEqual(fake.open_kwargs["output_device_index"], 4)
        self.assertEqual(fake.open_kwargs["channels"], 1)
        self.assertEqual(fake.open_kwargs["rate"], 44100)
        self.assertTrue(fake.stream.writes)
        self.assertEqual(sum(map(len, fake.stream.writes)), 8820)
        self.assertTrue(fake.stream.stopped)
        self.assertTrue(fake.stream.closed)
        self.assertTrue(fake.terminated)

    def test_play_wav_rejects_capture_only_device(self) -> None:
        fake = _FakePyAudio(output_channels=0)
        module = SimpleNamespace(PyAudio=lambda: fake)

        with (
            patch.dict(sys.modules, {"pyaudio": module}),
            self.assertRaises(AudioDeviceNotFoundError),
        ):
            PulseBackend.play_wav(_wav_bytes(), device_index=2)

        self.assertIsNone(fake.open_kwargs)
        self.assertTrue(fake.terminated)


class LinuxAudioCaptureTests(unittest.TestCase):
    def test_alsa_device_name_uses_hardware_identity(self) -> None:
        self.assertEqual(
            PulseBackend._alsa_device_name(
                {"name": "USB Audio Device: - (hw:3,0)"}
            ),
            "hw:3,0",
        )

    def test_capture_reader_emits_complete_ordered_frames(self) -> None:
        first = np.arange(4, dtype="<i2")
        second = np.arange(4, 8, dtype="<i2")

        class ChunkedOutput:
            def __init__(self, value: bytes) -> None:
                self.value = bytearray(value)

            def read(self, size: int = -1) -> bytes:
                if not self.value:
                    backend._running = False
                    return b""
                count = min(size, 3, len(self.value))
                result = bytes(self.value[:count])
                del self.value[:count]
                return result

        backend = PulseBackend()
        backend._running = True
        backend._stream = SimpleNamespace(
            stdout=ChunkedOutput(first.tobytes() + second.tobytes()),
            stderr=None,
            poll=lambda: None,
        )
        observed = []

        backend._read_capture(observed.append, channels=1, frames_per_buffer=4)

        self.assertEqual(len(observed), 2)
        np.testing.assert_array_equal(observed[0].ravel(), first)
        np.testing.assert_array_equal(observed[1].ravel(), second)

if __name__ == "__main__":
    unittest.main()
