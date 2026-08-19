from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
import io
import wave
import threading
from pathlib import Path
from types import SimpleNamespace

from prana_core.station.client import (
    StationApiClient,
    canonical_station_request,
    payload_hash,
)
from prana_core.backend.client import BackendApiError
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


def tx_wav(seconds: float = 0.1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\0\0" * round(16000 * seconds))
    return output.getvalue()


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
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            storage=SimpleNamespace(local=SimpleNamespace(timezone="")),
        )
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

    def test_unpaired_station_stops_a_running_pipeline(self) -> None:
        class Store:
            def get(self, key):
                return "1" if key == "station_provisioned" else None

        class Client:
            identity = SimpleNamespace(store=Store())

            def desired_state(self):
                raise BackendApiError(
                    "STATION_NOT_PAIRED",
                    "Station has not been paired",
                    403,
                )

        class Orchestrator:
            state = PipelineState.RUNNING
            stops = 0

            def stop(self):
                self.stops += 1
                self.state = PipelineState.STOPPING

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.client = Client()
        runtime.orchestrator = Orchestrator()
        runtime._provisioning_notice_shown = False
        runtime._pairing_expires_at = 0

        self.assertIsNone(runtime._desired())
        self.assertEqual(runtime.orchestrator.stops, 1)

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
            storage=SimpleNamespace(local=SimpleNamespace(timezone="")),
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
            storage=SimpleNamespace(local=SimpleNamespace(timezone="")),
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
            storage=SimpleNamespace(local=SimpleNamespace(timezone="")),
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

            def get_status(self):
                return {"startup_error": "AUDIO_INPUT_DEVICE_NOT_FOUND"}

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            translation=SimpleNamespace(target_language="en"),
            audio=SimpleNamespace(capture_mode="device", device_index=1),
            storage=SimpleNamespace(local=SimpleNamespace(timezone="")),
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
        self.assertEqual(runtime.observed_generation, 0)
        self.assertEqual(runtime._command_failed_generation, 3)
        self.assertEqual(
            runtime._command_error, "AUDIO_INPUT_DEVICE_NOT_FOUND"
        )

    def test_tx_files_share_rx_style_filename_and_date_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = StationRuntime.__new__(StationRuntime)
            runtime.config = SimpleNamespace(
                storage=SimpleNamespace(
                    local=SimpleNamespace(
                        tx_source_dir=str(root / "TX" / "source"),
                        tx_output_dir=str(root / "TX" / "output"),
                        tx_result_dir=str(root / "TX" / "results"),
                    )
                )
            )
            filename = "20260805_155923_0001.wav"

            runtime._save_tx_files(
                {"id": "job-1", "audio_filename": filename, "attempt": 1},
                b"source",
                b"output",
                "completed",
            )

            relative = Path("2026/08/05")
            self.assertEqual(
                (root / "TX" / "source" / relative / filename).read_bytes(),
                b"source",
            )
            self.assertEqual(
                (root / "TX" / "output" / relative / filename).read_bytes(),
                b"output",
            )
            receipt = json.loads(
                (root / "TX" / "results" / relative / "20260805_155923_0001.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(receipt["status"], "completed")

    def test_tx_playback_asserts_ptt_only_while_audio_is_playing(self) -> None:
        events = []

        class Ptt:
            def engage(self):
                events.append("ptt-high")

            def release(self):
                events.append("ptt-low")

        class Player:
            def play_wav(self, output, device_index):
                events.append(("play", output, device_index))

        runtime = StationRuntime.__new__(StationRuntime)
        runtime._ptt_controller = Ptt()
        runtime._audio_backend_factory = lambda: Player()
        audio = tx_wav()

        runtime._play_tx_audio(audio, 17)

        self.assertEqual(
            events,
            ["ptt-high", ("play", audio, 17), "ptt-low"],
        )

    def test_tx_playback_releases_ptt_when_audio_output_fails(self) -> None:
        events = []

        class Ptt:
            def engage(self):
                events.append("ptt-high")

            def release(self):
                events.append("ptt-low")

        class Player:
            def play_wav(self, output, device_index):
                events.append("play")
                raise RuntimeError("speaker failed")

        runtime = StationRuntime.__new__(StationRuntime)
        runtime._ptt_controller = Ptt()
        runtime._audio_backend_factory = lambda: Player()

        with self.assertRaisesRegex(RuntimeError, "speaker failed"):
            runtime._play_tx_audio(tx_wav(), -1)

        self.assertEqual(events, ["ptt-high", "play", "ptt-low"])

    def test_tx_playback_releases_ptt_when_assertion_fails(self) -> None:
        events = []

        class Ptt:
            def engage(self):
                events.append("ptt-high-failed")
                raise RuntimeError("gpio failed")

            def release(self):
                events.append("ptt-low")

        class Player:
            def play_wav(self, output, device_index):
                events.append("play")

        runtime = StationRuntime.__new__(StationRuntime)
        runtime._ptt_controller = Ptt()
        runtime._audio_backend_factory = lambda: Player()

        with self.assertRaisesRegex(RuntimeError, "gpio failed"):
            runtime._play_tx_audio(tx_wav(), -1)

        self.assertEqual(events, ["ptt-high-failed", "ptt-low"])

    def test_tx_watchdog_cancels_hung_player_and_releases_ptt(self) -> None:
        events = []

        class Ptt:
            def engage(self):
                events.append("ptt-high")

            def release(self):
                events.append("ptt-low")

        class Player:
            def play_wav(self, _output, _device_index, stop_event=None):
                events.append("play")
                stop_event.wait(5)
                events.append("stopped")

        runtime = StationRuntime.__new__(StationRuntime)
        runtime.config = SimpleNamespace(
            ptt=SimpleNamespace(
                watchdog_seconds=0.05,
                key_up_delay_ms=0,
                tail_delay_ms=0,
            )
        )
        runtime._stop_tx = threading.Event()
        runtime._ptt_controller = Ptt()
        runtime._audio_backend_factory = lambda: Player()

        with self.assertRaisesRegex(RuntimeError, "TX_PLAYBACK_TIMEOUT"):
            runtime._play_tx_audio(tx_wav(), -1)

        self.assertEqual(events[0:2], ["ptt-high", "play"])
        self.assertIn("stopped", events)
        self.assertEqual(events.count("ptt-low"), 1)

    def test_tx_output_over_120_seconds_is_rejected_before_ptt(self) -> None:
        class Ptt:
            def engage(self):
                raise AssertionError("PTT must not be asserted")

            def release(self):
                raise AssertionError("PTT was never asserted")

        runtime = StationRuntime.__new__(StationRuntime)
        runtime._ptt_controller = Ptt()
        runtime._audio_backend_factory = lambda: None

        with self.assertRaisesRegex(RuntimeError, "TX_OUTPUT_TOO_LONG"):
            runtime._play_tx_audio(tx_wav(120.01), -1)


if __name__ == "__main__":
    unittest.main()
