from __future__ import annotations

import base64
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from services.prana_api.auth import Identity, require_identity
from services.prana_api.main import app, get_repository
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Plan, UserAccount
from services.prana_api.security import (
    canonical_station_request,
    station_payload_hash,
)


class UserRegionTests(unittest.TestCase):
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

    def tearDown(self):
        app.dependency_overrides.clear()

    def claim_station(self) -> str:
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        station_id = uuid.uuid4().hex
        payload = {
            "station_id": station_id,
            "name": "Bridge Pi",
            "platform": "Linux aarch64",
            "public_key": base64.b64encode(public).decode("ascii"),
        }
        path = "/v1/station-pairings"
        request_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        signature = private.sign(
            canonical_station_request(
                "POST", path, request_id, timestamp, station_payload_hash(payload)
            )
        )
        pairing = self.client.post(
            path,
            json=payload,
            headers={
                "X-Station-ID": station_id,
                "X-Request-ID": request_id,
                "X-Timestamp": timestamp,
                "X-Signature": base64.b64encode(signature).decode("ascii"),
            },
        )
        self.assertEqual(pairing.status_code, 200, pairing.text)
        value = pairing.json()
        claim = self.client.post(
            f"/v1/station-pairings/{value['pairing_id']}/claim",
            json={"pairing_code": value["pairing_code"]},
        )
        self.assertEqual(claim.status_code, 200, claim.text)
        return station_id

    def test_me_defaults_to_empty_region_when_account_predates_the_field(self):
        response = self.client.get("/v1/me")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["country_code"], "")
        self.assertEqual(response.json()["timezone"], "")

    def test_country_catalog_is_served_and_cacheable(self):
        response = self.client.get("/v1/countries")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("max-age", response.headers["cache-control"])
        codes = {entry["code"] for entry in response.json()}
        self.assertIn("VN", codes)
        vietnam = next(e for e in response.json() if e["code"] == "VN")
        self.assertEqual(vietnam["timezones"], ["Asia/Ho_Chi_Minh"])

    def test_country_alone_resolves_to_the_primary_timezone(self):
        response = self.client.patch("/v1/me", json={"country_code": "vn"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["country_code"], "VN")
        self.assertEqual(response.json()["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(self.client.get("/v1/me").json()["timezone"], "Asia/Ho_Chi_Minh")

    def test_multi_zone_country_accepts_an_explicit_zone(self):
        response = self.client.patch(
            "/v1/me",
            json={"country_code": "US", "timezone": "America/Los_Angeles"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["timezone"], "America/Los_Angeles")

    def test_unknown_country_is_rejected(self):
        response = self.client.patch("/v1/me", json={"country_code": "ZZ"})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_COUNTRY")

    def test_timezone_from_another_country_is_rejected(self):
        response = self.client.patch(
            "/v1/me",
            json={"country_code": "VN", "timezone": "America/Adak"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_TIMEZONE")

    def test_selecting_a_country_fans_the_timezone_out_to_owned_stations(self):
        station_id = self.claim_station()
        before = self.client.get("/v1/stations").json()[0]["desired_state"]
        self.assertEqual(before["timezone"], "")

        response = self.client.patch("/v1/me", json={"country_code": "VN"})
        self.assertEqual(response.status_code, 200, response.text)

        after = self.client.get("/v1/stations").json()[0]["desired_state"]
        self.assertEqual(after["timezone"], "Asia/Ho_Chi_Minh")
        # Station acknowledges the change through the generation counter.
        self.assertGreater(after["generation"], before["generation"])

    def test_station_claimed_after_the_choice_is_seeded_with_the_timezone(self):
        self.client.patch("/v1/me", json={"country_code": "JP"})
        station_id = self.claim_station()
        desired = self.repo.station_registry[station_id]["desired_state"]
        self.assertEqual(desired["timezone"], "Asia/Tokyo")


if __name__ == "__main__":
    unittest.main()
