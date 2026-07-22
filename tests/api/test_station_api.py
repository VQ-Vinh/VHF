from __future__ import annotations

import base64
import hashlib
import io
import time
import unittest
import uuid
import wave
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from unittest.mock import patch

from services.prana_api.auth import Identity, require_identity
from services.prana_api.main import app, get_repository
from services.prana_api.google_services import ModelResult
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Plan, ProcessingResponse, UserAccount
from services.prana_api.security import canonical_request, canonical_station_request, station_payload_hash


def wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0" * 32000)
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
    def archive(self, *_args):
        pass


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

    def test_static_activation_rejects_wrong_code_other_owner_and_revoked_station(self):
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
        self.assertEqual(self.client.post(path, json=payload).status_code, 403)

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

    def test_desired_state_generation_heartbeat_replay_and_revoke(self):
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
        }
        response = self.client.post(
            heartbeat_path,
            json=heartbeat,
            headers=self.signed_headers("POST", heartbeat_path, heartbeat),
        )
        self.assertEqual(response.status_code, 204, response.text)
        station = self.client.get("/v1/stations").json()[0]
        self.assertEqual(station["observed_generation"], 1)
        self.assertEqual(station["sequence"], 4)

        self.assertEqual(self.client.delete(f"/v1/stations/{self.station_id}").status_code, 204)
        denied = self.client.get(
            desired_path,
            headers=self.signed_headers("GET", desired_path, {}),
        )
        self.assertEqual(denied.status_code, 403)

    def test_other_user_cannot_revoke_station(self):
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
        with patch("services.prana_api.main.get_processor", return_value=Processor()), patch(
            "services.prana_api.main.get_archive", return_value=Archive()
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
                files={"audio": ("segment.wav", audio, "audio/wav")},
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
                files={"audio": ("segment.wav", audio, "audio/wav")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(Processor.calls, 1)
        self.assertEqual(response.json()["station_id"], self.station_id)
        key = (self.identity.uid, self.station_id, "session-1", request_id)
        self.assertIn(key, self.repo.station_results)
        usage = self.repo.get_usage(self.identity.uid, self.repo.plans["free"])
        self.assertEqual(usage.used_audio_seconds, 1)


if __name__ == "__main__":
    unittest.main()
