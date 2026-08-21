from __future__ import annotations

import base64
import hashlib
import io
import time
import unittest
import uuid
import wave
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from unittest.mock import patch

from services.prana_api.auth import Identity, require_identity
from services.prana_api.main import app, get_repository, get_tx_repository
from services.prana_api.google_services import ModelResult
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.storage_paths import station_storage_folder
from services.prana_api.models import Plan, ProcessingResponse, UserAccount
from services.prana_api.security import canonical_request, canonical_station_request, station_payload_hash
from services.prana_api.tx_repository import MemoryTxRepository


def wav_bytes(seconds: float = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0" * round(32000 * seconds))
    return output.getvalue()


class Processor:
    calls = 0

    def process(self, _audio, _target, session_id, sequence, _request_id):
        type(self).calls += 1
        return ModelResult(
            response=ProcessingResponse(
                session_id=session_id,
                sequence=sequence,
                audio_file="segment.wav",
                transcript_restored="Mayday received.",
                translation="Đã nhận tín hiệu cấp cứu.",
                confidence=0.94,
            ),
            metrics={"model": "fake"},
        )


class Archive:
    def __init__(self):
        self.audio = {}
        self.station_calls = []
        self.tx_source_calls = []
        self.tx_output_calls = []

    def archive(self, *_args):
        uid, session_id, request_id, audio, _response = _args
        object_name = f"customers/{uid}/{session_id}/{request_id}.wav"
        self.audio[object_name] = audio
        return object_name

    def archive_station(
        self,
        station_id,
        station_name,
        audio_filename,
        date_path,
        audio,
        response,
    ):
        object_name = (
            f"VHF-Storage/{station_name}_{station_id[:8]}/audio/"
            f"{date_path}/{audio_filename}"
        )
        self.station_calls.append(
            {
                "station_id": station_id,
                "station_name": station_name,
                "audio_filename": audio_filename,
                "date_path": date_path,
                "response": dict(response),
            }
        )
        self.audio[object_name] = audio
        return object_name

    def download_audio(self, object_name):
        return self.audio.get(object_name)

    def archive_tx_source(self, station_id, station_name, audio_filename, date_path, source):
        source_object = (
            f"VHF-Storage/{station_name}_{station_id[:8]}/TX/source/"
            f"{date_path}/{audio_filename}"
        )
        self.tx_source_calls.append(
            {"audio_filename": audio_filename, "date_path": date_path}
        )
        self.audio[source_object] = source
        return source_object

    def archive_tx_output(self, station_id, station_name, audio_filename, date_path, output, _metadata):
        output_object = (
            f"VHF-Storage/{station_name}_{station_id[:8]}/TX/output/"
            f"{date_path}/{audio_filename}"
        )
        self.tx_output_calls.append(
            {"audio_filename": audio_filename, "date_path": date_path}
        )
        self.audio[output_object] = output
        return output_object


class Synthesizer:
    texts = []

    def synthesize_with_over(self, text, _target_language):
        type(self).texts.append(text)
        return wav_bytes()


class StationApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.repo.plans["free"] = Plan(
            id="free",
            name="Free",
            audio_seconds_limit=600,
            requests_per_minute=30,
            max_devices=2,
            max_stations=2,
        )
        self.identity = Identity("owner-1", "owner@example.com", True)
        self.repo.users[self.identity.uid] = UserAccount(
            uid=self.identity.uid,
            email=self.identity.email,
            email_verified=True,
            status="active",
            plan_id="free",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        app.dependency_overrides[get_repository] = lambda: self.repo
        app.dependency_overrides[require_identity] = lambda: self.identity
        self.tx_repo = MemoryTxRepository()
        app.dependency_overrides[get_tx_repository] = lambda: self.tx_repo
        self.client = TestClient(app, raise_server_exceptions=False)
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.station_id = uuid.uuid4().hex
        self.pairing_payload = {
            "station_id": self.station_id,
            "name": "Bridge Pi",
            "platform": "Linux aarch64",
            "public_key": base64.b64encode(public).decode("ascii"),
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    def signed_headers(self, method: str, path: str, payload: dict, request_id: str | None = None):
        request_id = request_id or str(uuid.uuid4())
        timestamp = str(int(time.time()))
        signature = self.private.sign(
            canonical_station_request(
                method, path, request_id, timestamp, station_payload_hash(payload)
            )
        )
        return {
            "X-Station-ID": self.station_id,
            "X-Request-ID": request_id,
            "X-Timestamp": timestamp,
            "X-Signature": base64.b64encode(signature).decode("ascii"),
        }

    def create_and_claim(self):
        path = "/v1/station-pairings"
        pairing = self.client.post(
            path,
            json=self.pairing_payload,
            headers=self.signed_headers("POST", path, self.pairing_payload),
        )
        self.assertEqual(pairing.status_code, 200, pairing.text)
        value = pairing.json()
        claim = self.client.post(
            f"/v1/station-pairings/{value['pairing_id']}/claim",
            json={"pairing_code": value["pairing_code"]},
        )
        self.assertEqual(claim.status_code, 200, claim.text)
        return value

    def heartbeat(self, **overrides):
        path = f"/v1/stations/{self.station_id}/heartbeat"
        payload = {
            "capture_state": "listening",
            "session_id": "session-1",
            "sequence": 0,
            "observed_generation": 0,
            "target_language": "en",
            "active_capture_mode": "device",
            "active_audio_device_id": "usb-input",
            "tx_state": "idle",
            "tx_job_id": "",
            "active_tx_audio_device_id": "usb-output",
            "ptt_mode": "gpio",
            "ptt_ready": True,
        }
        payload.update(overrides)
        response = self.client.post(
            path,
            json=payload,
            headers=self.signed_headers("POST", path, payload),
        )
        self.assertEqual(response.status_code, 204, response.text)

    def provision(self, activation_code: str = "ABCDEFGH23456789"):
        path = "/v1/station-provisions"
        payload = {
            **self.pairing_payload,
            "activation_hash": hashlib.sha256(
                f"{self.station_id}:{activation_code}".encode("utf-8")
            ).hexdigest(),
            "activation_version": 1,
        }
        response = self.client.post(
            path,
            json=payload,
            headers=self.signed_headers("POST", path, payload),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), activation_code

    def test_static_activation_claim_is_idempotent_for_owner_and_private_key_is_absent(self):
        provisioned, code = self.provision()
        claim_payload = {"setup_id": provisioned["setup_id"], "activation_code": code}
        first = self.client.post("/v1/station-activations/claim", json=claim_payload)
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.post("/v1/station-activations/claim", json=claim_payload)
        self.assertEqual(second.status_code, 200, second.text)
        registry = self.repo.station_registry[self.station_id]
        self.assertNotIn("private_key", registry)
        self.assertNotIn("activation_code", registry)
        self.assertEqual(registry["activation_claimed_at"].tzinfo, timezone.utc)

    def test_station_provisioning_is_idempotent_and_rejects_activation_change(self):
        first, _ = self.provision()
        second, _ = self.provision()
        self.assertEqual(second["setup_id"], first["setup_id"])
        path = "/v1/station-provisions"
        changed = {
            **self.pairing_payload,
            "activation_hash": "a" * 64,
            "activation_version": 1,
        }
        response = self.client.post(
            path,
            json=changed,
            headers=self.signed_headers("POST", path, changed),
        )
        self.assertEqual(response.status_code, 409)

    def test_static_activation_rejects_wrong_code_and_active_other_owner(self):
        provisioned, code = self.provision()
        path = "/v1/station-activations/claim"
        self.assertEqual(
            self.client.post(
                path,
                json={"setup_id": provisioned["setup_id"], "activation_code": "ZZZZZZZZZZZZZZZZ"},
            ).status_code,
            403,
        )
        payload = {"setup_id": provisioned["setup_id"], "activation_code": code}
        self.assertEqual(self.client.post(path, json=payload).status_code, 200)
        other = Identity("owner-2", "other@example.com", True)
        self.repo.users[other.uid] = UserAccount(
            uid=other.uid,
            email=other.email,
            email_verified=True,
            status="active",
            plan_id="free",
        )
        app.dependency_overrides[require_identity] = lambda: other
        self.assertEqual(self.client.post(path, json=payload).status_code, 409)
        app.dependency_overrides[require_identity] = lambda: self.identity
        self.assertEqual(self.client.delete(f"/v1/stations/{self.station_id}").status_code, 204)
        self.assertEqual(self.client.get("/v1/stations").json(), [])
        registry = self.repo.station_registry[self.station_id]
        self.assertTrue(registry["active"])
        self.assertIsNone(registry["owner_uid"])

        app.dependency_overrides[require_identity] = lambda: other
        reclaimed = self.client.post(path, json=payload)
        self.assertEqual(reclaimed.status_code, 200, reclaimed.text)
        self.assertEqual(reclaimed.json()["station_id"], self.station_id)
        self.assertEqual(
            self.repo.station_registry[self.station_id]["owner_uid"],
            other.uid,
        )
        self.assertFalse(
            self.repo.station_projections[self.identity.uid][self.station_id][
                "active"
            ]
        )

    def test_static_activation_attempts_are_rate_limited(self):
        provisioned, code = self.provision()
        path = "/v1/station-activations/claim"
        for _ in range(5):
            self.assertEqual(
                self.client.post(
                    path,
                    json={"setup_id": provisioned["setup_id"], "activation_code": "ZZZZZZZZZZZZZZZZ"},
                ).status_code,
                403,
            )
        limited = self.client.post(
            path,
            json={"setup_id": provisioned["setup_id"], "activation_code": code},
        )
        self.assertEqual(limited.status_code, 429)

    def test_released_station_keeps_old_results_isolated_from_new_owner(self):
        provisioned, code = self.provision()
        payload = {
            "setup_id": provisioned["setup_id"],
            "activation_code": code,
        }
        self.assertEqual(
            self.client.post(
                "/v1/station-activations/claim",
                json=payload,
            ).status_code,
            200,
        )
        old_result = {
            "request_id": str(uuid.uuid4()),
            "session_id": "session-old",
            "sequence": 1,
            "audio_file": "segment.wav",
            "translation": "Old owner result",
            "timestamp": datetime.now(timezone.utc),
        }
        self.repo.publish_station_result(
            self.identity.uid,
            self.station_id,
            old_result,
        )
        self.assertEqual(
            self.client.delete(
                f"/v1/stations/{self.station_id}",
            ).status_code,
            204,
        )
        self.assertIn(
            (
                self.identity.uid,
                self.station_id,
                "session-old",
                old_result["request_id"],
            ),
            self.repo.station_results,
        )

        other = Identity("owner-2", "other@example.com", True)
        self.repo.users[other.uid] = UserAccount(
            uid=other.uid,
            email=other.email,
            email_verified=True,
            status="active",
            plan_id="free",
        )
        app.dependency_overrides[require_identity] = lambda: other
        self.assertEqual(
            self.client.post(
                "/v1/station-activations/claim",
                json=payload,
            ).status_code,
            200,
        )
        results = self.client.get(
            f"/v1/stations/{self.station_id}/sessions/session-old/results"
        )
        self.assertEqual(results.status_code, 200, results.text)
        self.assertEqual(results.json(), [])

    def test_activation_still_enforces_target_owner_station_limit(self):
        provisioned, code = self.provision()
        self.repo.station_projections[self.identity.uid] = {
            "existing-1": {
                "name": "One",
                "platform": "test",
                "active": True,
            },
            "existing-2": {
                "name": "Two",
                "platform": "test",
                "active": True,
            },
        }
        response = self.client.post(
            "/v1/station-activations/claim",
            json={
                "setup_id": provisioned["setup_id"],
                "activation_code": code,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"]["code"],
            "STATION_LIMIT_REACHED",
        )

    def test_pairing_is_one_time_and_wrong_code_does_not_claim(self):
        path = "/v1/station-pairings"
        pairing = self.client.post(
            path,
            json=self.pairing_payload,
            headers=self.signed_headers("POST", path, self.pairing_payload),
        ).json()
        claim_path = f"/v1/station-pairings/{pairing['pairing_id']}/claim"
        wrong = self.client.post(claim_path, json={"pairing_code": "AAAAAAAA"})
        self.assertEqual(wrong.status_code, 403)
        claimed = self.client.post(claim_path, json={"pairing_code": pairing["pairing_code"]})
        self.assertEqual(claimed.status_code, 200)
        reused = self.client.post(claim_path, json={"pairing_code": pairing["pairing_code"]})
        self.assertEqual(reused.status_code, 409)

    def test_expired_pairing_cannot_be_claimed(self):
        path = "/v1/station-pairings"
        pairing = self.client.post(
            path,
            json=self.pairing_payload,
            headers=self.signed_headers("POST", path, self.pairing_payload),
        ).json()
        self.repo.station_pairings[pairing["pairing_id"]]["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        response = self.client.post(
            f"/v1/station-pairings/{pairing['pairing_id']}/claim",
            json={"pairing_code": pairing["pairing_code"]},
        )
        self.assertEqual(response.status_code, 410)

    def test_pairing_claim_attempts_are_rate_limited(self):
        path = "/v1/station-pairings"
        pairing = self.client.post(
            path,
            json=self.pairing_payload,
            headers=self.signed_headers("POST", path, self.pairing_payload),
        ).json()
        claim_path = f"/v1/station-pairings/{pairing['pairing_id']}/claim"
        for _ in range(10):
            self.assertEqual(
                self.client.post(claim_path, json={"pairing_code": "AAAAAAAA"}).status_code,
                403,
            )
        limited = self.client.post(claim_path, json={"pairing_code": pairing["pairing_code"]})
        self.assertEqual(limited.status_code, 429)

    def test_desired_state_generation_heartbeat_replay_and_release(self):
        self.create_and_claim()
        desired_path = f"/v1/stations/{self.station_id}/desired-state"
        changed = self.client.patch(
            desired_path,
            json={"running": True, "target_language": "vi"},
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["generation"], 1)

        request_id = str(uuid.uuid4())
        headers = self.signed_headers("GET", desired_path, {}, request_id)
        desired = self.client.get(desired_path, headers=headers)
        self.assertEqual(desired.status_code, 200)
        self.assertTrue(desired.json()["running"])
        replay = self.client.get(desired_path, headers=headers)
        self.assertEqual(replay.status_code, 409)

        heartbeat_path = f"/v1/stations/{self.station_id}/heartbeat"
        heartbeat = {
            "capture_state": "listening",
            "session_id": "session-1",
            "sequence": 4,
            "app_version": "1.2.0",
            "observed_generation": 1,
            "target_language": "vi",
            "error": None,
            "ptt_mode": "unavailable",
            "ptt_ready": False,
            "ptt_error": "PTT_UNAVAILABLE",
        }
        response = self.client.post(
            heartbeat_path,
            json=heartbeat,
            headers=self.signed_headers("POST", heartbeat_path, heartbeat),
        )
        self.assertEqual(response.status_code, 204, response.text)
        station = self.client.get("/v1/stations").json()[0]
        # Owners quote this to support when they ask for a recording, and it is
        # exactly the bucket folder, so it must not drift from the archive rule.
        self.assertEqual(
            station["storage_folder"],
            station_storage_folder(station["name"], self.station_id),
        )
        self.assertTrue(station["storage_folder"].endswith(self.station_id[:8]))
        self.assertEqual(station["observed_generation"], 1)
        self.assertEqual(station["sequence"], 4)
        self.assertEqual(station["ptt_mode"], "unavailable")
        self.assertFalse(station["ptt_ready"])
        self.assertEqual(station["ptt_error"], "PTT_UNAVAILABLE")

        self.assertEqual(self.client.delete(f"/v1/stations/{self.station_id}").status_code, 204)
        denied = self.client.get(
            desired_path,
            headers=self.signed_headers("GET", desired_path, {}),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["detail"]["code"], "STATION_NOT_PAIRED")

    def test_other_user_cannot_release_station(self):
        self.create_and_claim()
        other = Identity("owner-2", "other@example.com", True)
        self.repo.users[other.uid] = UserAccount(
            uid=other.uid,
            email=other.email,
            email_verified=True,
            status="active",
            plan_id="free",
        )
        app.dependency_overrides[require_identity] = lambda: other
        response = self.client.delete(f"/v1/stations/{self.station_id}")
        self.assertEqual(response.status_code, 404)

    def test_capabilities_gate_remote_audio_settings(self):
        self.create_and_claim()
        desired_path = f"/v1/stations/{self.station_id}/desired-state"
        unavailable = self.client.patch(
            desired_path,
            json={"capture_mode": "loopback", "audio_device_id": "a" * 32},
        )
        self.assertEqual(unavailable.status_code, 409)

        path = f"/v1/stations/{self.station_id}/capabilities"
        payload = {
            "capability_hash": "a" * 64,
            "capture_modes": ["device", "loopback"],
            "audio_devices": [
                {
                    "id": "b" * 32,
                    "name": "USB SoundCard",
                    "mode": "device",
                    "input_channels": 1,
                    "output_channels": 2,
                    "sample_rate": 48000,
                    "host_api": "WASAPI",
                },
                {
                    "id": "c" * 32,
                    "name": "Speakers (loopback)",
                    "mode": "loopback",
                    "input_channels": 2,
                    "output_channels": 0,
                    "sample_rate": 48000,
                    "host_api": "WASAPI",
                },
            ],
            "storage_path": "D:/PRANA",
        }
        response = self.client.post(
            path,
            json=payload,
            headers=self.signed_headers("POST", path, payload),
        )
        self.assertEqual(response.status_code, 204, response.text)

        invalid = self.client.patch(
            desired_path,
            json={"capture_mode": "loopback", "audio_device_id": "b" * 32},
        )
        self.assertEqual(invalid.status_code, 422)
        changed = self.client.patch(
            desired_path,
            json={
                "capture_mode": "loopback",
                "audio_device_id": "c" * 32,
                "refresh_capabilities": True,
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["capture_mode"], "loopback")
        self.assertEqual(changed.json()["capability_refresh_generation"], 1)

        replacement = {
            **payload,
            "capability_hash": "d" * 64,
            "audio_devices": [payload["audio_devices"][0]],
            "capture_modes": ["device"],
        }
        refreshed = self.client.post(
            path,
            json=replacement,
            headers=self.signed_headers("POST", path, replacement),
        )
        self.assertEqual(refreshed.status_code, 204, refreshed.text)
        reconciled = self.client.get(
            desired_path,
            headers=self.signed_headers("GET", desired_path, {}),
        ).json()
        self.assertEqual(reconciled["audio_device_id"], "")
        self.assertEqual(reconciled["capture_mode"], "device")
        self.assertGreater(reconciled["generation"], changed.json()["generation"])

    def test_removed_auto_start_and_legacy_boot_id_have_no_effect(self):
        self.create_and_claim()
        desired_path = f"/v1/stations/{self.station_id}/desired-state"
        registry = self.repo.station_registry[self.station_id]
        projection = self.repo.station_projections[
            self.identity.uid
        ][self.station_id]
        registry["boot_id"] = "stale-boot"
        projection["boot_id"] = "stale-boot"
        registry["desired_state"]["auto_start_capture"] = True
        projection["desired_state"]["auto_start_capture"] = True

        changed = self.client.patch(
            desired_path,
            json={"auto_start_capture": True},
        )
        self.assertEqual(changed.status_code, 422, changed.text)

        heartbeat_path = f"/v1/stations/{self.station_id}/heartbeat"
        heartbeat = {
            "capture_state": "idle",
            "session_id": "",
            "sequence": 0,
            "app_version": "1.2.0",
            "observed_generation": 0,
            "target_language": "vi",
            "boot_id": "boot-1",
            "active_capture_mode": "device",
            "active_audio_device_id": "",
            "error": None,
            "retrying": True,
            "retry_code": "SERVICE_BUSY",
            "retry_attempt": 2,
        }
        first = self.client.post(
            heartbeat_path,
            json=heartbeat,
            headers=self.signed_headers("POST", heartbeat_path, heartbeat),
        )
        self.assertEqual(first.status_code, 204, first.text)
        self.assertTrue(projection["retrying"])
        self.assertEqual(projection["retry_code"], "SERVICE_BUSY")
        self.assertEqual(projection["retry_attempt"], 2)
        self.assertNotIn("boot_id", projection)

        cleanup = self.client.patch(
            desired_path,
            json={"target_language": "vi"},
        )
        self.assertEqual(cleanup.status_code, 200, cleanup.text)
        self.assertNotIn("boot_id", registry)
        self.assertNotIn("boot_id", projection)
        self.assertNotIn("auto_start_capture", registry["desired_state"])
        self.assertNotIn("auto_start_capture", projection["desired_state"])

        desired = self.client.get(
            desired_path,
            headers=self.signed_headers("GET", desired_path, {}),
        ).json()
        self.assertFalse(desired["running"])
        self.assertEqual(desired["generation"], 1)
        self.assertNotIn("auto_start_capture", desired)

    def test_result_listing_returns_the_newest_results(self):
        self.create_and_claim()
        now = datetime.now(timezone.utc)
        for sequence, timestamp in enumerate(
            [
                now - timedelta(days=2),
                now - timedelta(hours=3),
                now - timedelta(hours=2),
                now - timedelta(hours=1),
            ],
            start=1,
        ):
            response = ProcessingResponse(
                request_id=f"request-{sequence}",
                station_id=self.station_id,
                session_id="session-1",
                sequence=sequence,
                audio_file=f"{sequence}.wav",
                timestamp=timestamp,
            ).model_dump(mode="json")
            self.repo.publish_station_result(
                self.identity.uid,
                self.station_id,
                response,
            )
        response = self.client.get(
            f"/v1/stations/{self.station_id}/sessions/session-1/results"
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            [item["sequence"] for item in response.json()],
            [1, 2, 3, 4],
        )

    def test_live_results_merge_today_across_sessions_and_honour_limit(self):
        self.create_and_claim()
        local_timezone = timezone(timedelta(hours=7))
        local_now = datetime.now(timezone.utc).astimezone(local_timezone)
        timestamps = [
            local_now - timedelta(days=1),
            local_now.replace(hour=8, minute=0, second=0, microsecond=0),
            local_now.replace(hour=9, minute=0, second=0, microsecond=0),
            local_now.replace(hour=10, minute=0, second=0, microsecond=0),
        ]
        for sequence, timestamp in enumerate(timestamps, start=1):
            self.repo.publish_station_result(
                self.identity.uid,
                self.station_id,
                ProcessingResponse(
                    request_id=f"live-request-{sequence}",
                    station_id=self.station_id,
                    session_id=f"session-{sequence}",
                    sequence=sequence,
                    audio_file=f"{sequence}.wav",
                    timestamp=timestamp.astimezone(timezone.utc),
                ).model_dump(mode="json"),
            )
        response = self.client.get(
            f"/v1/stations/{self.station_id}/live/results",
            params={"timezone_offset_minutes": 420, "limit": 2},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            [item["request_id"] for item in response.json()],
            ["live-request-3", "live-request-4"],
        )
        self.assertEqual(
            [item["session_id"] for item in response.json()],
            ["session-3", "session-4"],
        )

    def test_history_groups_sessions_by_local_day_and_locks_past_days(self):
        self.create_and_claim()
        local_timezone = timezone(timedelta(hours=7))
        local_today = datetime.now(timezone.utc).astimezone(local_timezone).date()
        previous_day = local_today - timedelta(days=1)
        timestamps = [
            datetime.combine(
                previous_day,
                datetime.min.time(),
                local_timezone,
            ).replace(hour=23, minute=59),
            datetime.combine(
                local_today,
                datetime.min.time(),
                local_timezone,
            ).replace(minute=1),
        ]
        for sequence, timestamp in enumerate(timestamps, start=1):
            self.repo.publish_station_result(
                self.identity.uid,
                self.station_id,
                ProcessingResponse(
                    request_id=f"day-request-{sequence}",
                    station_id=self.station_id,
                    session_id=f"session-{sequence}",
                    sequence=sequence,
                    audio_file=f"{sequence}.wav",
                    timestamp=timestamp.astimezone(timezone.utc),
                ).model_dump(mode="json"),
            )

        response = self.client.get(
            f"/v1/stations/{self.station_id}/history/days",
            params={"timezone_offset_minutes": 420},
        )

        self.assertEqual(response.status_code, 200, response.text)
        days = response.json()
        self.assertEqual(
            [item["date"] for item in days],
            [local_today.isoformat(), previous_day.isoformat()],
        )
        # Free keeps history_past_days at 0: today reads, anything older locks.
        self.assertFalse(days[0]["locked"])
        self.assertTrue(days[1]["locked"])
        locked = self.client.get(
            f"/v1/stations/{self.station_id}/history/days/"
            f"{previous_day.isoformat()}/results",
            params={"timezone_offset_minutes": 420},
        )
        self.assertEqual(locked.status_code, 403, locked.text)
        self.assertEqual(locked.json()["detail"]["code"], "HISTORY_LOCKED")
        unlocked = self.client.get(
            f"/v1/stations/{self.station_id}/history/days/"
            f"{local_today.isoformat()}/results",
            params={"timezone_offset_minutes": 420},
        )
        self.assertEqual(unlocked.status_code, 200, unlocked.text)
        self.assertEqual(
            [item["request_id"] for item in unlocked.json()["items"]],
            ["day-request-2"],
        )

    def test_history_paginates_all_sessions_for_today(self):
        self.create_and_claim()
        now = datetime.now(timezone.utc)
        for sequence in range(1001):
            self.repo.publish_station_result(
                self.identity.uid,
                self.station_id,
                ProcessingResponse(
                    request_id=f"page-request-{sequence:04d}",
                    station_id=self.station_id,
                    session_id=f"session-{sequence % 3}",
                    sequence=sequence,
                    audio_file=f"{sequence}.wav",
                    timestamp=now + timedelta(microseconds=sequence),
                ).model_dump(mode="json"),
            )
        history_date = now.date().isoformat()
        first = self.client.get(
            f"/v1/stations/{self.station_id}/history/days/{history_date}/results",
            params={"limit": 1000},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(len(first.json()["items"]), 1000)
        self.assertEqual(first.json()["next_cursor"], "1000")
        second = self.client.get(
            f"/v1/stations/{self.station_id}/history/days/{history_date}/results",
            params={"limit": 1000, "cursor": first.json()["next_cursor"]},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(len(second.json()["items"]), 1)
        self.assertIsNone(second.json()["next_cursor"])

    def test_station_audio_uses_owner_quota_and_publishes_projection(self):
        self.create_and_claim()
        Processor.calls = 0
        audio = wav_bytes()
        digest = hashlib.sha256(audio).hexdigest()
        timestamp = str(int(time.time()))
        request_id = str(uuid.uuid4())
        signature = base64.b64encode(self.private.sign(canonical_request(
            request_id, timestamp, digest, "vi", "session-1", 1,
        ))).decode("ascii")
        archive = Archive()
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_archive", return_value=archive
        ):
            response = self.client.post(
                f"/v1/stations/{self.station_id}/audio/process",
                headers={
                    "X-Station-ID": self.station_id,
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                },
                data={
                    "target_language": "vi",
                    "session_id": "session-1",
                    "sequence": "1",
                    "request_id": request_id,
                },
                files={
                    "audio": (
                        "20260803_110002_0001.wav",
                        audio,
                        "audio/wav",
                    )
                },
            )
            repeated = self.client.post(
                f"/v1/stations/{self.station_id}/audio/process",
                headers={
                    "X-Station-ID": self.station_id,
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                },
                data={
                    "target_language": "vi",
                    "session_id": "session-1",
                    "sequence": "1",
                    "request_id": request_id,
                },
                files={
                    "audio": (
                        "20260803_110002_0001.wav",
                        audio,
                        "audio/wav",
                    )
                },
            )
            source = self.client.get(
                f"/v1/stations/{self.station_id}/sessions/session-1/"
                f"results/{request_id}/audio"
            )
            missing = self.client.get(
                f"/v1/stations/{self.station_id}/sessions/session-1/"
                f"results/{uuid.uuid4()}/audio"
            )
            app.dependency_overrides[require_identity] = lambda: Identity(
                "other-owner",
                "other@example.com",
                True,
            )
            forbidden = self.client.get(
                f"/v1/stations/{self.station_id}/sessions/session-1/"
                f"results/{request_id}/audio"
            )
            app.dependency_overrides[require_identity] = lambda: self.identity
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(source.status_code, 200, source.text)
        self.assertEqual(source.content, audio)
        self.assertEqual(source.headers["content-type"], "audio/wav")
        self.assertEqual(source.headers["cache-control"], "private, max-age=3600")
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(missing.json()["detail"]["code"], "SOURCE_AUDIO_UNAVAILABLE")
        self.assertEqual(forbidden.status_code, 404, forbidden.text)
        self.assertEqual(Processor.calls, 1)
        self.assertEqual(response.json()["station_id"], self.station_id)
        self.assertEqual(response.json()["target_language"], "vi")
        self.assertEqual(
            response.json()["audio_file"],
            "20260803_110002_0001.wav",
        )
        self.assertNotIn("_source_audio_object", response.json())
        key = (self.identity.uid, self.station_id, "session-1", request_id)
        self.assertIn(key, self.repo.station_results)
        self.assertEqual(self.repo.station_results[key]["target_language"], "vi")
        self.assertEqual(
            self.repo.station_results[key]["audio_file"],
            "20260803_110002_0001.wav",
        )
        self.assertIn("_source_audio_object", self.repo.station_results[key])
        self.assertEqual(len(archive.station_calls), 1)
        self.assertEqual(archive.station_calls[0]["station_name"], "Bridge Pi")
        self.assertEqual(archive.station_calls[0]["date_path"], "2026/08/03")
        usage = self.repo.get_usage(self.identity.uid, self.repo.plans["free"])
        self.assertEqual(usage.used_audio_seconds, 1)

    def test_signed_station_profile_exposes_plan_concurrency(self):
        self.create_and_claim()
        path = f"/v1/stations/{self.station_id}/profile"

        response = self.client.get(
            path,
            headers=self.signed_headers("GET", path, {}),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "active")
        self.assertEqual(
            response.json()["entitlements"]["max_concurrency"],
            2,
        )

    def test_tx_draft_confirm_claim_download_and_complete(self):
        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        archive = Archive()
        request_id = str(uuid.uuid4())
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_tx_synthesizer", return_value=Synthesizer()
        ), patch("services.prana_api.main.get_archive", return_value=archive):
            draft = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                headers={"X-Request-ID": request_id},
            )
            self.assertEqual(draft.status_code, 200, draft.text)
            self.assertEqual(draft.json()["status"], "review_ready")

            confirmed = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts/{request_id}/confirm",
                json={"translation": "Chuyển sang kênh 18."},
            )
            self.assertEqual(confirmed.status_code, 200, confirmed.text)
            self.assertEqual(confirmed.json()["translation"], "Chuyển sang kênh 18.")
            self.assertTrue(confirmed.json()["translation_edited"])
            self.assertRegex(
                confirmed.json()["audio_filename"],
                r"^\d{8}_\d{6}_\d{4}\.wav$",
            )
            self.assertEqual(Synthesizer.texts[-1], "Chuyển sang kênh 18.")
            synthesis_count = len(Synthesizer.texts)
            duplicate = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts/{request_id}/confirm",
                json={"translation": "Chuyển sang kênh 18."},
            )
            self.assertEqual(duplicate.status_code, 200, duplicate.text)
            self.assertEqual(len(Synthesizer.texts), synthesis_count)

            claim_path = f"/v1/stations/{self.station_id}/tx/jobs/claim"
            claimed = self.client.post(
                claim_path,
                headers=self.signed_headers("POST", claim_path, {}),
            )
            self.assertEqual(claimed.status_code, 200, claimed.text)
            self.assertEqual(claimed.json()["id"], request_id)

            audio_path = f"/v1/stations/{self.station_id}/tx/jobs/{request_id}/audio"
            output = self.client.get(
                audio_path,
                params={"kind": "output"},
                headers=self.signed_headers("GET", audio_path, {}),
            )
            self.assertEqual(output.status_code, 200, output.text)
            self.assertEqual(output.headers["content-type"], "audio/wav")

            status_path = f"/v1/stations/{self.station_id}/tx/jobs/{request_id}/status"
            transmitting = {"status": "transmitting"}
            response = self.client.post(
                status_path,
                json=transmitting,
                headers=self.signed_headers("POST", status_path, transmitting),
            )
            self.assertEqual(response.status_code, 200, response.text)
            completed = {"status": "completed"}
            response = self.client.post(
                status_path,
                json=completed,
                headers=self.signed_headers("POST", status_path, completed),
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "completed")

            days = self.client.get(
                f"/v1/stations/{self.station_id}/tx/history/days",
                params={"timezone_offset_minutes": 420},
            )
            self.assertEqual(days.status_code, 200, days.text)
            self.assertEqual(days.json()[0]["result_count"], 1)
            history_date = days.json()[0]["date"]
            # Regression: TX jobs carry "created_at", not "timestamp", so the
            # grouping key used to fall back to datetime.min and bucket every
            # job under 0001-01-01.
            self.assertEqual(
                history_date,
                datetime.now(timezone(timedelta(minutes=420))).date().isoformat(),
            )
            jobs = self.client.get(
                f"/v1/stations/{self.station_id}/tx/history/days/{history_date}/jobs",
                params={"timezone_offset_minutes": 420},
            )
            self.assertEqual(jobs.status_code, 200, jobs.text)
            self.assertEqual(jobs.json()["items"][0]["id"], request_id)
            history_audio = self.client.get(
                f"/v1/stations/{self.station_id}/tx/history/{request_id}/audio"
            )
            self.assertEqual(history_audio.status_code, 200, history_audio.text)
            self.assertEqual(history_audio.headers["content-type"], "audio/wav")

    def test_tx_archive_date_path_matches_filename_for_source_and_output(self):
        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        archive = Archive()
        request_id = str(uuid.uuid4())
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_tx_synthesizer", return_value=Synthesizer()
        ), patch("services.prana_api.main.get_archive", return_value=archive):
            draft = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                headers={"X-Request-ID": request_id},
            )
            self.assertEqual(draft.status_code, 200, draft.text)
            confirmed = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts/{request_id}/confirm",
                json={"translation": "Chuyển sang kênh 18."},
            )
            self.assertEqual(confirmed.status_code, 200, confirmed.text)

        source = archive.tx_source_calls[-1]
        output = archive.tx_output_calls[-1]
        # Regression: output used to fall back to datetime.min and archive under
        # "1/01/01" because the TX job dict has no "timestamp" key.
        self.assertRegex(output["date_path"], r"^\d{4}/\d{2}/\d{2}$")
        self.assertEqual(
            output["date_path"][:4],
            f"{datetime.now(timezone.utc).year:04d}",
        )
        # Source, output and result of one job must share one folder.
        self.assertEqual(output["date_path"], source["date_path"])
        # And that folder must be the one encoded in the logical filename.
        self.assertEqual(
            output["date_path"].replace("/", ""),
            output["audio_filename"][:8],
        )

    def test_tx_filename_date_follows_the_owner_timezone(self):
        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        # Auckland (UTC+12/+13) and Honolulu (UTC-10) are ~23 hours apart, so
        # their local dates never coincide -- one of them always differs from
        # UTC, which is what makes this assertion meaningful at any wall clock.
        seen = {}
        for country, zone in (("NZ", "Pacific/Auckland"), ("US", "Pacific/Honolulu")):
            patched = self.client.patch(
                "/v1/me", json={"country_code": country, "timezone": zone}
            )
            self.assertEqual(patched.status_code, 200, patched.text)
            request_id = str(uuid.uuid4())
            with patch(
                "services.prana_api.main.get_processor", return_value=Processor()
            ), patch("services.prana_api.main.get_archive", return_value=Archive()):
                draft = self.client.post(
                    f"/v1/stations/{self.station_id}/tx/drafts",
                    data={"target_language": "vi"},
                    files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                    headers={"X-Request-ID": request_id},
                )
            self.assertEqual(draft.status_code, 200, draft.text)
            seen[zone] = draft.json()["audio_filename"][:8]
            self.assertEqual(
                seen[zone],
                datetime.now(ZoneInfo(zone)).strftime("%Y%m%d"),
            )
        self.assertNotEqual(seen["Pacific/Auckland"], seen["Pacific/Honolulu"])

    def test_tx_create_and_confirm_require_station_start(self):
        self.create_and_claim()
        archive = Archive()
        request_id = str(uuid.uuid4())
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_archive", return_value=archive
        ):
            blocked = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                headers={"X-Request-ID": request_id},
            )
            self.assertEqual(blocked.status_code, 409, blocked.text)
            self.assertEqual(blocked.json()["detail"]["code"], "TX_NOT_STARTED")

            self.repo.update_station_desired_state(
                self.identity.uid, self.station_id, {"running": True}
            )
            self.heartbeat()
            draft = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                headers={"X-Request-ID": request_id},
            )
            self.assertEqual(draft.status_code, 200, draft.text)
            self.repo.update_station_desired_state(
                self.identity.uid, self.station_id, {"running": False}
            )
            confirm = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts/{request_id}/confirm",
                json={"translation": draft.json()["translation"]},
            )
            self.assertEqual(confirm.status_code, 409, confirm.text)
            self.assertEqual(confirm.json()["detail"]["code"], "TX_NOT_STARTED")

    def test_tx_draft_enforces_current_plan_recording_limit(self):
        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        self.repo.plans["free"] = self.repo.plans["free"].model_copy(
            update={"tx_max_recording_seconds": 5}
        )
        archive = Archive()
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_archive", return_value=archive
        ):
            accepted = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(5), "audio/wav")},
                headers={"X-Request-ID": str(uuid.uuid4())},
            )
            rejected_id = str(uuid.uuid4())
            rejected = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(5.1), "audio/wav")},
                headers={"X-Request-ID": rejected_id},
            )

        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(rejected.status_code, 413, rejected.text)
        self.assertEqual(rejected.json()["detail"]["code"], "TX_AUDIO_TOO_LONG")
        self.assertEqual(rejected.json()["detail"]["max_seconds"], 5)
        self.assertIsNone(self.tx_repo.get(rejected_id))
        self.assertEqual(len(archive.audio), 1)

    def test_tx_output_over_120_seconds_is_not_archived_or_queued(self):
        class LongSynthesizer:
            def synthesize_with_over(self, _text, _target_language):
                return wav_bytes(120.01)

        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        archive = Archive()
        request_id = str(uuid.uuid4())
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_tx_synthesizer",
            return_value=LongSynthesizer(),
        ), patch("services.prana_api.main.get_archive", return_value=archive):
            draft = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts",
                data={"target_language": "vi"},
                files={"audio": ("phone.wav", wav_bytes(), "audio/wav")},
                headers={"X-Request-ID": request_id},
            )
            confirmed = self.client.post(
                f"/v1/stations/{self.station_id}/tx/drafts/{request_id}/confirm",
                json={"translation": draft.json()["translation"]},
            )

        self.assertEqual(confirmed.status_code, 422, confirmed.text)
        self.assertEqual(confirmed.json()["detail"]["code"], "TX_OUTPUT_TOO_LONG")
        self.assertEqual(self.tx_repo.get(request_id)["status"], "failed")
        self.assertFalse(self.tx_repo.get(request_id)["output_available"])
        self.assertFalse(any("/output/" in key for key in archive.audio))

    def test_tx_create_idempotency_reuses_result_and_rejects_changed_audio(self):
        self.create_and_claim()
        self.repo.update_station_desired_state(
            self.identity.uid, self.station_id, {"running": True}
        )
        self.heartbeat()
        archive = Archive()
        request_id = str(uuid.uuid4())
        Processor.calls = 0
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_archive", return_value=archive
        ):
            def create(audio_bytes):
                return self.client.post(
                    f"/v1/stations/{self.station_id}/tx/drafts",
                    data={"target_language": "vi"},
                    files={"audio": ("phone.wav", audio_bytes, "audio/wav")},
                    headers={"X-Request-ID": request_id},
                )

            first = create(wav_bytes())
            repeated = create(wav_bytes())
            conflict = create(wav_bytes(1.1))

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(first.json()["id"], repeated.json()["id"])
        self.assertEqual(first.json()["audio_filename"], repeated.json()["audio_filename"])
        self.assertEqual(Processor.calls, 1)
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["detail"]["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(len(archive.audio), 1)


if __name__ == "__main__":
    unittest.main()
