from __future__ import annotations

import threading
from datetime import datetime, timezone

from google.cloud import firestore

from services.prana_api.errors import api_error


ACTIVE_TX_STATES = {"queued", "claimed", "transmitting"}


class MemoryTxRepository:
    def __init__(self):
        self.lock = threading.RLock()
        self.items: dict[str, dict] = {}

    def create(self, value: dict) -> dict:
        with self.lock:
            self.items[value["id"]] = dict(value)
            return dict(value)

    def get(self, job_id: str) -> dict | None:
        value = self.items.get(job_id)
        return dict(value) if value else None

    def confirm(self, uid: str, station_id: str, job_id: str) -> dict:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item["status"] != "review_ready":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is not ready")
            if any(
                other["station_id"] == station_id
                and other["status"] in ACTIVE_TX_STATES
                for other in self.items.values()
            ):
                raise api_error(409, "TX_BUSY", "Station already has an active TX job")
            item["status"] = "queued"
            return dict(item)

    def cancel(self, uid: str, station_id: str, job_id: str) -> None:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item["status"] in {"claimed", "transmitting", "completed"}:
                raise api_error(409, "TX_INVALID_STATE", "TX job cannot be cancelled")
            item["status"] = "cancelled"

    def retry(self, uid: str, station_id: str, job_id: str, new_id: str) -> dict:
        with self.lock:
            failed = self._owned(uid, station_id, job_id)
            if failed["status"] != "failed":
                raise api_error(409, "TX_INVALID_STATE", "Only failed jobs can be retried")
            if any(
                other["station_id"] == station_id and other["status"] in ACTIVE_TX_STATES
                for other in self.items.values()
            ):
                raise api_error(409, "TX_BUSY", "Station already has an active TX job")
            clone = dict(failed, id=new_id, status="queued", attempt=failed.get("attempt", 1) + 1,
                         retry_of=job_id, created_at=datetime.now(timezone.utc))
            self.items[new_id] = clone
            return dict(clone)

    def claim(self, station_id: str) -> dict | None:
        with self.lock:
            queued = sorted(
                (item for item in self.items.values() if item["station_id"] == station_id and item["status"] == "queued"),
                key=lambda item: item["created_at"],
            )
            if not queued:
                return None
            item = queued[0]
            item["status"] = "claimed"
            item["claimed_at"] = datetime.now(timezone.utc)
            return dict(item)

    def station_update(self, station_id: str, job_id: str, status: str, error: str | None = None) -> dict:
        with self.lock:
            item = self.items.get(job_id)
            if not item or item["station_id"] != station_id:
                raise api_error(404, "TX_NOT_FOUND", "TX job was not found")
            allowed = {"claimed": {"transmitting", "failed"}, "transmitting": {"completed", "failed"}}
            if status not in allowed.get(item["status"], set()):
                raise api_error(409, "TX_INVALID_STATE", "Invalid TX transition")
            item["status"] = status
            item["error"] = error
            return dict(item)

    def _owned(self, uid: str, station_id: str, job_id: str) -> dict:
        item = self.items.get(job_id)
        if not item or item["uid"] != uid or item["station_id"] != station_id:
            raise api_error(404, "TX_NOT_FOUND", "TX draft was not found")
        return item


class FirestoreTxRepository:
    """Firestore-backed TX queue. Transactions guarantee one claim and one active job."""

    def __init__(self, project: str = ""):
        self.db = firestore.Client(project=project or None)
        self.collection = self.db.collection("station_tx_jobs")

    def create(self, value: dict) -> dict:
        self.collection.document(value["id"]).set(value)
        return value

    def get(self, job_id: str) -> dict | None:
        snap = self.collection.document(job_id).get()
        return ({"id": snap.id, **snap.to_dict()} if snap.exists else None)

    def confirm(self, uid: str, station_id: str, job_id: str) -> dict:
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            snap, active = ref.get(transaction=tx), active_ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            self._owned(item, uid, station_id)
            if item["status"] != "review_ready":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is not ready")
            active_data = active.to_dict() or {}
            if active_data.get("job_id"):
                raise api_error(409, "TX_BUSY", "Station already has an active TX job")
            tx.update(ref, {"status": "queued", "updated_at": firestore.SERVER_TIMESTAMP})
            tx.set(active_ref, {"job_id": job_id, "status": "queued"})
            return dict(item, status="queued")
        return apply(transaction)

    def cancel(self, uid: str, station_id: str, job_id: str) -> None:
        item = self.get(job_id)
        self._owned(item, uid, station_id)
        if item["status"] in {"claimed", "transmitting", "completed"}:
            raise api_error(409, "TX_INVALID_STATE", "TX job cannot be cancelled")
        self.collection.document(job_id).update({"status": "cancelled"})

    def retry(self, uid: str, station_id: str, job_id: str, new_id: str) -> dict:
        failed = self.get(job_id)
        self._owned(failed, uid, station_id)
        if failed["status"] != "failed":
            raise api_error(409, "TX_INVALID_STATE", "Only failed jobs can be retried")
        clone = dict(failed, id=new_id, status="review_ready", attempt=failed.get("attempt", 1) + 1,
                     retry_of=job_id, created_at=datetime.now(timezone.utc))
        self.create(clone)
        return self.confirm(uid, station_id, new_id)

    def claim(self, station_id: str) -> dict | None:
        transaction = self.db.transaction()
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            active = active_ref.get(transaction=tx)
            job_id = (active.to_dict() or {}).get("job_id") if active.exists else None
            if not job_id:
                return None
            ref = self.collection.document(job_id)
            snap = ref.get(transaction=tx)
            if not snap.exists:
                tx.set(active_ref, {"job_id": "", "status": "failed"})
                return None
            item = {"id": snap.id, **(snap.to_dict() or {})}
            if item.get("status") != "queued":
                return None
            tx.update(ref, {"status": "claimed", "claimed_at": firestore.SERVER_TIMESTAMP})
            tx.update(active_ref, {"status": "claimed"})
            return dict(item, status="claimed")
        return apply(transaction)

    def station_update(self, station_id: str, job_id: str, status: str, error: str | None = None) -> dict:
        item = self.get(job_id)
        if not item or item.get("station_id") != station_id:
            raise api_error(404, "TX_NOT_FOUND", "TX job was not found")
        allowed = {"claimed": {"transmitting", "failed"}, "transmitting": {"completed", "failed"}}
        if status not in allowed.get(item["status"], set()):
            raise api_error(409, "TX_INVALID_STATE", "Invalid TX transition")
        self.collection.document(job_id).update({"status": status, "error": error, "updated_at": firestore.SERVER_TIMESTAMP})
        if status in {"completed", "failed"}:
            self.db.collection("station_tx_state").document(station_id).set({"job_id": "", "status": status})
        return dict(item, status=status, error=error)

    @staticmethod
    def _owned(item: dict | None, uid: str, station_id: str) -> None:
        if not item or item.get("uid") != uid or item.get("station_id") != station_id:
            raise api_error(404, "TX_NOT_FOUND", "TX draft was not found")
