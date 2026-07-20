from __future__ import annotations

import base64
import io
import time
import unittest
import wave
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from services.prana_api.audio import validate_wav
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Device, Plan, UserAccount
from services.prana_api.security import (
    body_hash,
    canonical_request,
    verify_device_signature,
    verify_timestamp,
)


def wav_bytes(seconds: float = 1, rate: int = 16000, channels: int = 1, width: int = 2) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\0" * int(seconds * rate * channels * width))
    return output.getvalue()


class AudioValidationTests(unittest.TestCase):
    def test_valid_wav_duration_rounds_up(self):
        self.assertEqual(validate_wav(wav_bytes(1.1), 10 * 1024 * 1024, 120).seconds, 2)

    def test_invalid_codec_and_duration_are_rejected(self):
        with self.assertRaises(HTTPException) as invalid:
            validate_wav(wav_bytes(rate=8000), 10 * 1024 * 1024, 120)
        self.assertEqual(invalid.exception.detail["code"], "INVALID_AUDIO")
        with self.assertRaises(HTTPException) as long:
            validate_wav(wav_bytes(121), 10 * 1024 * 1024, 120)
        self.assertEqual(long.exception.detail["code"], "AUDIO_TOO_LARGE")


class DeviceSignatureTests(unittest.TestCase):
    def test_signature_and_replay_window(self):
        private = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        timestamp = str(int(time.time()))
        message = canonical_request("request", timestamp, body_hash(b"audio"), "en", "session", 1)
        signature = base64.b64encode(private.sign(message)).decode()
        verify_device_signature(public, signature, message)
        verify_timestamp(timestamp, 300)
        with self.assertRaises(HTTPException):
            verify_device_signature(public, signature, message + b"changed")
        with self.assertRaises(HTTPException):
            verify_timestamp(str(int(time.time()) - 301), 300)


class QuotaRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository(global_daily_audio_seconds=100)
        self.plan = Plan(
            id="starter", name="Starter", monthly_audio_seconds=60, requests_per_minute=10,
            max_concurrency=2, max_devices=2,
        )
        self.repo.plans[self.plan.id] = self.plan

    def test_device_limit_and_revoke(self):
        for number in (1, 2):
            self.repo.register_device(
                "u", Device(id=f"device-{number:010d}", uid="u", name="Pi", platform="linux", public_key=str(number)), 2
            )
        with self.assertRaises(HTTPException) as error:
            self.repo.register_device(
                "u", Device(id="device-0000000003", uid="u", name="PC", platform="win", public_key="3"), 2
            )
        self.assertEqual(error.exception.detail["code"], "DEVICE_LIMIT_REACHED")
        self.repo.revoke_device("u", "device-0000000001")
        with self.assertRaises(HTTPException) as revoked:
            self.repo.register_device(
                "u", Device(id="device-0000000001", uid="u", name="Pi", platform="linux", public_key="1"), 2
            )
        self.assertEqual(revoked.exception.detail["code"], "DEVICE_REVOKED")
        self.repo.register_device(
            "u", Device(id="device-0000000003", uid="u", name="PC", platform="win", public_key="3"), 2
        )

    def test_idempotency_and_settlement(self):
        self.repo.reserve("u", self.plan, "r1", "hash", 20)
        with self.assertRaises(HTTPException) as conflict:
            self.repo.reserve("u", self.plan, "r1", "other", 20)
        self.assertEqual(conflict.exception.detail["code"], "IDEMPOTENCY_CONFLICT")
        self.repo.settle_success("u", "r1", {"translation": "ok"}, {})
        cached = self.repo.reserve("u", self.plan, "r1", "hash", 20)
        self.assertEqual(cached.state, "completed")
        self.assertEqual(self.repo.get_usage("u", self.plan).used_audio_seconds, 20)

    def test_failure_releases_quota_and_concurrency_is_atomic(self):
        self.repo.reserve("u", self.plan, "r1", "1", 30)
        self.repo.reserve("u", self.plan, "r2", "2", 30)
        with self.assertRaises(HTTPException) as limited:
            self.repo.reserve("u", self.plan, "r3", "3", 1)
        self.assertEqual(limited.exception.detail["code"], "RATE_LIMITED")
        self.repo.settle_failure("u", "r1", "PROVIDER_ERROR", {})
        self.repo.reserve("u", self.plan, "r3", "3", 30)
        self.assertEqual(self.repo.get_usage("u", self.plan).reserved_audio_seconds, 60)

    def test_monthly_and_global_circuit_breakers(self):
        self.repo.reserve("u", self.plan, "r1", "1", 50)
        self.repo.settle_success("u", "r1", {"ok": True}, {})
        with self.assertRaises(HTTPException) as monthly:
            self.repo.reserve("u", self.plan, "r2", "2", 11)
        self.assertEqual(monthly.exception.detail["code"], "MONTHLY_QUOTA_EXCEEDED")

        global_repo = MemoryRepository(global_daily_audio_seconds=5)
        with self.assertRaises(HTTPException) as global_limit:
            global_repo.reserve("u", self.plan, "r", "hash", 6)
        self.assertEqual(global_limit.exception.detail["code"], "SERVICE_USAGE_LIMIT_REACHED")

    def test_account_expiry(self):
        active = UserAccount(
            uid="u", email="u@example.com", email_verified=True, status="active", plan_id="starter",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        self.assertTrue(active.subscription_active)
        self.assertFalse(active.model_copy(update={"subscription_expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}).subscription_active)


if __name__ == "__main__":
    unittest.main()
