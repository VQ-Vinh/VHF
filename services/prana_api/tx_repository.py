from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from services.prana_api.errors import api_error


ACTIVE_TX_STATES = {"synthesizing", "queued", "claimed", "transmitting"}
HISTORY_TX_STATES = ACTIVE_TX_STATES | {"completed", "failed"}
SYNTHESIS_LEASE_SECONDS = 180


class MemoryTxRepository:
    def __init__(self):
        self.lock = threading.RLock()
        self.items: dict[str, dict] = {}
        self.counters: dict[tuple[str, str], int] = {}

    def next_filename(self, station_id: str, created_at: datetime) -> str:
        day = created_at.strftime("%Y%m%d")
        with self.lock:
            key = (station_id, day)
            self.counters[key] = self.counters.get(key, 0) + 1
            return f"{created_at:%Y%m%d_%H%M%S}_{self.counters[key]:04d}.wav"

    def create(self, value: dict) -> dict:
        with self.lock:
            self.items[value["id"]] = dict(value)
            return dict(value)

    def reserve_processing(self, value: dict, request_hash: str) -> tuple[dict, bool]:
        with self.lock:
            existing = self.items.get(value["id"])
            if existing:
                if (
                    existing.get("uid") != value.get("uid")
                    or existing.get("station_id") != value.get("station_id")
                    or existing.get("request_hash") != request_hash
                ):
                    raise api_error(409, "IDEMPOTENCY_CONFLICT", "Request ID is already used")
                return dict(existing), False
            reserved = dict(
                value,
                status="processing",
                request_hash=request_hash,
                processing_lease_expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=SYNTHESIS_LEASE_SECONDS),
            )
            self.items[value["id"]] = reserved
            return dict(reserved), True

    def complete_processing(self, job_id: str, updates: dict) -> dict:
        with self.lock:
            item = self.items.get(job_id)
            if not item or item.get("status") != "processing":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is no longer processing")
            item.update(updates)
            item["status"] = "review_ready"
            item.pop("processing_lease_expires_at", None)
            return dict(item)

    def release_processing(self, job_id: str) -> None:
        with self.lock:
            if self.items.get(job_id, {}).get("status") == "processing":
                del self.items[job_id]

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

    def begin_confirm(self, uid: str, station_id: str, job_id: str, translation: str) -> dict:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item["status"] != "review_ready":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is not ready")
            if any(other["station_id"] == station_id and other["status"] in ACTIVE_TX_STATES for other in self.items.values()):
                raise api_error(409, "TX_BUSY", "Station already has an active TX job")
            item.update({
                "status": "synthesizing",
                "translation": translation,
                "translation_edited": translation != item.get("translation_original", ""),
                "confirmed": True,
                "synthesis_started_at": datetime.now(timezone.utc),
                "synthesis_lease_expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=SYNTHESIS_LEASE_SECONDS),
            })
            return dict(item)

    def finish_confirm(self, uid: str, station_id: str, job_id: str, output_object: str) -> dict:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item["status"] != "synthesizing":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is not synthesizing")
            item.update({"status": "queued", "output_object": output_object, "output_available": True})
            item.pop("synthesis_lease_expires_at", None)
            return dict(item)

    def fail_synthesis(self, uid: str, station_id: str, job_id: str, error: str) -> dict:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item.get("status") != "synthesizing":
                return dict(item)
            item.update({"status": "failed", "error": error, "output_available": False})
            return dict(item)

    def history(self, uid: str, station_id: str) -> list[dict]:
        with self.lock:
            values = [dict(item) for item in self.items.values() if item.get("uid") == uid and item.get("station_id") == station_id and item.get("status") in HISTORY_TX_STATES and item.get("confirmed", True)]
        return sorted(values, key=lambda item: item["created_at"], reverse=True)

    def cancel(self, uid: str, station_id: str, job_id: str) -> None:
        with self.lock:
            item = self._owned(uid, station_id, job_id)
            if item["status"] != "review_ready":
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
            clone = dict(failed, id=new_id, status="review_ready", attempt=failed.get("attempt", 1) + 1,
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

    def expire_stale_active(
        self, station_id: str, station_stale: bool, now: datetime
    ) -> dict | None:
        with self.lock:
            synthesizing = next(
                (
                    item
                    for item in self.items.values()
                    if item.get("station_id") == station_id
                    and item.get("status") == "synthesizing"
                    and item.get("synthesis_lease_expires_at")
                    and item["synthesis_lease_expires_at"] <= now
                ),
                None,
            )
            if synthesizing is not None:
                synthesizing.update(
                    {
                        "status": "failed",
                        "error": "TX_SYNTHESIS_TIMEOUT",
                        "output_available": False,
                        "updated_at": now,
                    }
                )
                return dict(synthesizing)
            active = next(
                (
                    item
                    for item in self.items.values()
                    if item.get("station_id") == station_id
                    and item.get("status") in {"claimed", "transmitting"}
                ),
                None,
            )
            if active is None:
                return None
            activity_at = (
                active.get("updated_at")
                or active.get("claimed_at")
                or active.get("created_at")
            )
            lease_stale = bool(
                activity_at
                and activity_at <= now - timedelta(seconds=90)
            )
            if not station_stale and not lease_stale:
                return None
            active.update(
                {
                    "status": "failed",
                    "error": "STATION_OFFLINE_DURING_TX",
                    "updated_at": now,
                }
            )
            return dict(active)

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

    def reserve_processing(self, value: dict, request_hash: str) -> tuple[dict, bool]:
        transaction = self.db.transaction()
        ref = self.collection.document(value["id"])

        @firestore.transactional
        def apply(tx):
            snap = ref.get(transaction=tx)
            if snap.exists:
                existing = {"id": snap.id, **(snap.to_dict() or {})}
                if (
                    existing.get("uid") != value.get("uid")
                    or existing.get("station_id") != value.get("station_id")
                    or existing.get("request_hash") != request_hash
                ):
                    raise api_error(409, "IDEMPOTENCY_CONFLICT", "Request ID is already used")
                return existing, False
            reserved = dict(
                value,
                status="processing",
                request_hash=request_hash,
                processing_lease_expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=SYNTHESIS_LEASE_SECONDS),
            )
            tx.set(ref, reserved)
            return reserved, True

        return apply(transaction)

    def complete_processing(self, job_id: str, updates: dict) -> dict:
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)

        @firestore.transactional
        def apply(tx):
            snap = ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            if not item or item.get("status") != "processing":
                raise api_error(409, "TX_INVALID_STATE", "TX draft is no longer processing")
            values = dict(updates, status="review_ready", processing_lease_expires_at=firestore.DELETE_FIELD)
            tx.update(ref, values)
            return dict(item, **updates, status="review_ready")

        return apply(transaction)

    def release_processing(self, job_id: str) -> None:
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)

        @firestore.transactional
        def apply(tx):
            snap = ref.get(transaction=tx)
            if snap.exists and (snap.to_dict() or {}).get("status") == "processing":
                tx.delete(ref)

        apply(transaction)

    def get(self, job_id: str) -> dict | None:
        snap = self.collection.document(job_id).get()
        return ({"id": snap.id, **snap.to_dict()} if snap.exists else None)

    def next_filename(self, station_id: str, created_at: datetime) -> str:
        day = created_at.strftime("%Y%m%d")
        ref = self.db.collection("station_tx_counters").document(f"{station_id}_{day}")
        transaction = self.db.transaction()

        @firestore.transactional
        def allocate(tx):
            snap = ref.get(transaction=tx)
            sequence = int((snap.to_dict() or {}).get("sequence", 0)) + 1
            tx.set(ref, {"station_id": station_id, "date": day, "sequence": sequence})
            return sequence

        sequence = allocate(transaction)
        return f"{created_at:%Y%m%d_%H%M%S}_{sequence:04d}.wav"

    def begin_confirm(self, uid: str, station_id: str, job_id: str, translation: str) -> dict:
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
            if (active.to_dict() or {}).get("job_id"):
                raise api_error(409, "TX_BUSY", "Station already has an active TX job")
            now = datetime.now(timezone.utc)
            updates = {"status": "synthesizing", "translation": translation, "translation_edited": translation != item.get("translation_original", ""), "confirmed": True, "synthesis_started_at": now, "synthesis_lease_expires_at": now + timedelta(seconds=SYNTHESIS_LEASE_SECONDS), "updated_at": firestore.SERVER_TIMESTAMP}
            tx.update(ref, updates)
            tx.set(active_ref, {"job_id": job_id, "status": "synthesizing"})
            return dict(item, **{key: value for key, value in updates.items() if key != "updated_at"})
        return apply(transaction)

    def finish_confirm(self, uid: str, station_id: str, job_id: str, output_object: str) -> dict:
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            snap, active = ref.get(transaction=tx), active_ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            self._owned(item, uid, station_id)
            if item["status"] != "synthesizing" or (active.to_dict() or {}).get("job_id") != job_id:
                raise api_error(409, "TX_INVALID_STATE", "TX draft is no longer synthesizing")
            updates = {"status": "queued", "output_object": output_object, "output_available": True, "synthesis_lease_expires_at": firestore.DELETE_FIELD, "updated_at": firestore.SERVER_TIMESTAMP}
            tx.update(ref, updates)
            tx.update(active_ref, {"status": "queued"})
            return dict(item, status="queued", output_object=output_object, output_available=True)

        return apply(transaction)

    def fail_synthesis(self, uid: str, station_id: str, job_id: str, error: str) -> dict:
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            snap, active = ref.get(transaction=tx), active_ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            self._owned(item, uid, station_id)
            if item.get("status") != "synthesizing":
                return item
            updates = {"status": "failed", "error": error, "output_available": False, "updated_at": firestore.SERVER_TIMESTAMP}
            tx.update(ref, updates)
            if (active.to_dict() or {}).get("job_id") == job_id:
                tx.set(active_ref, {"job_id": "", "status": "failed"})
            return dict(item, status="failed", error=error, output_available=False)

        return apply(transaction)

    def history(self, uid: str, station_id: str) -> list[dict]:
        values = []
        for snap in self.collection.where("station_id", "==", station_id).stream():
            item = {"id": snap.id, **(snap.to_dict() or {})}
            if item.get("uid") == uid and item.get("status") in HISTORY_TX_STATES and item.get("confirmed", True):
                values.append(item)
        return sorted(values, key=lambda item: item["created_at"], reverse=True)

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
        transaction = self.db.transaction()
        ref = self.collection.document(job_id)

        @firestore.transactional
        def apply(tx):
            snap = ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            self._owned(item, uid, station_id)
            if item["status"] != "review_ready":
                raise api_error(409, "TX_INVALID_STATE", "TX job cannot be cancelled")
            tx.update(ref, {"status": "cancelled", "updated_at": firestore.SERVER_TIMESTAMP})

        apply(transaction)

    def retry(self, uid: str, station_id: str, job_id: str, new_id: str) -> dict:
        failed = self.get(job_id)
        self._owned(failed, uid, station_id)
        if failed["status"] != "failed":
            raise api_error(409, "TX_INVALID_STATE", "Only failed jobs can be retried")
        clone = dict(failed, id=new_id, status="review_ready", attempt=failed.get("attempt", 1) + 1,
                     retry_of=job_id, created_at=datetime.now(timezone.utc))
        return self.create(clone)

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
        transaction = self.db.transaction()
        job_ref = self.collection.document(job_id)
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            snap = job_ref.get(transaction=tx)
            item = {"id": snap.id, **(snap.to_dict() or {})} if snap.exists else None
            if not item or item.get("station_id") != station_id:
                raise api_error(404, "TX_NOT_FOUND", "TX job was not found")
            allowed = {
                "claimed": {"transmitting", "failed"},
                "transmitting": {"completed", "failed"},
            }
            if status not in allowed.get(item["status"], set()):
                raise api_error(409, "TX_INVALID_STATE", "Invalid TX transition")
            tx.update(
                job_ref,
                {
                    "status": status,
                    "error": error,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )
            if status in {"completed", "failed"}:
                tx.set(active_ref, {"job_id": "", "status": status})
            return dict(item, status=status, error=error)

        return apply(transaction)

    def expire_stale_active(
        self, station_id: str, station_stale: bool, now: datetime
    ) -> dict | None:
        """Fail an abandoned claimed/transmitting job and release its active slot."""
        transaction = self.db.transaction()
        active_ref = self.db.collection("station_tx_state").document(station_id)

        @firestore.transactional
        def apply(tx):
            active_snap = active_ref.get(transaction=tx)
            active_data = active_snap.to_dict() or {}
            job_id = active_data.get("job_id")
            if not job_id:
                return None
            job_ref = self.collection.document(job_id)
            job_snap = job_ref.get(transaction=tx)
            if not job_snap.exists:
                tx.set(active_ref, {"job_id": "", "status": "failed"})
                return None
            item = {"id": job_snap.id, **(job_snap.to_dict() or {})}
            status = item.get("status")
            if status not in ACTIVE_TX_STATES:
                tx.set(active_ref, {"job_id": "", "status": status or "failed"})
                return None
            if status == "synthesizing":
                lease_expires_at = item.get("synthesis_lease_expires_at")
                if not lease_expires_at or lease_expires_at > now:
                    return None
                updates = {
                    "status": "failed",
                    "error": "TX_SYNTHESIS_TIMEOUT",
                    "output_available": False,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
                tx.update(job_ref, updates)
                tx.set(active_ref, {"job_id": "", "status": "failed"})
                return dict(item, status="failed", error=updates["error"])
            if status not in {"claimed", "transmitting"}:
                return None
            activity_at = (
                item.get("updated_at")
                or item.get("claimed_at")
                or item.get("created_at")
            )
            lease_stale = bool(
                activity_at
                and activity_at <= now - timedelta(seconds=90)
            )
            if not station_stale and not lease_stale:
                return None
            updates = {
                "status": "failed",
                "error": "STATION_OFFLINE_DURING_TX",
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            tx.update(job_ref, updates)
            tx.set(active_ref, {"job_id": "", "status": "failed"})
            return dict(item, status="failed", error=updates["error"])

        return apply(transaction)

    @staticmethod
    def _owned(item: dict | None, uid: str, station_id: str) -> None:
        if not item or item.get("uid") != uid or item.get("station_id") != station_id:
            raise api_error(404, "TX_NOT_FOUND", "TX draft was not found")
