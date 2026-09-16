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
from services.prana_api.main import app, get_repository, get_tx_repository
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Plan, UserAccount
from services.prana_api.security import canonical_station_request, station_payload_hash
from services.prana_api.tx_repository import MemoryTxRepository
from tests.api.test_station_api import wav_bytes


class OperatorTestBase(unittest.TestCase):
    """Two accounts: a Station owner, and an operator who owns nothing."""

    def setUp(self):
        self.repo = MemoryRepository()
        for plan_id, past_days in (("free", 0), ("pro", 30)):
            self.repo.plans[plan_id] = Plan(
                id=plan_id,
                name=plan_id.title(),
                audio_seconds_limit=600,
                requests_per_minute=30,
                max_devices=2,
                max_stations=2,
                history_past_days=past_days,
            )

        self.owner = Identity("owner-1", "owner@example.com", True)
        self.operator = Identity("op-1", "ops@example.com", True)
        self._account(self.owner, plan_id="free")
        self._account(self.operator, plan_id="free", fleet_operator=True)

        self.identity = self.owner
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
        self.claim_station()

    def tearDown(self):
        app.dependency_overrides.clear()

    def _account(self, identity: Identity, plan_id: str, fleet_operator: bool = False):
        self.repo.users[identity.uid] = UserAccount(
            uid=identity.uid,
            email=identity.email,
            email_verified=True,
            status="active",
            plan_id=plan_id,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            fleet_operator=fleet_operator,
        )

    def signed_headers(self, method: str, path: str, payload: dict):
        request_id = str(uuid.uuid4())
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

    def claim_station(self):
        # The pairing endpoint allows one code per station per minute; these
        # tests re-pair the same station id deliberately.
        registry = self.repo.station_registry.get(self.station_id)
        if registry:
            registry.pop("last_pairing_created_at", None)
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

    def as_operator(self):
        self.identity = self.operator

    def as_owner(self):
        self.identity = self.owner

    def acquire(self, force: bool = False):
        response = self.client.post(
            f"/v1/operator/stations/{self.station_id}/control",
            json={"force": force, "label": "Ops desk"},
        )
        return response


class OperatorAccessTests(OperatorTestBase):
    def test_non_operator_account_is_refused(self):
        response = self.client.get("/v1/operator/stations")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"]["code"], "OPERATOR_REQUIRED")

    def test_operator_lists_and_reads_a_station_it_does_not_own(self):
        self.as_operator()
        listing = self.client.get("/v1/operator/stations")
        self.assertEqual(listing.status_code, 200, listing.text)
        items = listing.json()["items"]
        self.assertEqual([item["station_id"] for item in items], [self.station_id])
        self.assertEqual(items[0]["owner_uid"], self.owner.uid)
        self.assertEqual(items[0]["owner_email"], self.owner.email)

        detail = self.client.get(f"/v1/operator/stations/{self.station_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["name"], "Bridge Pi")

    def test_owner_routes_stay_closed_to_the_operator(self):
        """The operator namespace must not widen the owner-scoped routes."""
        self.as_operator()
        response = self.client.get("/v1/stations")
        self.assertEqual(response.json(), [])
        patched = self.client.patch(
            f"/v1/stations/{self.station_id}/desired-state",
            json={"running": True},
        )
        self.assertEqual(patched.status_code, 404, patched.text)

    def test_unclaimed_station_is_a_conflict_not_a_silent_success(self):
        self.as_owner()
        released = self.client.delete(f"/v1/stations/{self.station_id}")
        self.assertEqual(released.status_code, 204, released.text)
        self.as_operator()
        response = self.client.get(f"/v1/operator/stations/{self.station_id}")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "STATION_UNCLAIMED")

    def test_history_window_follows_the_owner_plan_not_the_operator_plan(self):
        """A Pro operator still cannot read past a Free owner's window."""
        self.repo.users[self.operator.uid] = self.repo.users[
            self.operator.uid
        ].model_copy(update={"plan_id": "pro"})
        self.as_operator()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        response = self.client.get(
            f"/v1/operator/stations/{self.station_id}/history/days/{yesterday}/results"
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"]["code"], "HISTORY_LOCKED")

    def test_reads_are_audited(self):
        self.as_operator()
        response = self.client.get(
            f"/v1/operator/stations/{self.station_id}/live/results"
        )
        self.assertEqual(response.status_code, 200, response.text)
        actions = [event["action"] for event in self.repo.operator_audit]
        self.assertIn("station.live_read", actions)
        self.assertEqual(self.repo.operator_audit[-1]["actor_uid"], self.operator.uid)
        self.assertEqual(self.repo.operator_audit[-1]["owner_uid"], self.owner.uid)

    def test_released_then_reclaimed_station_does_not_leak_the_old_owner(self):
        """The users/{uid}/... prefix filter is what keeps the two owners apart."""
        self.repo.station_results[
            (self.owner.uid, self.station_id, "session-1", "req-1")
        ] = {
            "request_id": "req-1",
            "station_id": self.station_id,
            "session_id": "session-1",
            "sequence": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.as_owner()
        self.assertEqual(
            self.client.delete(f"/v1/stations/{self.station_id}").status_code, 204
        )
        second = Identity("owner-2", "second@example.com", True)
        self._account(second, plan_id="free")
        self.identity = second
        self.claim_station()

        self.as_operator()
        response = self.client.get(
            f"/v1/operator/stations/{self.station_id}/live/results"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])


class ControlLeaseTests(OperatorTestBase):
    def test_acquire_release_round_trip(self):
        self.as_operator()
        response = self.acquire()
        self.assertEqual(response.status_code, 200, response.text)
        lease = response.json()
        self.assertEqual(lease["holder_kind"], "operator")
        self.assertEqual(lease["holder_uid"], self.operator.uid)
        self.assertEqual(lease["epoch"], 1)

        released = self.client.delete(
            f"/v1/operator/stations/{self.station_id}/control",
            headers={"X-Control-Epoch": str(lease["epoch"])},
        )
        self.assertEqual(released.status_code, 204, released.text)
        registry = self.repo.get_station_registry(self.station_id)
        self.assertNotIn("control_lease", registry)

    def test_second_operator_is_refused_then_can_force(self):
        self.as_operator()
        first = self.acquire()
        self.assertEqual(first.status_code, 200, first.text)

        other = Identity("op-2", "ops2@example.com", True)
        self._account(other, plan_id="free", fleet_operator=True)
        self.identity = other

        blocked = self.acquire()
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(blocked.json()["detail"]["code"], "CONTROL_HELD")

        forced = self.acquire(force=True)
        self.assertEqual(forced.status_code, 200, forced.text)
        lease = forced.json()
        self.assertEqual(lease["holder_uid"], other.uid)
        self.assertEqual(lease["preempted_from_uid"], self.operator.uid)
        self.assertEqual(lease["epoch"], 2)

    def test_preempted_holder_cannot_renew_or_command(self):
        """The epoch is a fencing token, not a courtesy."""
        self.as_operator()
        stale = self.acquire().json()

        other = Identity("op-2", "ops2@example.com", True)
        self._account(other, plan_id="free", fleet_operator=True)
        self.identity = other
        self.acquire(force=True)

        self.as_operator()
        renewed = self.client.post(
            f"/v1/operator/stations/{self.station_id}/control/renew",
            headers={"X-Control-Epoch": str(stale["epoch"])},
        )
        self.assertEqual(renewed.status_code, 409, renewed.text)
        self.assertEqual(renewed.json()["detail"]["code"], "CONTROL_LOST")

        commanded = self.client.patch(
            f"/v1/operator/stations/{self.station_id}/desired-state",
            json={"running": True},
            headers={"X-Control-Epoch": str(stale["epoch"])},
        )
        self.assertEqual(commanded.status_code, 409, commanded.text)
        self.assertEqual(commanded.json()["detail"]["code"], "CONTROL_LOST")

    def test_operator_command_without_a_lease_is_refused(self):
        self.as_operator()
        response = self.client.patch(
            f"/v1/operator/stations/{self.station_id}/desired-state",
            json={"running": True},
            headers={"X-Control-Epoch": "1"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "CONTROL_LOST")

    def test_expired_lease_stops_authorising_commands(self):
        self.as_operator()
        lease = self.acquire().json()
        registry = self.repo.get_station_registry(self.station_id)
        registry["control_lease"]["expires_at"] = datetime.now(
            timezone.utc
        ) - timedelta(seconds=1)

        response = self.client.patch(
            f"/v1/operator/stations/{self.station_id}/desired-state",
            json={"running": True},
            headers={"X-Control-Epoch": str(lease["epoch"])},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "CONTROL_LOST")

    def test_operator_command_writes_under_the_owner_projection(self):
        """`uid` is the data owner; `actor.uid` is the operator. They diverge."""
        self.as_operator()
        lease = self.acquire().json()
        response = self.client.patch(
            f"/v1/operator/stations/{self.station_id}/desired-state",
            json={"running": True},
            headers={"X-Control-Epoch": str(lease["epoch"])},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["running"])

        projection = self.repo.station_projections[self.owner.uid][self.station_id]
        self.assertTrue(projection["desired_state"]["running"])
        self.assertNotIn(self.operator.uid, self.repo.station_projections)

        # The owner's phone learns about the seizure through this mirror, which
        # is the only station data Firestore rules let a client read.
        self.assertEqual(projection["control_lease"]["holder_uid"], self.operator.uid)

    def test_owner_keeps_control_while_preemption_is_disabled(self):
        """Default rollout: operators coordinate, owners are never demoted."""
        self.as_operator()
        self.acquire()
        self.as_owner()
        response = self.client.patch(
            f"/v1/stations/{self.station_id}/desired-state",
            json={"running": True},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_no_lease_leaves_owner_control_untouched(self):
        self.as_owner()
        response = self.client.patch(
            f"/v1/stations/{self.station_id}/desired-state",
            json={"running": True},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["running"])


class OperatorTxTests(OperatorTestBase):
    """TX is the one operator action that physically keys somebody's radio."""

    def setUp(self):
        super().setUp()
        self.tx_repo = MemoryTxRepository()
        app.dependency_overrides[get_tx_repository] = lambda: self.tx_repo

    def _upload(self, epoch: int):
        return self.client.post(
            f"/v1/operator/stations/{self.station_id}/tx/drafts",
            files={"audio": ("tx.wav", wav_bytes(), "audio/wav")},
            data={"target_language": "en"},
            headers={
                "X-Request-ID": str(uuid.uuid4()),
                "X-Control-Epoch": str(epoch),
            },
        )

    def test_tx_requires_a_held_lease(self):
        self.as_operator()
        response = self._upload(epoch=1)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "CONTROL_LOST")

    def test_lease_is_checked_before_the_station_preconditions(self):
        """Holding the lease gets you as far as the ordinary TX guards."""
        self.as_operator()
        lease = self.acquire().json()
        response = self._upload(epoch=lease["epoch"])
        self.assertEqual(response.status_code, 409, response.text)
        # The Station has never been started, so the owner-side guard fires.
        self.assertEqual(response.json()["detail"]["code"], "TX_NOT_STARTED")

    def test_transmission_attempts_are_audited_against_the_owner(self):
        self.as_operator()
        lease = self.acquire().json()
        self._upload(epoch=lease["epoch"])
        events = [
            event
            for event in self.repo.operator_audit
            if event["action"] == "tx.draft_created"
        ]
        self.assertEqual(len(events), 1, self.repo.operator_audit)
        self.assertEqual(events[0]["actor_uid"], self.operator.uid)
        self.assertEqual(events[0]["owner_uid"], self.owner.uid)


if __name__ == "__main__":
    unittest.main()
