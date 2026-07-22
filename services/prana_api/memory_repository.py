from __future__ import annotations

import threading
import time
import hmac
import hashlib
from datetime import datetime, timezone

from services.prana_api.errors import api_error
from services.prana_api.models import (
    Device,
    Plan,
    Reservation,
    Station,
    StationDesiredState,
    StationHeartbeat,
    StationPairingRequest,
    StationProvisionRequest,
    Usage,
    UserAccount,
)
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
        self.station_registry: dict[str, dict] = {}
        self.station_pairings: dict[str, dict] = {}
        self.station_projections: dict[str, dict[str, dict]] = {}
        self.station_nonces: set[tuple[str, str]] = set()
        self.station_results: dict[tuple[str, str, str, str], dict] = {}
        self.station_pairing_attempts: dict[tuple[str, str, int], int] = {}
        self.station_activation_index: dict[str, str] = {}
        self.station_activation_attempts: dict[tuple[str, str, int], int] = {}

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

    def get_account(self, uid: str) -> UserAccount | None:
        return self.users.get(uid)

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

    def create_station_pairing(
        self,
        request: StationPairingRequest,
        pairing_id: str,
        secret_hash: str,
        expires_at: datetime,
    ) -> None:
        with self.lock:
            current = self.station_registry.get(request.station_id)
            if current and current["public_key"] != request.public_key:
                raise api_error(409, "STATION_ID_CONFLICT", "Station ID is already registered")
            if current and current.get("active") is False:
                raise api_error(403, "STATION_REVOKED", "Station access has been revoked")
            if current and current.get("owner_uid"):
                raise api_error(409, "STATION_ALREADY_CLAIMED", "Station already has an owner")
            last_pairing = current.get("last_pairing_created_at") if current else None
            if last_pairing and (datetime.now(timezone.utc) - last_pairing).total_seconds() < 60:
                raise api_error(429, "RATE_LIMITED", "Wait before creating another pairing code")
            self.station_registry[request.station_id] = {
                **(current or {}),
                **request.model_dump(exclude={"station_id"}),
                "station_id": request.station_id,
                "active": True,
                "owner_uid": None,
                "desired_state": (current or {}).get("desired_state", StationDesiredState().model_dump()),
                "observed_generation": 0,
                "last_pairing_created_at": datetime.now(timezone.utc),
            }
            self.station_pairings[pairing_id] = {
                "station_id": request.station_id,
                "secret_hash": secret_hash,
                "expires_at": expires_at,
                "claimed_at": None,
            }

    @staticmethod
    def _station(station_id: str, data: dict) -> Station:
        return Station(
            station_id=station_id,
            name=data.get("name", "PRANA station"),
            platform=data.get("platform", "unknown"),
            active=data.get("active", True),
            online=data.get("online", False),
            capture_state=data.get("capture_state", "idle"),
            desired_state=StationDesiredState.model_validate(data.get("desired_state") or {}),
            observed_generation=data.get("observed_generation", 0),
            session_id=data.get("session_id", ""),
            sequence=data.get("sequence", 0),
            last_seen_at=data.get("last_seen_at"),
        )

    def claim_station(self, uid: str, pairing_id: str, secret_hash: str, max_stations: int) -> Station:
        with self.lock:
            pairing = self.station_pairings.get(pairing_id)
            if not pairing:
                raise api_error(404, "PAIRING_NOT_FOUND", "Pairing was not found")
            if pairing["claimed_at"] is not None:
                raise api_error(409, "PAIRING_ALREADY_USED", "Pairing code has already been used")
            if pairing["expires_at"] <= datetime.now(timezone.utc):
                raise api_error(410, "PAIRING_EXPIRED", "Pairing code has expired")
            if not hmac.compare_digest(pairing["secret_hash"], secret_hash):
                raise api_error(403, "PAIRING_CODE_INVALID", "Pairing code is invalid")
            station_id = pairing["station_id"]
            registry = self.station_registry[station_id]
            if registry.get("owner_uid") and registry["owner_uid"] != uid:
                raise api_error(409, "STATION_ALREADY_CLAIMED", "Station already has an owner")
            stations = self.station_projections.setdefault(uid, {})
            if station_id not in stations and sum(item.get("active", True) for item in stations.values()) >= max_stations:
                raise api_error(403, "STATION_LIMIT_REACHED", f"Maximum {max_stations} active stations")
            registry["owner_uid"] = uid
            pairing["claimed_at"] = datetime.now(timezone.utc)
            projection = {
                "name": registry["name"],
                "platform": registry["platform"],
                "active": True,
                "online": False,
                "capture_state": "idle",
                "desired_state": registry["desired_state"],
                "observed_generation": 0,
                "session_id": "",
                "sequence": 0,
            }
            stations[station_id] = projection
            return self._station(station_id, projection)

    def check_pairing_claim_rate(self, uid: str, pairing_id: str, limit: int = 10) -> None:
        with self.lock:
            key = (uid, pairing_id, int(time.time() // 60))
            count = self.station_pairing_attempts.get(key, 0)
            if count >= limit:
                raise api_error(429, "RATE_LIMITED", "Too many pairing attempts")
            self.station_pairing_attempts[key] = count + 1

    def provision_station(self, request: StationProvisionRequest, setup_id: str) -> dict:
        with self.lock:
            indexed_station = self.station_activation_index.get(setup_id)
            if indexed_station and indexed_station != request.station_id:
                raise api_error(409, "SETUP_ID_CONFLICT", "Setup ID is already registered")
            current = self.station_registry.get(request.station_id)
            if current:
                if current.get("public_key") != request.public_key:
                    raise api_error(409, "STATION_ID_CONFLICT", "Station ID is already registered")
                if current.get("activation_hash") not in {None, request.activation_hash}:
                    raise api_error(409, "ACTIVATION_CONFLICT", "Station activation is already configured")
                existing_setup_id = current.get("setup_id")
                if existing_setup_id:
                    return {
                        "station_id": request.station_id,
                        "setup_id": existing_setup_id,
                        "state": "claimed" if current.get("owner_uid") else "provisioned",
                    }
            registry = {
                **(current or {}),
                **request.model_dump(exclude={"station_id", "activation_hash", "activation_version"}),
                "station_id": request.station_id,
                "active": (current or {}).get("active", True),
                "owner_uid": (current or {}).get("owner_uid"),
                "desired_state": (current or {}).get("desired_state", StationDesiredState().model_dump()),
                "observed_generation": (current or {}).get("observed_generation", 0),
                "setup_id": setup_id,
                "activation_hash": request.activation_hash,
                "activation_version": request.activation_version,
                "activation_claimed_at": (current or {}).get("activation_claimed_at"),
                "provisioned": True,
            }
            self.station_registry[request.station_id] = registry
            self.station_activation_index[setup_id] = request.station_id
            return {
                "station_id": request.station_id,
                "setup_id": setup_id,
                "state": "claimed" if registry.get("owner_uid") else "provisioned",
            }

    def claim_station_activation(
        self, uid: str, setup_id: str, activation_code: str, max_stations: int
    ) -> Station:
        with self.lock:
            station_id = self.station_activation_index.get(setup_id)
            registry = self.station_registry.get(station_id or "")
            activation_hash = hashlib.sha256(
                f"{station_id}:{activation_code}".encode("utf-8")
            ).hexdigest()
            if not registry or not hmac.compare_digest(
                str(registry.get("activation_hash", "")), activation_hash
            ):
                raise api_error(403, "ACTIVATION_INVALID", "Activation is invalid or unavailable")
            if not registry.get("active", True):
                raise api_error(403, "STATION_REVOKED", "Station access has been revoked")
            owner_uid = registry.get("owner_uid")
            if owner_uid and owner_uid != uid:
                raise api_error(409, "STATION_ALREADY_CLAIMED", "Station already has an owner")
            stations = self.station_projections.setdefault(uid, {})
            if station_id not in stations and sum(
                item.get("active", True) for item in stations.values()
            ) >= max_stations:
                raise api_error(403, "STATION_LIMIT_REACHED", f"Maximum {max_stations} active stations")
            if owner_uid == uid and station_id in stations:
                return self._station(station_id, stations[station_id])
            registry["owner_uid"] = uid
            registry["activation_claimed_at"] = datetime.now(timezone.utc)
            projection = {
                "name": registry["name"],
                "platform": registry["platform"],
                "active": True,
                "online": False,
                "capture_state": "idle",
                "desired_state": registry["desired_state"],
                "observed_generation": 0,
                "session_id": "",
                "sequence": 0,
            }
            stations[station_id] = projection
            return self._station(station_id, projection)

    def check_activation_claim_rate(
        self, uid: str, setup_id: str, client_ip: str, limit: int = 5
    ) -> None:
        with self.lock:
            minute = int(time.time() // 60)
            dimensions = (
                ("uid", uid, 10),
                ("setup", setup_id, limit),
                ("ip", client_ip, 30),
            )
            for dimension, value, dimension_limit in dimensions:
                count = self.station_activation_attempts.get((dimension, value, minute), 0)
                if count >= dimension_limit:
                    raise api_error(429, "RATE_LIMITED", "Too many activation attempts")
            for dimension, value, _dimension_limit in dimensions:
                key = (dimension, value, minute)
                self.station_activation_attempts[key] = self.station_activation_attempts.get(key, 0) + 1

    def list_stations(self, uid: str) -> list[Station]:
        return [self._station(key, value) for key, value in self.station_projections.get(uid, {}).items()]

    def get_station_registry(self, station_id: str) -> dict | None:
        return self.station_registry.get(station_id)

    def revoke_station(self, uid: str, station_id: str) -> None:
        with self.lock:
            registry = self.station_registry.get(station_id)
            if not registry or registry.get("owner_uid") != uid:
                raise api_error(404, "STATION_NOT_FOUND", "Station was not found")
            registry["active"] = False
            self.station_projections[uid][station_id].update({"active": False, "online": False})

    def update_station_desired_state(self, uid: str, station_id: str, updates: dict) -> StationDesiredState:
        with self.lock:
            registry = self.station_registry.get(station_id)
            if not registry or registry.get("owner_uid") != uid:
                raise api_error(404, "STATION_NOT_FOUND", "Station was not found")
            if not registry.get("active", True):
                raise api_error(403, "STATION_REVOKED", "Station access has been revoked")
            desired = StationDesiredState.model_validate(registry.get("desired_state") or {})
            data = desired.model_dump()
            if updates.pop("retry_generation_increment", False):
                data["retry_generation"] = desired.retry_generation + 1
            data.update({key: value for key, value in updates.items() if value is not None})
            data["generation"] = desired.generation + 1
            value = StationDesiredState.model_validate(data)
            registry["desired_state"] = value.model_dump()
            self.station_projections[uid][station_id]["desired_state"] = value.model_dump()
            return value

    def heartbeat_station(self, station_id: str, heartbeat: StationHeartbeat) -> None:
        with self.lock:
            registry = self.station_registry.get(station_id)
            if not registry or not registry.get("owner_uid"):
                raise api_error(403, "STATION_NOT_PAIRED", "Station has not been paired")
            now = datetime.now(timezone.utc)
            values = {
                "online": True,
                "capture_state": heartbeat.capture_state,
                "session_id": heartbeat.session_id,
                "sequence": heartbeat.sequence,
                "observed_generation": heartbeat.observed_generation,
                "target_language": heartbeat.target_language,
                "last_error": heartbeat.error,
                "last_seen_at": now,
            }
            registry.update(values)
            self.station_projections[registry["owner_uid"]][station_id].update(values)

    def consume_station_request(self, station_id: str, request_id: str, expires_at: datetime) -> None:
        del expires_at
        with self.lock:
            key = (station_id, request_id)
            if key in self.station_nonces:
                raise api_error(409, "REPLAY_DETECTED", "Station request has already been used")
            self.station_nonces.add(key)

    def publish_station_result(self, uid: str, station_id: str, response: dict) -> None:
        key = (uid, station_id, response["session_id"], response["request_id"])
        self.station_results[key] = dict(response)

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
