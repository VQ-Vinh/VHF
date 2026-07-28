from __future__ import annotations

import unittest

from google.cloud import firestore

from services.prana_api.models import StationHeartbeat
from services.prana_api.repository import FirestoreRepository


class _Snapshot:
    exists = True

    def __init__(self, data: dict):
        self._data = data

    def to_dict(self) -> dict:
        return dict(self._data)


class _Document:
    def __init__(self, db: "_Database", path: tuple[str, ...]):
        self.db = db
        self.path = path

    def get(self) -> _Snapshot:
        return _Snapshot(self.db.documents[self.path])

    def collection(self, name: str) -> "_Collection":
        return _Collection(self.db, self.path + (name,))


class _Collection:
    def __init__(self, db: "_Database", path: tuple[str, ...]):
        self.db = db
        self.path = path

    def document(self, document_id: str) -> _Document:
        return _Document(self.db, self.path + (document_id,))


class _Batch:
    def __init__(self):
        self.writes: list[tuple[tuple[str, ...], dict, bool]] = []
        self.committed = False

    def set(self, ref: _Document, value: dict, merge: bool = False) -> None:
        self.writes.append((ref.path, value, merge))

    def commit(self) -> None:
        self.committed = True


class _Database:
    def __init__(self):
        self.documents = {
            ("station_registry", "station-1"): {"owner_uid": "owner-1"},
        }
        self.last_batch: _Batch | None = None

    def collection(self, name: str) -> _Collection:
        return _Collection(self, (name,))

    def batch(self) -> _Batch:
        self.last_batch = _Batch()
        return self.last_batch


class FirestoreRepositoryTests(unittest.TestCase):
    def test_heartbeat_updates_registry_and_owner_projection_atomically(self) -> None:
        db = _Database()
        repository = object.__new__(FirestoreRepository)
        repository.db = db

        repository.heartbeat_station(
            "station-1",
            StationHeartbeat(
                capture_state="listening",
                app_version="1.2.3",
                observed_generation=7,
            ),
        )

        self.assertIsNotNone(db.last_batch)
        assert db.last_batch is not None
        self.assertTrue(db.last_batch.committed)
        self.assertEqual(
            [write[0] for write in db.last_batch.writes],
            [
                ("station_registry", "station-1"),
                ("users", "owner-1", "stations", "station-1"),
            ],
        )
        for _, value, merge in db.last_batch.writes:
            self.assertTrue(merge)
            self.assertTrue(value["online"])
            self.assertEqual(value["capture_state"], "listening")
            self.assertEqual(value["app_version"], "1.2.3")
            self.assertIs(value["last_seen_at"], firestore.SERVER_TIMESTAMP)


if __name__ == "__main__":
    unittest.main()
