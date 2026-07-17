from __future__ import annotations

import base64
import hashlib
import io
import time
import unittest
import uuid
import wave
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from services.prana_api.auth import Identity, require_identity
from services.prana_api.google_services import ModelResult
from services.prana_api.main import app, get_archive, get_processor, get_repository
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Device, Plan, ProcessingResponse, UserAccount
from services.prana_api.security import canonical_request


def audio_bytes() -> bytes:
    value = io.BytesIO()
    with wave.open(value, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0" * 32000)
    return value.getvalue()


class FakeProcessor:
    calls = 0

    def __init__(self, _settings):
        pass

    def process(self, _audio, _target, session_id, sequence, _request_id):
        type(self).calls += 1
        return ModelResult(
            response=ProcessingResponse(
                session_id=session_id,
                sequence=sequence,
                audio_file="audio.wav",
                detected_language="en",
                transcript_raw="test",
                transcript_restored="Test.",
                translation="Test.",
                confidence=0.9,
            ),
            metrics={"model": "fake", "input_tokens": 1, "output_tokens": 1},
        )


class FakeArchive:
    def __init__(self, _settings):
        pass

    def archive(self, *_args):
        pass


class SaasApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.plan = Plan(
            id="starter", name="Starter", monthly_audio_seconds=120,
            requests_per_minute=10, max_concurrency=2, max_devices=2,
        )
        self.repo.plans[self.plan.id] = self.plan
        self.repo.users["user-1"] = UserAccount(
            uid="user-1", email="user@example.com", email_verified=True,
            status="active", plan_id="starter",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.identity = Identity(uid="user-1", email="user@example.com", email_verified=True)
        app.dependency_overrides[get_repository] = lambda: self.repo
        app.dependency_overrides[require_identity] = lambda: self.identity
        self.client = TestClient(app, raise_server_exceptions=False)

        self.private = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            self.private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        self.device_id = "device-0000000001"
        self.repo.register_device(
            "user-1",
            Device(id=self.device_id, uid="user-1", name="test", platform="win", public_key=public),
            2,
        )
        FakeProcessor.calls = 0
        get_processor.cache_clear()
        get_archive.cache_clear()

    def tearDown(self):
        app.dependency_overrides.clear()

    def _audio_request(self, request_id: str, target: str = "en"):
        audio = audio_bytes()
        digest = hashlib.sha256(audio).hexdigest()
        timestamp = str(int(time.time()))
        signature = base64.b64encode(
            self.private.sign(canonical_request(request_id, timestamp, digest, target, "session-1", 1))
        ).decode()
        return self.client.post(
            "/v1/audio/process",
            headers={
                "X-Device-ID": self.device_id,
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            },
            data={"target_language": target, "session_id": "session-1", "sequence": "1", "request_id": request_id},
            files={"audio": ("audio.wav", audio, "audio/wav")},
        )

    def test_inactive_and_unverified_accounts_are_blocked(self):
        self.repo.users["user-1"] = self.repo.users["user-1"].model_copy(update={"status": "expired"})
        response = self.client.get("/v1/devices")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "SUBSCRIPTION_INACTIVE")

        self.identity = Identity(uid="new-user", email="new@example.com", email_verified=False)
        response = self.client.get("/v1/devices")
        self.assertEqual(response.json()["detail"]["code"], "EMAIL_NOT_VERIFIED")

    def test_audio_retry_is_cached_and_changed_body_conflicts(self):
        request_id = str(uuid.uuid4())
        with (
            patch("services.prana_api.main.get_processor", return_value=FakeProcessor(None)),
            patch("services.prana_api.main.get_archive", return_value=FakeArchive(None)),
        ):
            first = self._audio_request(request_id)
            second = self._audio_request(request_id)
            conflict = self._audio_request(request_id, "vi")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(FakeProcessor.calls, 1)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(self.repo.get_usage("user-1", self.plan).used_audio_seconds, 1)

    def test_revoked_or_bad_signature_is_blocked(self):
        request_id = str(uuid.uuid4())
        self.repo.revoke_device("user-1", self.device_id)
        response = self._audio_request(request_id)
        self.assertEqual(response.json()["detail"]["code"], "DEVICE_REVOKED")


if __name__ == "__main__":
    unittest.main()
