from __future__ import annotations

import unittest

from prana_elex.audio.exceptions import AudioDeviceNotFoundError
from prana_elex.audio.wasapi import WASAPIBackend


class _FakePyAudio:
    def __init__(self, devices: list[dict]) -> None:
        self._devices = devices

    def get_device_count(self) -> int:
        return len(self._devices)

    def get_device_info_by_index(self, index: int) -> dict:
        if index < 0 or index >= len(self._devices):
            raise OSError("invalid device index")
        return self._devices[index]


def _device(index: int, name: str, inputs: int = 2) -> dict:
    return {
        "index": index,
        "name": name,
        "maxInputChannels": inputs,
        "defaultSampleRate": 48000,
    }


class WASAPILoopbackSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = WASAPIBackend()
        self.pa = _FakePyAudio(
            [
                _device(0, "HP 19ka (NVIDIA High Definition Audio) [Loopback]"),
                _device(1, "Speaker (Realtek(R) Audio) [Loopback]"),
                _device(2, "Microphone (Realtek(R) Audio)"),
            ]
        )

    def test_explicit_selection_is_used_instead_of_first_hdmi_loopback(self) -> None:
        selected = self.backend._find_loopback_device(self.pa, 1)

        self.assertEqual(selected["index"], 1)
        self.assertIn("Realtek", selected["name"])

    def test_auto_selection_is_only_used_without_an_explicit_device(self) -> None:
        selected = self.backend._find_loopback_device(self.pa, -1)

        self.assertEqual(selected["index"], 0)
        self.assertIn("HP 19ka", selected["name"])

    def test_invalid_explicit_selection_does_not_fall_back_to_hdmi(self) -> None:
        with self.assertRaisesRegex(
            AudioDeviceNotFoundError, "is not a WASAPI loopback input"
        ):
            self.backend._find_loopback_device(self.pa, 2)

    def test_missing_explicit_selection_does_not_fall_back_to_hdmi(self) -> None:
        with self.assertRaisesRegex(
            AudioDeviceNotFoundError, "Loopback device index 99 not found"
        ):
            self.backend._find_loopback_device(self.pa, 99)


if __name__ == "__main__":
    unittest.main()
