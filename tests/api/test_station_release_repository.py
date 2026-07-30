from __future__ import annotations

import hashlib
import unittest

from fastapi import HTTPException

from services.prana_api.memory_repository import MemoryRepository


class StationReleaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MemoryRepository()
        self.station_id = "station-release-test"
        self.setup_id = "SETUPTEST1"
        self.activation_code = "ABCDEFGH23456789"
        self.repo.station_activation_index[self.setup_id] = self.station_id
        self.repo.station_registry[self.station_id] = {
            "station_id": self.station_id,
            "name": "Bridge Pi",
            "platform": "Linux aarch64",
            "active": True,
            "owner_uid": "owner-a",
            "activation_hash": hashlib.sha256(
                f"{self.station_id}:{self.activation_code}".encode()
            ).hexdigest(),
            "desired_state": {"running": True, "generation": 7},
            "online": True,
            "capture_state": "running",
            "capabilities": {"capture_modes": ["device"]},
        }
        self.repo.station_projections["owner-a"] = {
            self.station_id: {
                "name": "Bridge Pi",
                "platform": "Linux aarch64",
                "active": True,
                "desired_state": {"running": True, "generation": 7},
            }
        }

    def test_release_hides_old_projection_and_allows_static_qr_reclaim(self) -> None:
        self.repo.release_station("owner-a", self.station_id)

        registry = self.repo.station_registry[self.station_id]
        self.assertIsNone(registry["owner_uid"])
        self.assertTrue(registry["active"])
        self.assertFalse(registry["desired_state"]["running"])
        self.assertEqual(registry["desired_state"]["generation"], 8)
        self.assertNotIn("capabilities", registry)
        self.assertEqual(self.repo.list_stations("owner-a"), [])

        station = self.repo.claim_station_activation(
            "owner-b", self.setup_id, self.activation_code, max_stations=2
        )

        self.assertEqual(station.station_id, self.station_id)
        self.assertEqual(registry["owner_uid"], "owner-b")
        self.assertFalse(
            self.repo.station_projections["owner-a"][self.station_id]["active"]
        )
        self.assertTrue(
            self.repo.station_projections["owner-b"][self.station_id]["active"]
        )

    def test_inactive_projection_does_not_bypass_station_quota(self) -> None:
        self.repo.release_station("owner-a", self.station_id)
        self.repo.station_projections["owner-b"] = {
            self.station_id: {"active": False},
            "another-station": {"active": True},
        }

        with self.assertRaises(HTTPException) as raised:
            self.repo.claim_station_activation(
                "owner-b", self.setup_id, self.activation_code, max_stations=1
            )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(
            raised.exception.detail["code"],
            "STATION_LIMIT_REACHED",
        )


if __name__ == "__main__":
    unittest.main()
