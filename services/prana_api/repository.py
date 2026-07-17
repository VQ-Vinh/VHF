from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from google.cloud import firestore

from services.prana_api.errors import api_error
from services.prana_api.models import Device, Plan, Reservation, Usage, UserAccount


def current_period(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


class Repository(Protocol):
    def sync_identity(self, uid: str, email: str, email_verified: bool) -> UserAccount: ...
    def get_plan(self, plan_id: str) -> Plan: ...
    def get_usage(self, uid: str, plan: Plan) -> Usage: ...
    def list_devices(self, uid: str) -> list[Device]: ...
    def register_device(self, uid: str, device: Device, max_devices: int) -> Device: ...
    def get_device(self, uid: str, device_id: str) -> Device | None: ...
    def revoke_device(self, uid: str, device_id: str) -> None: ...
    def reserve(
        self, uid: str, plan: Plan, request_id: str, request_hash: str, seconds: int
    ) -> Reservation: ...
    def settle_success(self, uid: str, request_id: str, response: dict, metrics: dict) -> None: ...
    def settle_failure(self, uid: str, request_id: str, error_code: str, metrics: dict) -> None: ...


class FirestoreRepository:
    def __init__(
        self,
        project: str = "",
        global_daily_audio_seconds: int = 0,
        global_monthly_audio_seconds: int = 0,
    ):
        self.db = firestore.Client(project=project or None)
        self.global_daily_audio_seconds = global_daily_audio_seconds
        self.global_monthly_audio_seconds = global_monthly_audio_seconds

    def _user_ref(self, uid: str):
        return self.db.collection("users").document(uid)

    def sync_identity(self, uid: str, email: str, email_verified: bool) -> UserAccount:
        ref = self._user_ref(uid)
        snap = ref.get()
        if not snap.exists:
            status = "pending_payment" if email_verified else "registered"
            data = {
                "uid": uid,
                "email": email,
                "email_lower": email.strip().lower(),
                "email_verified": email_verified,
                "status": status,
                "plan_id": None,
                "subscription_expires_at": None,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            ref.set(data)
            return UserAccount(uid=uid, email=email, email_verified=email_verified, status=status)
        data = snap.to_dict()
        updates = {"email": email, "email_lower": email.strip().lower(),
                   "email_verified": email_verified, "updated_at": firestore.SERVER_TIMESTAMP}
        if email_verified and data.get("status") in {"registered", "email_verified"}:
            updates["status"] = "pending_payment"
            updates["email_verified_at"] = firestore.SERVER_TIMESTAMP
        expires = data.get("subscription_expires_at")
        if data.get("status") == "active" and expires is not None and expires <= datetime.now(timezone.utc):
            updates["status"] = "expired"
        ref.update(updates)
        data.update(updates)
        data["uid"] = uid
        return UserAccount.model_validate(data)

    def get_plan(self, plan_id: str) -> Plan:
        snap = self.db.collection("plans").document(plan_id).get()
        if not snap.exists:
            raise api_error(403, "SUBSCRIPTION_INACTIVE", "Assigned plan does not exist")
        return Plan(id=snap.id, **snap.to_dict())

    def get_usage(self, uid: str, plan: Plan) -> Usage:
        period = current_period()
        snap = self._user_ref(uid).collection("usage").document(period).get()
        data = snap.to_dict() if snap.exists else {}
        return Usage(period=period, monthly_audio_seconds=plan.monthly_audio_seconds, **data)

    def list_devices(self, uid: str) -> list[Device]:
        docs = self._user_ref(uid).collection("devices").stream()
        return [Device(id=doc.id, uid=uid, **doc.to_dict()) for doc in docs]

    def _register_transaction(self, tx, uid: str, device: Device, max_devices: int) -> Device:
        collection = self._user_ref(uid).collection("devices")
        existing_ref = collection.document(device.id)
        existing = existing_ref.get(transaction=tx)
        if existing.exists:
            current = Device(id=existing.id, uid=uid, **existing.to_dict())
            if current.public_key != device.public_key:
                raise api_error(409, "DEVICE_ID_CONFLICT", "Device ID is already registered")
            if not current.active:
                raise api_error(403, "DEVICE_REVOKED", "Device access has been revoked")
            tx.update(existing_ref, {"last_seen_at": firestore.SERVER_TIMESTAMP})
            return current
        active = list(collection.where("active", "==", True).stream(transaction=tx))
        if len(active) >= max_devices:
            raise api_error(403, "DEVICE_LIMIT_REACHED", f"Maximum {max_devices} active devices")
        tx.set(existing_ref, device.model_dump(exclude={"id", "uid"}))
        return device

    def register_device(self, uid: str, device: Device, max_devices: int) -> Device:
        @firestore.transactional
        def run(tx):
            return self._register_transaction(tx, uid, device, max_devices)

        return run(self.db.transaction())

    def get_device(self, uid: str, device_id: str) -> Device | None:
        snap = self._user_ref(uid).collection("devices").document(device_id).get()
        return Device(id=snap.id, uid=uid, **snap.to_dict()) if snap.exists else None

    def revoke_device(self, uid: str, device_id: str) -> None:
        ref = self._user_ref(uid).collection("devices").document(device_id)
        if not ref.get().exists:
            raise api_error(404, "DEVICE_NOT_FOUND", "Device was not found")
        ref.update({"active": False, "revoked_at": firestore.SERVER_TIMESTAMP})

    def _reserve_transaction(
        self, tx, uid: str, plan: Plan, request_id: str, request_hash: str, seconds: int
    ) -> Reservation:
        user_ref = self._user_ref(uid)
        request_ref = user_ref.collection("requests").document(request_id)
        request_snap = request_ref.get(transaction=tx)
        stale_reserved = 0
        existing_request = {}
        if request_snap.exists:
            data = request_snap.to_dict()
            existing_request = data
            if data.get("body_hash") != request_hash:
                raise api_error(409, "IDEMPOTENCY_CONFLICT", "Request ID was used with different content")
            if data.get("state") == "completed":
                return Reservation(request_id=request_id, state="completed", cached_response=data.get("response"))
            lease = data.get("lease_expires_at")
            if data.get("state") == "processing" and (lease is None or lease > datetime.now(timezone.utc)):
                raise api_error(409, "REQUEST_IN_PROGRESS", "Request is already processing", retry_after=2)
            if data.get("state") == "processing":
                stale_reserved = int(data.get("reserved_audio_seconds", 0))

        now = datetime.now(timezone.utc)
        period = current_period(now)
        usage_ref = user_ref.collection("usage").document(period)
        usage_snap = usage_ref.get(transaction=tx)
        usage = usage_snap.to_dict() if usage_snap.exists else {}
        used = int(usage.get("used_audio_seconds", 0))
        reserved = max(0, int(usage.get("reserved_audio_seconds", 0)) - stale_reserved)
        active = max(0, int(usage.get("active_requests", 0)) - (1 if stale_reserved else 0))
        if active >= plan.max_concurrency:
            raise api_error(429, "RATE_LIMITED", "Too many concurrent requests")
        if used + reserved + seconds > plan.monthly_audio_seconds:
            raise api_error(429, "MONTHLY_QUOTA_EXCEEDED", "Monthly audio quota is exhausted")

        minute_key = now.strftime("%Y%m%d%H%M")
        rate_ref = user_ref.collection("rate_minutes").document(minute_key)
        rate_snap = rate_ref.get(transaction=tx)
        rate_count = int((rate_snap.to_dict() if rate_snap.exists else {}).get("count", 0))
        if rate_count >= plan.requests_per_minute:
            raise api_error(429, "RATE_LIMITED", "Requests-per-minute limit exceeded")

        global_refs = [
            (self.db.collection("system_usage").document(f"daily-{now:%Y%m%d}"), self.global_daily_audio_seconds),
            (self.db.collection("system_usage").document(f"monthly-{period}"), self.global_monthly_audio_seconds),
        ]
        global_values = []
        for global_ref, limit in global_refs:
            snap = global_ref.get(transaction=tx)
            value = snap.to_dict() if snap.exists else {}
            if stale_reserved and global_ref.id in existing_request.get("global_usage_keys", []):
                value["reserved_audio_seconds"] = max(
                    0, int(value.get("reserved_audio_seconds", 0)) - stale_reserved
                )
            if limit > 0 and int(value.get("used_audio_seconds", 0)) + int(value.get("reserved_audio_seconds", 0)) + seconds > limit:
                raise api_error(503, "SERVICE_USAGE_LIMIT_REACHED", "Service-wide usage limit reached")
            global_values.append((global_ref, value))

        tx.set(
            usage_ref,
            {
                "used_audio_seconds": used,
                "reserved_audio_seconds": reserved + seconds,
                "active_requests": active + 1,
                "request_count": int(usage.get("request_count", 0)),
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        tx.set(rate_ref, {"count": rate_count + 1, "expires_at": now + timedelta(minutes=2)}, merge=True)
        for global_ref, value in global_values:
            tx.set(
                global_ref,
                {
                    "used_audio_seconds": int(value.get("used_audio_seconds", 0)),
                    "reserved_audio_seconds": int(value.get("reserved_audio_seconds", 0)) + seconds,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
        tx.set(
            request_ref,
            {
                "state": "processing",
                "body_hash": request_hash,
                "reserved_audio_seconds": seconds,
                "usage_period": period,
                "global_usage_keys": [ref.id for ref, _value in global_values],
                "created_at": firestore.SERVER_TIMESTAMP,
                "lease_expires_at": now + timedelta(minutes=4),
            },
        )
        return Reservation(request_id=request_id, state="reserved")

    def reserve(self, uid: str, plan: Plan, request_id: str, request_hash: str, seconds: int) -> Reservation:
        @firestore.transactional
        def run(tx):
            return self._reserve_transaction(tx, uid, plan, request_id, request_hash, seconds)

        return run(self.db.transaction())

    def _settle_transaction(
        self, tx, uid: str, request_id: str, response: dict | None, error_code: str | None, metrics: dict
    ) -> None:
        user_ref = self._user_ref(uid)
        request_ref = user_ref.collection("requests").document(request_id)
        request_snap = request_ref.get(transaction=tx)
        if not request_snap.exists or request_snap.to_dict().get("state") != "processing":
            return
        request = request_snap.to_dict()
        seconds = int(request.get("reserved_audio_seconds", 0))
        period = request.get("usage_period") or current_period()
        usage_ref = user_ref.collection("usage").document(period)
        usage_snap = usage_ref.get(transaction=tx)
        usage = usage_snap.to_dict() if usage_snap.exists else {}
        success = response is not None
        global_values = []
        for key in request.get("global_usage_keys", []):
            global_ref = self.db.collection("system_usage").document(key)
            snap = global_ref.get(transaction=tx)
            global_values.append((global_ref, snap.to_dict() if snap.exists else {}))
        tx.set(
            usage_ref,
            {
                "reserved_audio_seconds": max(0, int(usage.get("reserved_audio_seconds", 0)) - seconds),
                "active_requests": max(0, int(usage.get("active_requests", 0)) - 1),
                "used_audio_seconds": int(usage.get("used_audio_seconds", 0)) + (seconds if success else 0),
                "request_count": int(usage.get("request_count", 0)) + (1 if success else 0),
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        for global_ref, value in global_values:
            tx.set(
                global_ref,
                {
                    "reserved_audio_seconds": max(0, int(value.get("reserved_audio_seconds", 0)) - seconds),
                    "used_audio_seconds": int(value.get("used_audio_seconds", 0)) + (seconds if success else 0),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
        update = {
            "state": "completed" if success else "failed",
            "completed_at": firestore.SERVER_TIMESTAMP,
            "metrics": metrics,
        }
        if success:
            update["response"] = response
        else:
            update["error_code"] = error_code
        tx.update(request_ref, update)

    def settle_success(self, uid: str, request_id: str, response: dict, metrics: dict) -> None:
        @firestore.transactional
        def run(tx):
            return self._settle_transaction(tx, uid, request_id, response, None, metrics)

        run(self.db.transaction())

    def settle_failure(self, uid: str, request_id: str, error_code: str, metrics: dict) -> None:
        @firestore.transactional
        def run(tx):
            return self._settle_transaction(tx, uid, request_id, None, error_code, metrics)

        run(self.db.transaction())
