from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from services.prana_api.errors import api_error
from services.prana_api.models import Device, Plan, Reservation, Usage, UserAccount
from services.prana_api.repository import identity_updates, usage_period, usage_reset_at


class MemoryRepository:
    """Atomic in-memory repository for tests and local API development only."""

    def __init__(self, global_daily_audio_seconds: int = 0, global_monthly_audio_seconds: int = 0):
        self.lock = threading.RLock()
        self.users: dict[str, UserAccount] = {}
        self.plans: dict[str, Plan] = {}
        self.devices: dict[str, dict[str, Device]] = {}
        self.usage: dict[tuple[str, str], dict] = {}
        self.requests: dict[tuple[str, str], dict] = {}
        self.rates: dict[tuple[str, int], int] = {}
        self.global_daily_audio_seconds = global_daily_audio_seconds
        self.global_monthly_audio_seconds = global_monthly_audio_seconds
        self.global_used = 0
        self.global_reserved = 0

    def sync_identity(self, uid: str, email: str, email_verified: bool) -> UserAccount:
        with self.lock:
            account = self.users.get(uid)
            if account is None:
                account = UserAccount(
                    uid=uid,
                    email=email,
                    email_verified=email_verified,
                    status="active" if email_verified else "registered",
                    plan_id="free" if email_verified else None,
                )
            else:
                current = account.model_dump()
                current["email_lower"] = account.email.strip().lower()
                updates = identity_updates(
                    current,
                    email,
                    email_verified,
                    datetime.now(timezone.utc),
                )
                account = account.model_copy(
                    update={key: value for key, value in updates.items() if key in UserAccount.model_fields}
                )
            self.users[uid] = account
            return account

    def get_plan(self, plan_id: str) -> Plan:
        if plan_id not in self.plans:
            raise api_error(403, "SUBSCRIPTION_INACTIVE", "Assigned plan does not exist")
        return self.plans[plan_id]

    def list_plans(self) -> list[Plan]:
        return sorted(self.plans.values(), key=lambda plan: (plan.sort_order, plan.id))

    def select_plan(self, uid: str, plan: Plan) -> UserAccount:
        with self.lock:
            if plan.availability != "available" or plan.id != "free":
                raise api_error(409, "PLAN_NOT_AVAILABLE", "This plan is not available yet")
            account = self.users.get(uid)
            if not account:
                raise api_error(404, "ACCOUNT_NOT_FOUND", "Account was not found")
            if not account.email_verified:
                raise api_error(403, "EMAIL_NOT_VERIFIED", "Verify your email before selecting a plan")
            if account.status == "suspended":
                raise api_error(403, "SUBSCRIPTION_INACTIVE", "Account is suspended")
            account = account.model_copy(update={
                "status": "active",
                "plan_id": plan.id,
                "subscription_expires_at": None,
            })
            self.users[uid] = account
            return account

    def get_usage(self, uid: str, plan: Plan) -> Usage:
        now = datetime.now(timezone.utc)
        period = usage_period(plan, now)
        data = self.usage.get((uid, period), {})
        return Usage(
            period=period,
            audio_seconds_limit=plan.audio_seconds_limit,
            monthly_audio_seconds=plan.audio_seconds_limit,
            quota_period=plan.quota_period,
            resets_at=usage_reset_at(plan, now),
            **data,
        )

    def list_devices(self, uid: str) -> list[Device]:
        return list(self.devices.get(uid, {}).values())

    def register_device(self, uid: str, device: Device, max_devices: int) -> Device:
        with self.lock:
            devices = self.devices.setdefault(uid, {})
            current = devices.get(device.id)
            if current:
                if current.public_key != device.public_key:
                    raise api_error(409, "DEVICE_ID_CONFLICT", "Device ID is already registered")
                if not current.active:
                    raise api_error(403, "DEVICE_REVOKED", "Device access has been revoked")
                return current
            if sum(item.active for item in devices.values()) >= max_devices:
                raise api_error(403, "DEVICE_LIMIT_REACHED", f"Maximum {max_devices} active devices")
            devices[device.id] = device
            return device

    def get_device(self, uid: str, device_id: str) -> Device | None:
        return self.devices.get(uid, {}).get(device_id)

    def revoke_device(self, uid: str, device_id: str) -> None:
        with self.lock:
            device = self.get_device(uid, device_id)
            if not device:
                raise api_error(404, "DEVICE_NOT_FOUND", "Device was not found")
            self.devices[uid][device_id] = device.model_copy(update={"active": False})

    def reserve(self, uid: str, plan: Plan, request_id: str, request_hash: str, seconds: int) -> Reservation:
        with self.lock:
            key = (uid, request_id)
            request = self.requests.get(key)
            if request:
                if request["body_hash"] != request_hash:
                    raise api_error(409, "IDEMPOTENCY_CONFLICT", "Request ID was used with different content")
                if request["state"] == "completed":
                    return Reservation(request_id=request_id, state="completed", cached_response=request["response"])
                if request["state"] == "processing":
                    raise api_error(409, "REQUEST_IN_PROGRESS", "Request is already processing", retry_after=2)

            now = datetime.now(timezone.utc)
            period = usage_period(plan, now)
            usage_key = (uid, period)
            usage = self.usage.setdefault(
                usage_key,
                {"used_audio_seconds": 0, "reserved_audio_seconds": 0, "active_requests": 0, "request_count": 0},
            )
            if usage["active_requests"] >= plan.max_concurrency:
                raise api_error(429, "RATE_LIMITED", "Too many concurrent requests")
            if usage["used_audio_seconds"] + usage["reserved_audio_seconds"] + seconds > plan.audio_seconds_limit:
                raise api_error(
                    429,
                    "DAILY_QUOTA_EXCEEDED" if plan.quota_period == "daily" else "MONTHLY_QUOTA_EXCEEDED",
                    "Daily audio quota is exhausted" if plan.quota_period == "daily" else "Monthly audio quota is exhausted",
                    resets_at=usage_reset_at(plan, now).isoformat(),
                )
            minute = int(time.time() // 60)
            if self.rates.get((uid, minute), 0) >= plan.requests_per_minute:
                raise api_error(429, "RATE_LIMITED", "Requests-per-minute limit exceeded")
            for limit in (self.global_daily_audio_seconds, self.global_monthly_audio_seconds):
                if limit and self.global_used + self.global_reserved + seconds > limit:
                    raise api_error(503, "SERVICE_USAGE_LIMIT_REACHED", "Service-wide usage limit reached")

            usage["reserved_audio_seconds"] += seconds
            usage["active_requests"] += 1
            self.global_reserved += seconds
            self.rates[(uid, minute)] = self.rates.get((uid, minute), 0) + 1
            self.requests[key] = {
                "state": "processing",
                "body_hash": request_hash,
                "seconds": seconds,
                "usage_period": period,
            }
            return Reservation(request_id=request_id, state="reserved")

    def _settle(self, uid: str, request_id: str, response: dict | None, error_code: str | None, metrics: dict) -> None:
        with self.lock:
            request = self.requests.get((uid, request_id))
            if not request or request["state"] != "processing":
                return
            seconds = request["seconds"]
            usage = self.usage[(uid, request["usage_period"])]
            usage["reserved_audio_seconds"] -= seconds
            usage["active_requests"] -= 1
            self.global_reserved -= seconds
            if response is not None:
                usage["used_audio_seconds"] += seconds
                usage["request_count"] += 1
                self.global_used += seconds
                request.update({"state": "completed", "response": response, "metrics": metrics})
            else:
                request.update({"state": "failed", "error_code": error_code, "metrics": metrics})

    def settle_success(self, uid: str, request_id: str, response: dict, metrics: dict) -> None:
        self._settle(uid, request_id, response, None, metrics)

    def settle_failure(self, uid: str, request_id: str, error_code: str, metrics: dict) -> None:
        self._settle(uid, request_id, None, error_code, metrics)
