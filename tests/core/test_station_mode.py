from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from prana_core.station.client import canonical_station_request, payload_hash
from prana_core.station.identity import StationIdentity
from prana_core.station.runtime import StationRuntime
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


if __name__ == "__main__":
    unittest.main()
