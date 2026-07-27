from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from prana_core.station.client import (
    StationApiClient,
    canonical_station_request,
    payload_hash,
)
from prana_core.station.identity import StationIdentity
from prana_core.station.runtime import StationRuntime
from prana_core.audio.capabilities import normalize_audio_devices
from prana_core.station.label import grouped, qr_payload, write_label
from prana_core.pipeline.orchestrator import PipelineState


class DictStore:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


class StationModeTests(unittest.TestCase):
    def test_station_control_timeout_allows_slow_firestore_round_trips(self) -> None:
        client = StationApiClient(
            "http://127.0.0.1:8080",
            StationIdentity(DictStore()),
            timeout_seconds=150,
        )
        self.assertEqual(client.control_timeout, 60)

    def test_capability_scan_accepts_a_callable_backend_factory(self) -> None:
        class Backend:
            def list_devices(self):
                return [{
                    "index": 3,
                    "name": "Microphone",
                    "inputs": 1,
                    "outputs": 0,
                    "sr": 48000,
                    "host_api": "WASAPI",
                }]

        class Client:
            published = None

            def publish_capabilities(self, payload):
                self.published = payload

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            general=SimpleNamespace(data_dir=Path("data")),
        )
        runtime.client = Client()
        runtime._audio_backend_factory = lambda: Backend()
        runtime._next_capability_scan = 0
        runtime._published_capability_hash = ""
        runtime._device_indices = {}
        runtime._device_modes = {}

        runtime._scan_capabilities(force=True)

        self.assertEqual(
            runtime.client.published["audio_devices"][0]["name"],
            "Microphone",
        )
        device_id = runtime.client.published["audio_devices"][0]["id"]
        self.assertEqual(runtime._device_indices[device_id], 3)
        self.assertEqual(runtime._device_modes[device_id], "device")

    def test_audio_capability_ids_are_stable_and_separate_by_mode(self) -> None:
        devices = [{
            "index": 7,
            "name": "USB SoundCard",
            "inputs": 1,
            "outputs": 2,
            "sr": 48000,
            "host_api": "WASAPI",
        }]
        loopbacks = [{
            "index": 9,
            "name": "USB SoundCard",
            "inputs": 2,
            "outputs": 0,
            "sr": 48000,
            "host_api": "WASAPI",
        }]
        first, indices = normalize_audio_devices(devices, loopbacks)
        second, _ = normalize_audio_devices(devices, loopbacks)
        self.assertEqual(first, second)
        self.assertNotEqual(first[0]["id"], first[1]["id"])
        self.assertEqual(indices[first[0]["id"]], 7)

    def test_station_identity_survives_restart(self) -> None:
        store = DictStore()
        first = StationIdentity(store)
        signature = first.sign(b"proof")
        second = StationIdentity(store)
        self.assertEqual(second.id, first.id)
        self.assertEqual(second.public_key, first.public_key)
        self.assertEqual(second.sign(b"proof"), signature)

    def test_client_and_server_canonical_json_signatures_match(self) -> None:
        payload = {"target_language": "vi", "running": True, "generation": 2}
        digest = payload_hash(payload)
        expected_digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(digest, expected_digest)
        self.assertEqual(
            canonical_station_request("POST", "/heartbeat", "request", "123", digest),
            f"POST\n/heartbeat\nrequest\n123\n{digest}".encode(),
        )

    def test_printed_label_contains_public_activation_data_not_private_key(self) -> None:
        setup_id = "ABCDEFGH23"
        activation_code = "ABCDEFGH23456789"
        with tempfile.TemporaryDirectory() as directory:
            png, svg = write_label(Path(directory), setup_id, activation_code)
            self.assertTrue(png.exists())
            contents = svg.read_text(encoding="utf-8")
            self.assertIn(setup_id, contents)
            self.assertIn(grouped(activation_code), contents)
            self.assertNotIn("private_key", contents)
            self.assertEqual(
                qr_payload(setup_id, activation_code),
                f"prana-elex:///activate?v=1&id={setup_id}&code={activation_code}",
            )

    def test_desired_state_controls_pipeline_language_and_retry(self) -> None:
        class Orchestrator:
            state = PipelineState.IDLE
            retries = 0

            def start(self):
                self.state = PipelineState.RUNNING

            def stop(self):
                self.state = PipelineState.IDLE

            def retry_last_failed(self):
                self.retries += 1
                return True

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(translation=SimpleNamespace(target_language="en"))
        runtime.orchestrator = Orchestrator()
        runtime.observed_generation = 0
        runtime.retry_generation = 0

        runtime._apply({
            "running": True,
            "target_language": "vi",
            "retry_generation": 1,
            "generation": 4,
        })
        self.assertEqual(runtime.orchestrator.state, PipelineState.RUNNING)
        self.assertEqual(runtime.config.translation.target_language, "vi")
        self.assertEqual(runtime.orchestrator.retries, 1)
        self.assertEqual(runtime.observed_generation, 4)

        runtime._apply({
            "running": False,
            "target_language": "vi",
            "retry_generation": 1,
            "generation": 5,
        })
        self.assertEqual(runtime.orchestrator.state, PipelineState.IDLE)
        self.assertEqual(runtime.observed_generation, 5)

    def test_audio_change_restarts_running_pipeline_and_applies_generation(self) -> None:
        class Orchestrator:
            state = PipelineState.RUNNING
            restarts = 0

            def restart(self):
                self.restarts += 1
                self.state = PipelineState.RUNNING

            def retry_last_failed(self):
                return False

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            audio=SimpleNamespace(capture_mode="device", device_index=1),
        )
        runtime.orchestrator = Orchestrator()
        runtime.observed_generation = 2
        runtime.retry_generation = 0
        runtime._device_indices = {"loopback-id": 8}
        runtime._last_capability_refresh_generation = 0
        runtime._failed_audio_generation = -1
        runtime._last_start_attempt = None
        runtime._station_error = None

        runtime._apply({
            "running": True,
            "target_language": "en",
            "retry_generation": 0,
            "capture_mode": "loopback",
            "audio_device_id": "loopback-id",
            "generation": 3,
        })

        self.assertEqual(runtime.orchestrator.restarts, 1)
        self.assertEqual(runtime.config.audio.capture_mode, "loopback")
        self.assertEqual(runtime.config.audio.device_index, 8)
        self.assertEqual(runtime.observed_generation, 3)

    def test_stale_audio_device_falls_back_and_acknowledges_generation(self) -> None:
        class Orchestrator:
            state = PipelineState.IDLE

            def retry_last_failed(self):
                return False

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            audio=SimpleNamespace(capture_mode="device", device_index=4),
        )
        runtime.orchestrator = Orchestrator()
        runtime.observed_generation = 2
        runtime.retry_generation = 0
        runtime._device_indices = {}
        runtime._last_capability_refresh_generation = 0
        runtime._failed_audio_generation = -1
        runtime._last_start_attempt = None
        runtime._station_error = None

        runtime._apply({
            "running": False,
            "target_language": "en",
            "retry_generation": 0,
            "capture_mode": "loopback",
            "audio_device_id": "removed-device",
            "generation": 3,
        })

        self.assertEqual(runtime.config.audio.capture_mode, "loopback")
        self.assertEqual(runtime.config.audio.device_index, -1)
        self.assertEqual(runtime.observed_generation, 3)
        self.assertIsNone(runtime._station_error)

    def test_audio_change_rolls_back_when_restart_fails(self) -> None:
        class Orchestrator:
            state = PipelineState.RUNNING
            starts = 0

            def restart(self):
                self.state = PipelineState.ERROR

            def start(self):
                self.starts += 1
                self.state = PipelineState.RUNNING

            def retry_last_failed(self):
                return False

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            audio=SimpleNamespace(capture_mode="device", device_index=1),
        )
        runtime.orchestrator = Orchestrator()
        runtime.observed_generation = 2
        runtime.retry_generation = 0
        runtime._device_indices = {"loopback-id": 8}
        runtime._last_capability_refresh_generation = 0
        runtime._failed_audio_generation = -1
        runtime._last_start_attempt = None
        runtime._station_error = None

        runtime._apply({
            "running": True,
            "target_language": "en",
            "retry_generation": 0,
            "capture_mode": "loopback",
            "audio_device_id": "loopback-id",
            "generation": 3,
        })

        self.assertEqual(runtime.config.audio.capture_mode, "device")
        self.assertEqual(runtime.config.audio.device_index, 1)
        self.assertEqual(runtime.orchestrator.starts, 1)
        self.assertEqual(runtime.observed_generation, 2)
        self.assertEqual(runtime._station_error, "AUDIO_DEVICE_UNAVAILABLE")

    def test_failed_start_is_not_retried_for_same_generation(self) -> None:
        class Orchestrator:
            state = PipelineState.ERROR
            starts = 0

            def start(self):
                self.starts += 1
                self.state = PipelineState.ERROR

            def retry_last_failed(self):
                return False

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            audio=SimpleNamespace(capture_mode="device", device_index=1),
        )
        runtime.orchestrator = Orchestrator()
        runtime.observed_generation = 0
        runtime.retry_generation = 0
        runtime._device_indices = {}
        runtime._last_capability_refresh_generation = 0
        runtime._failed_audio_generation = -1
        runtime._last_start_attempt = None
        runtime._station_error = None
        desired = {
            "running": True,
            "target_language": "en",
            "retry_generation": 0,
            "capture_mode": "device",
            "generation": 3,
        }

        runtime._apply(desired)
        runtime._apply(desired)

        self.assertEqual(runtime.orchestrator.starts, 1)


if __name__ == "__main__":
    unittest.main()
