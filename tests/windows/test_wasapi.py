from __future__ import annotations

import unittest
from unittest.mock import patch

from prana_core.audio.exceptions import AudioDeviceNotFoundError
from prana_windows.audio.wasapi import WASAPIBackend


class _FakePyAudio:
    def __init__(self, devices: list[dict]) -> None:
        self._devices = devices
        self.terminated = False

    def get_device_count(self) -> int:
        return len(self._devices)

    def get_device_info_by_index(self, index: int) -> dict:
        if index < 0 or index >= len(self._devices):
            raise OSError("invalid device index")
        return self._devices[index]

    def get_host_api_info_by_index(self, index: int) -> dict:
        return {"name": f"Host API {index}"}

    def terminate(self) -> None:
        self.terminated = True


def _device(
    index: int,
    name: str,
    inputs: int = 2,
    outputs: int = 0,
) -> dict:
    return {
        "index": index,
        "name": name,
        "maxInputChannels": inputs,
        "maxOutputChannels": outputs,
        "defaultSampleRate": 48000,
        "hostApi": 0,
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

    def test_discovery_terminates_before_capture_starts(self) -> None:
        with patch.object(
            WASAPIBackend,
            "_new_pa",
            return_value=self.pa,
        ) as get_pa:
            all_devices = WASAPIBackend.list_devices()
            loopbacks = WASAPIBackend.list_loopback_devices()

        self.assertEqual(get_pa.call_count, 2)
        self.assertEqual([item["index"] for item in all_devices], [0, 1, 2])
        self.assertEqual([item["index"] for item in loopbacks], [0, 1])
        self.assertTrue(self.pa.terminated)

    def test_selected_loopback_is_resolved_after_device_indices_shift(self) -> None:
        expected = self.backend._device_identity(
            self.pa.get_device_info_by_index(1)
        )
        shifted = _FakePyAudio(
            [
                _device(0, "Speaker (Realtek(R) Audio) [Loopback]"),
                _device(1, "HP 19ka (NVIDIA High Definition Audio) [Loopback]"),
            ]
        )

        selected = self.backend._find_loopback_device(
            shifted,
            1,
            expected_identity=expected,
        )

        self.assertEqual(selected["index"], 0)
        self.assertIn("Realtek", selected["name"])


if __name__ == "__main__":
    unittest.main()
