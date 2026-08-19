from __future__ import annotations

import hashlib
import logging
import secrets
import time
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from google.api_core.exceptions import Aborted
from google.cloud import firestore

from services.prana_api.audio import validate_wav
from services.prana_api.auth import (
    FirebaseSession,
    Identity,
    require_firebase_session,
    require_identity,
)
from services.prana_api.config import get_settings
from services.prana_api.errors import api_error
from services.prana_api.google_services import (
    CloudStorageArchive,
    GeminiProcessor,
    station_audio_filename,
    tx_date_path,
)
from services.prana_api.tx_audio import (
    MAX_TX_OUTPUT_SECONDS,
    CloudTxSynthesizer,
    wav_duration_seconds,
)
from services.prana_api.timezones import (
    country_catalog,
    country_timezones,
    load_timezone,
    resolve_timezone,
)
from services.prana_api.tx_repository import FirestoreTxRepository
from services.prana_api.google_auth import (
    AuthRateLimiter,
    FirestoreAuthRateLimiter,
    GoogleAuthBroker,
)
from services.prana_api.models import (
    Device,
    DeviceRegisterRequest,
    FirebaseSessionResponse,
    GoogleAuthorizationRequest,
    MeResponse,
    Plan,
    PlanSelectionRequest,
    ProcessingResponse,
    Station,
    StationActivationClaimRequest,
    StationCapabilities,
    StationClaimRequest,
    StationDesiredState,
    StationDesiredStatePatch,
    StationHeartbeat,
    StationHistoryDay,
    StationHistoryPage,
    StationPairingRequest,
    StationPairingResponse,
    StationProvisionRequest,
    StationProvisionResponse,
    CountryOption,
    UserSettingsPatch,
    TxDraft,
    TxConfirmRequest,
    TxHistoryPage,
    TxJob,
    TxJobUpdate,
)
from services.prana_api.repository import FirestoreRepository, Repository
from services.prana_api.security import (
    body_hash,
    canonical_request,
    canonical_station_request,
    idempotency_hash,
    station_payload_hash,
    verify_device_signature,
    verify_timestamp,
)

app = FastAPI(title="PRANA ELEX API", version="1.2.0", docs_url=None, redoc_url=None)
logger = logging.getLogger(__name__)


@app.exception_handler(Aborted)
async def firestore_contention(_request, _exc):
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "2"},
        content={
            "detail": {
                "code": "SERVICE_BUSY",
                "message": "The service is busy; retry this request",
                "retry_after": 2,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(_request, exc):
    # Do not serialize request bodies, audio, transcripts, tokens or provider errors.
    return JSONResponse(status_code=500, content={"detail": {"code": "INTERNAL_ERROR", "message": "Request failed"}})


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    return FirestoreRepository(
        settings.google_cloud_project,
        settings.global_daily_audio_seconds,
        settings.global_monthly_audio_seconds,
    )


@lru_cache
def get_processor() -> GeminiProcessor:
    return GeminiProcessor(get_settings())


@lru_cache
def get_archive() -> CloudStorageArchive:
    return CloudStorageArchive(get_settings())


@lru_cache
def get_tx_synthesizer() -> CloudTxSynthesizer:
    return CloudTxSynthesizer(get_settings().google_cloud_project)


@lru_cache
def get_tx_repository():
    return FirestoreTxRepository(get_settings().google_cloud_project)


@lru_cache
def get_google_auth_broker() -> GoogleAuthBroker:
    return GoogleAuthBroker(get_settings())


@lru_cache
def get_google_auth_limiter() -> AuthRateLimiter:
    return AuthRateLimiter(get_settings().google_auth_instance_requests_per_minute)


@lru_cache
def get_google_auth_global_limiter() -> FirestoreAuthRateLimiter:
    settings = get_settings()
    db = firestore.Client(project=settings.google_cloud_project or None)
    return FirestoreAuthRateLimiter(
        db,
        settings.google_auth_global_requests_per_minute,
    )


def enforce_google_auth_rate() -> None:
    get_google_auth_limiter().check()
    get_google_auth_global_limiter().check()


def verified_account(identity: Identity, repo: Repository):
    account = repo.sync_identity(identity.uid, identity.email, identity.email_verified)
    if not account.email_verified:
        raise api_error(403, "EMAIL_NOT_VERIFIED", "Verify your email before using PRANA ELEX")
    return account


def active_account(identity: Identity, repo: Repository):
    account = verified_account(identity, repo)
    if not account.subscription_active or not account.plan_id:
        raise api_error(403, "SUBSCRIPTION_INACTIVE", "Subscription is not active")
    return account, repo.get_plan(account.plan_id)


def _pairing_hash(pairing_id: str, code: str) -> str:
    return hashlib.sha256(f"{pairing_id}:{code}".encode("utf-8")).hexdigest()


def _activation_hash(station_id: str, code: str) -> str:
    return hashlib.sha256(f"{station_id}:{code}".encode("utf-8")).hexdigest()


def _validate_request_id(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise api_error(422, "INVALID_REQUEST", "X-Request-ID must be a UUID") from exc


def _history_timezone(offset_minutes: int) -> timezone:
    if offset_minutes < -840 or offset_minutes > 840:
        raise api_error(
            422,
            "INVALID_TIMEZONE",
            "Timezone offset must be between -840 and 840 minutes",
        )
    return timezone(timedelta(minutes=offset_minutes))


def _account_timezone(account) -> ZoneInfo:
    """Timezone used to lay out this owner's storage folders."""
    stored = getattr(account, "timezone", "") or ""
    return resolve_timezone(stored, get_settings().default_timezone)


def _fan_out_station_timezone(repo: Repository, uid: str, timezone_name: str) -> None:
    """Push the owner's timezone to every Station they own.

    Best effort per Station: one failure must not abandon the rest, and the
    setting is already persisted on the account by the time we get here.
    """
    for station in repo.list_stations(uid):
        try:
            repo.update_station_desired_state(
                uid, station.station_id, {"timezone": timezone_name}
            )
        except Exception:
            logger.exception(
                "Could not fan out timezone to Station",
                extra={"station_id": station.station_id},
            )


def _seed_station_timezone(repo: Repository, account, station: Station) -> Station:
    """Give a freshly claimed Station its owner's timezone.

    Without this a Station claimed after the owner picked a country would keep
    using its own system clock until the next settings change.
    """
    timezone_name = getattr(account, "timezone", "") or ""
    if not timezone_name:
        return station
    try:
        desired = repo.update_station_desired_state(
            account.uid, station.station_id, {"timezone": timezone_name}
        )
    except Exception:
        logger.exception(
            "Could not seed timezone on claimed Station",
            extra={"station_id": station.station_id},
        )
        return station
    return station.model_copy(update={"desired_state": desired})


def _record_timestamp(value: dict) -> datetime | None:
    """Return the record's instant, or None when it carries no usable one.

    RX results store it as "timestamp"; TX jobs store it as "created_at".
    """
    for key in ("timestamp", "created_at"):
        candidate = value.get(key)
        if isinstance(candidate, datetime):
            return (
                candidate.replace(tzinfo=timezone.utc)
                if candidate.tzinfo is None
                else candidate
            )
        if isinstance(candidate, str):
            try:
                parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            except ValueError:
                continue
            return (
                parsed.replace(tzinfo=timezone.utc)
                if parsed.tzinfo is None
                else parsed
            )
    return None


def _history_timestamp(value: dict) -> datetime:
    """Sort/group key for history listings.

    Falls back instead of raising: this runs per record inside grouping loops,
    so one malformed document must not fail the whole history page.
    """
    timestamp = _record_timestamp(value)
    if timestamp is None:
        logger.warning(
            "History record has no usable timestamp",
            extra={
                "record_id": str(value.get("id") or ""),
                "station_id": str(value.get("station_id") or ""),
            },
        )
        return datetime.min.replace(tzinfo=timezone.utc)
    return timestamp


def _history_unlocked(history_date: date, plan: Plan, local_today: date) -> bool:
    return history_date + timedelta(days=plan.history_unlock_delay_days) <= local_today


def _station_history_values(
    repo: Repository,
    uid: str,
    station_id: str,
) -> list[dict]:
    unique: dict[str, dict] = {}
    for value in repo.list_station_history_results(uid, station_id):
        request_id = str(value.get("request_id") or "")
        key = request_id or (
            f"{value.get('session_id', '')}:{value.get('sequence', 0)}:"
            f"{_history_timestamp(value).isoformat()}"
        )
        unique[key] = value
    return sorted(
        unique.values(),
        key=lambda item: (
            _history_timestamp(item),
            int(item.get("sequence") or 0),
            str(item.get("request_id") or ""),
        ),
    )


def _authenticate_station_request(
    *,
    station_id: str,
    method: str,
    path: str,
    request_id: str,
    request_timestamp: str,
    signature: str,
    payload: dict,
    repo: Repository,
) -> dict:
    settings = get_settings()
    _validate_request_id(request_id)
    verify_timestamp(request_timestamp, settings.signature_clock_skew_seconds)
    station = repo.get_station_registry(station_id)
    if not station:
        raise api_error(403, "STATION_NOT_PAIRED", "Station has not been paired")
    if not station.get("active", True):
        raise api_error(403, "STATION_REVOKED", "Station is not active")
    verify_device_signature(
        station["public_key"],
        signature,
        canonical_station_request(
            method,
            path,
            request_id,
            request_timestamp,
            station_payload_hash(payload),
        ),
    )
    repo.consume_station_request(
        station_id,
        request_id,
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    if not station.get("owner_uid"):
        raise api_error(403, "STATION_NOT_PAIRED", "Station has not been paired")
    return station


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/auth/google/exchange", response_model=FirebaseSessionResponse)
def exchange_google_session(
    authorization: GoogleAuthorizationRequest,
    _rate_limit: None = Depends(enforce_google_auth_rate),
    broker: GoogleAuthBroker = Depends(get_google_auth_broker),
):
    return broker.exchange(authorization)


@app.post("/v1/auth/google/link", response_model=FirebaseSessionResponse)
def link_google_session(
    authorization: GoogleAuthorizationRequest,
    _rate_limit: None = Depends(enforce_google_auth_rate),
    session: FirebaseSession = Depends(require_firebase_session),
    broker: GoogleAuthBroker = Depends(get_google_auth_broker),
):
    return broker.exchange(
        authorization,
        firebase_id_token=session.id_token,
        expected_email=session.identity.email,
    )


@app.get("/v1/me", response_model=MeResponse)
def me(identity: Identity = Depends(require_identity), repo: Repository = Depends(get_repository)):
    account = repo.sync_identity(identity.uid, identity.email, identity.email_verified)
    usage = None
    plan = None
    if account.plan_id:
        plan = repo.get_plan(account.plan_id)
        usage = repo.get_usage(identity.uid, plan)
    entitlements = {
        "live_log_limit": plan.live_log_limit if plan else 10,
        "history_unlock_delay_days": (
            plan.history_unlock_delay_days if plan else 1
        ),
        "max_concurrency": plan.max_concurrency if plan else 2,
        "tx_max_recording_seconds": (
            plan.tx_max_recording_seconds if plan else 60
        ),
    }
    return MeResponse(
        **account.model_dump(),
        usage=usage,
        entitlements=entitlements,
    )


@app.get("/v1/countries", response_model=list[CountryOption])
def countries(
    response: Response,
    _identity: Identity = Depends(require_identity),
):
    response.headers["Cache-Control"] = "public, max-age=86400"
    return country_catalog()


@app.patch("/v1/me", response_model=MeResponse)
def update_me(
    request: UserSettingsPatch,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account = verified_account(identity, repo)
    country_code = request.country_code.upper()
    options = country_timezones(country_code)
    if not options:
        raise api_error(422, "INVALID_COUNTRY", "Country is not supported")
    timezone_name = request.timezone or options[0]
    if timezone_name not in options:
        raise api_error(
            422,
            "INVALID_TIMEZONE",
            "Timezone does not belong to the selected country",
        )
    if load_timezone(timezone_name) is None:
        raise api_error(422, "INVALID_TIMEZONE", "Timezone is not available")
    account = repo.update_user_region(account.uid, country_code, timezone_name)
    _fan_out_station_timezone(repo, account.uid, timezone_name)
    usage = None
    plan = None
    if account.plan_id:
        plan = repo.get_plan(account.plan_id)
        usage = repo.get_usage(account.uid, plan)
    return MeResponse(
        **account.model_dump(),
        usage=usage,
        entitlements={
            "live_log_limit": plan.live_log_limit if plan else 10,
            "history_unlock_delay_days": (
                plan.history_unlock_delay_days if plan else 1
            ),
            "max_concurrency": plan.max_concurrency if plan else 2,
            "tx_max_recording_seconds": (
                plan.tx_max_recording_seconds if plan else 60
            ),
        },
    )


@app.get("/v1/plans", response_model=list[Plan])
def plans(
    response: Response,
    _identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    response.headers["Cache-Control"] = "no-store"
    return repo.list_plans()


@app.post("/v1/subscription/select", response_model=MeResponse)
def select_subscription(
    request: PlanSelectionRequest,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account = verified_account(identity, repo)
    plan = repo.get_plan(request.plan_id)
    account = repo.select_plan(account.uid, plan)
    return MeResponse(
        **account.model_dump(),
        usage=repo.get_usage(account.uid, plan),
        entitlements={
            "live_log_limit": plan.live_log_limit,
            "history_unlock_delay_days": plan.history_unlock_delay_days,
            "max_concurrency": plan.max_concurrency,
            "tx_max_recording_seconds": plan.tx_max_recording_seconds,
        },
    )


@app.get("/v1/usage")
def usage(identity: Identity = Depends(require_identity), repo: Repository = Depends(get_repository)):
    account, plan = active_account(identity, repo)
    return repo.get_usage(account.uid, plan)


@app.get("/v1/devices")
def list_devices(identity: Identity = Depends(require_identity), repo: Repository = Depends(get_repository)):
    verified_account(identity, repo)
    return repo.list_devices(identity.uid)


@app.post("/v1/devices/register", response_model=Device)
def register_device(
    request: DeviceRegisterRequest,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    _account, plan = active_account(identity, repo)
    device = Device(id=request.device_id, uid=identity.uid, **request.model_dump(exclude={"device_id"}))
    return repo.register_device(identity.uid, device, plan.max_devices)


@app.get("/v1/devices/{device_id}", response_model=Device)
def get_device(
    device_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    verified_account(identity, repo)
    device = repo.get_device(identity.uid, device_id)
    if not device:
        raise api_error(404, "DEVICE_NOT_FOUND", "Device was not found")
    return device


@app.delete("/v1/devices/{device_id}", status_code=204)
def revoke_device(
    device_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    verified_account(identity, repo)
    repo.revoke_device(identity.uid, device_id)
    return Response(status_code=204)


@app.post("/v1/station-pairings", response_model=StationPairingResponse)
def create_station_pairing(
    request: StationPairingRequest,
    station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if station_id != request.station_id:
        raise api_error(422, "INVALID_REQUEST", "Station header and body do not match")
    _validate_request_id(request_id)
    verify_timestamp(request_timestamp, get_settings().signature_clock_skew_seconds)
    verify_device_signature(
        request.public_key,
        signature,
        canonical_station_request(
            "POST",
            "/v1/station-pairings",
            request_id,
            request_timestamp,
            station_payload_hash(request.model_dump()),
        ),
    )
    pairing_id = str(uuid.uuid4())
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    pairing_code = "".join(secrets.choice(alphabet) for _ in range(8))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    repo.create_station_pairing(
        request,
        pairing_id,
        _pairing_hash(pairing_id, pairing_code),
        expires_at,
    )
    repo.consume_station_request(
        station_id,
        request_id,
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    return StationPairingResponse(
        pairing_id=pairing_id,
        pairing_code=pairing_code,
        qr_payload=f"prana-elex:///pair?pairing_id={pairing_id}&code={pairing_code}",
        expires_at=expires_at,
    )


@app.post("/v1/station-provisions", response_model=StationProvisionResponse)
def provision_station(
    request: StationProvisionRequest,
    station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if station_id != request.station_id:
        raise api_error(422, "INVALID_REQUEST", "Station header and body do not match")
    _validate_request_id(request_id)
    verify_timestamp(request_timestamp, get_settings().signature_clock_skew_seconds)
    verify_device_signature(
        request.public_key,
        signature,
        canonical_station_request(
            "POST",
            "/v1/station-provisions",
            request_id,
            request_timestamp,
            station_payload_hash(request.model_dump()),
        ),
    )
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    value = None
    for _ in range(5):
        setup_id = "".join(secrets.choice(alphabet) for _ in range(10))
        try:
            value = repo.provision_station(request, setup_id)
            break
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if detail.get("code") != "SETUP_ID_CONFLICT":
                raise
    if value is None:
        raise api_error(503, "SETUP_ID_UNAVAILABLE", "Could not allocate a setup ID")
    repo.consume_station_request(
        station_id,
        request_id,
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    return StationProvisionResponse.model_validate(value)


@app.post("/v1/station-activations/claim", response_model=Station)
def claim_station_activation(
    request: StationActivationClaimRequest,
    http_request: Request,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    _account, plan = active_account(identity, repo)
    client_ip = http_request.client.host if http_request.client else "unknown"
    repo.check_activation_claim_rate(identity.uid, request.setup_id, client_ip)
    station = repo.claim_station_activation(
        identity.uid,
        request.setup_id,
        request.activation_code,
        plan.max_stations,
    )
    return _seed_station_timezone(repo, _account, station)


@app.post("/v1/station-pairings/{pairing_id}/claim", response_model=Station)
def claim_station(
    pairing_id: str,
    request: StationClaimRequest,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    _account, plan = active_account(identity, repo)
    repo.check_pairing_claim_rate(identity.uid, pairing_id)
    station = repo.claim_station(
        identity.uid,
        pairing_id,
        _pairing_hash(pairing_id, request.pairing_code.upper()),
        plan.max_stations,
    )
    return _seed_station_timezone(repo, _account, station)


@app.get("/v1/stations", response_model=list[Station])
def list_stations(
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    _account, plan = active_account(identity, repo)
    return repo.list_stations(identity.uid)


@app.get(
    "/v1/stations/{station_id}/history/days",
    response_model=list[StationHistoryDay],
)
def list_station_history_days(
    station_id: str,
    timezone_offset_minutes: int = 0,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account, plan = active_account(identity, repo)
    local_timezone = _history_timezone(timezone_offset_minutes)
    local_today = datetime.now(timezone.utc).astimezone(local_timezone).date()
    grouped: dict[date, list[datetime]] = {}
    for value in _station_history_values(repo, account.uid, station_id):
        timestamp = _history_timestamp(value)
        local_date = timestamp.astimezone(local_timezone).date()
        grouped.setdefault(local_date, []).append(timestamp)
    return [
        StationHistoryDay(
            date=history_date,
            result_count=len(timestamps),
            first_result_at=min(timestamps),
            last_result_at=max(timestamps),
            locked=not _history_unlocked(history_date, plan, local_today),
        )
        for history_date, timestamps in sorted(
            grouped.items(),
            reverse=True,
        )
    ]


@app.get(
    "/v1/stations/{station_id}/history/days/{history_date}/results",
    response_model=StationHistoryPage,
)
def list_station_history_day_results(
    station_id: str,
    history_date: date,
    timezone_offset_minutes: int = 0,
    limit: int = 200,
    cursor: str | None = None,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account, plan = active_account(identity, repo)
    local_timezone = _history_timezone(timezone_offset_minutes)
    local_today = datetime.now(timezone.utc).astimezone(local_timezone).date()
    if not _history_unlocked(history_date, plan, local_today):
        raise api_error(
            403,
            "HISTORY_LOCKED",
            "Full history is not available until the configured unlock date",
        )
    safe_limit = max(1, min(limit, 1000))
    try:
        offset = int(cursor or "0")
    except ValueError as exc:
        raise api_error(422, "INVALID_CURSOR", "History cursor is invalid") from exc
    if offset < 0:
        raise api_error(422, "INVALID_CURSOR", "History cursor is invalid")

    values = [
        value
        for value in _station_history_values(repo, account.uid, station_id)
        if _history_timestamp(value).astimezone(local_timezone).date()
        == history_date
    ]
    page = values[offset : offset + safe_limit]
    next_offset = offset + len(page)
    return StationHistoryPage(
        items=page,
        next_cursor=str(next_offset) if next_offset < len(values) else None,
    )


@app.get(
    "/v1/stations/{station_id}/live/results",
    response_model=list[ProcessingResponse],
)
def list_station_live_results(
    station_id: str,
    timezone_offset_minutes: int = 0,
    limit: int = 1000,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account, plan = active_account(identity, repo)
    local_timezone = _history_timezone(timezone_offset_minutes)
    local_now = datetime.now(timezone.utc).astimezone(local_timezone)
    local_start = datetime.combine(local_now.date(), datetime.min.time(), local_timezone)
    start_at = local_start.astimezone(timezone.utc)
    end_at = (local_start + timedelta(days=1)).astimezone(timezone.utc)
    safe_limit = max(1, min(limit, 1000))
    entitled_limit = (
        safe_limit
        if plan.live_log_limit == 0
        else min(safe_limit, plan.live_log_limit)
    )
    return repo.list_station_live_results(
        account.uid,
        station_id,
        start_at,
        end_at,
        entitled_limit,
    )


@app.get(
    "/v1/stations/{station_id}/sessions/{session_id}/results",
    response_model=list[ProcessingResponse],
)
def list_station_results(
    station_id: str,
    session_id: str,
    limit: int = 1000,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    account, plan = active_account(identity, repo)
    safe_limit = max(1, min(limit, 1000))
    return repo.list_station_results(
        account.uid,
        station_id,
        session_id,
        plan,
        safe_limit,
    )


@app.get(
    "/v1/stations/{station_id}/sessions/{session_id}/results/{request_id}/audio"
)
def get_station_result_audio(
    station_id: str,
    session_id: str,
    request_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    result = repo.get_station_result(
        identity.uid,
        station_id,
        session_id,
        request_id,
    )
    object_name = (result or {}).get("_source_audio_object")
    if not object_name:
        raise api_error(
            404,
            "SOURCE_AUDIO_UNAVAILABLE",
            "Source audio is not available for this result",
        )
    audio = get_archive().download_audio(str(object_name))
    if audio is None:
        raise api_error(
            404,
            "SOURCE_AUDIO_UNAVAILABLE",
            "Source audio is not available for this result",
        )
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/v1/stations/{station_id}", status_code=204)
def release_station(
    station_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    verified_account(identity, repo)
    repo.release_station(identity.uid, station_id)
    return Response(status_code=204)


@app.patch("/v1/stations/{station_id}/desired-state", response_model=StationDesiredState)
def update_station_desired_state(
    station_id: str,
    request: StationDesiredStatePatch,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    active_account(identity, repo)
    updates = request.model_dump(
        exclude={"retry", "refresh_capabilities"}, exclude_none=True
    )
    if request.retry:
        updates["retry_generation_increment"] = True
    if request.refresh_capabilities:
        updates["capability_refresh_increment"] = True
    if not updates:
        raise api_error(422, "INVALID_REQUEST", "No desired state change was supplied")
    return repo.update_station_desired_state(identity.uid, station_id, updates)


@app.get("/v1/stations/{station_id}/desired-state", response_model=StationDesiredState)
def get_station_desired_state(
    station_id: str,
    signed_station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    station = _authenticate_station_request(
        station_id=station_id,
        method="GET",
        path=f"/v1/stations/{station_id}/desired-state",
        request_id=request_id,
        request_timestamp=request_timestamp,
        signature=signature,
        payload={},
        repo=repo,
    )
    return StationDesiredState.model_validate(station.get("desired_state") or {})


@app.get("/v1/stations/{station_id}/profile")
def get_station_profile(
    station_id: str,
    signed_station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    path = f"/v1/stations/{station_id}/profile"
    station = _authenticate_station_request(
        station_id=station_id,
        method="GET",
        path=path,
        request_id=request_id,
        request_timestamp=request_timestamp,
        signature=signature,
        payload={},
        repo=repo,
    )
    account = repo.get_account(station["owner_uid"])
    if not account or not account.subscription_active or not account.plan_id:
        raise api_error(
            403,
            "SUBSCRIPTION_INACTIVE",
            "Station owner's subscription is not active",
        )
    plan = repo.get_plan(account.plan_id)
    return {
        "status": "active",
        "station_id": station_id,
        "entitlements": {"max_concurrency": plan.max_concurrency},
    }


@app.post("/v1/stations/{station_id}/heartbeat", status_code=204)
def station_heartbeat(
    station_id: str,
    request: StationHeartbeat,
    signed_station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    _authenticate_station_request(
        station_id=station_id,
        method="POST",
        path=f"/v1/stations/{station_id}/heartbeat",
        request_id=request_id,
        request_timestamp=request_timestamp,
        signature=signature,
        payload=request.model_dump(exclude_unset=True),
        repo=repo,
    )
    repo.heartbeat_station(station_id, request)
    return Response(status_code=204)


@app.post("/v1/stations/{station_id}/capabilities", status_code=204)
def station_capabilities(
    station_id: str,
    request: StationCapabilities,
    signed_station_id: str = Header(alias="X-Station-ID"),
    request_id: str = Header(alias="X-Request-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    path = f"/v1/stations/{station_id}/capabilities"
    _authenticate_station_request(
        station_id=station_id,
        method="POST",
        path=path,
        request_id=request_id,
        request_timestamp=request_timestamp,
        signature=signature,
        payload=request.model_dump(),
        repo=repo,
    )
    repo.update_station_capabilities(station_id, request)
    return Response(status_code=204)


@app.post("/v1/audio/process", response_model=ProcessingResponse)
def process_audio(
    audio: UploadFile = File(),
    target_language: str = Form(),
    session_id: str = Form(),
    sequence: int = Form(),
    request_id: str = Form(),
    device_id: str = Header(alias="X-Device-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    settings = get_settings()
    if target_language not in {"vi", "en", "zh", "ja", "ko"}:
        raise api_error(422, "INVALID_REQUEST", "Unsupported target language")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id) or sequence < 0:
        raise api_error(422, "INVALID_REQUEST", "Invalid session or sequence")
    try:
        uuid.UUID(request_id)
    except ValueError as exc:
        raise api_error(422, "INVALID_REQUEST", "request_id must be a UUID") from exc
    account, plan = active_account(identity, repo)
    data = audio.file.read(settings.max_audio_bytes + 1)
    info = validate_wav(data, settings.max_audio_bytes, settings.max_audio_seconds)
    digest = body_hash(data)
    verify_timestamp(request_timestamp, settings.signature_clock_skew_seconds)
    device = repo.get_device(identity.uid, device_id)
    if not device or not device.active:
        raise api_error(403, "DEVICE_REVOKED", "Device is not active")
    verify_device_signature(
        device.public_key,
        signature,
        canonical_request(request_id, request_timestamp, digest, target_language, session_id, sequence),
    )

    request_hash = idempotency_hash(digest, target_language, session_id, sequence)
    reservation = repo.reserve(identity.uid, plan, request_id, request_hash, info.seconds)
    if reservation.state == "completed":
        return ProcessingResponse.model_validate(reservation.cached_response)

    started = time.perf_counter()
    try:
        model_result = get_processor().process(data, target_language, session_id, sequence, request_id)
    except Exception:
        repo.settle_failure(
            identity.uid,
            request_id,
            "PROVIDER_ERROR",
            {"audio_seconds": info.seconds, "latency_ms": round((time.perf_counter() - started) * 1000, 1)},
        )
        raise api_error(503, "SERVICE_USAGE_LIMIT_REACHED", "Translation service is temporarily unavailable")
    processed_response = model_result.response.model_copy(
        update={"target_language": target_language}
    )
    response = processed_response.model_dump(mode="json")
    metrics = dict(model_result.metrics)
    metrics.update({"audio_seconds": info.seconds, "request_id": request_id})
    try:
        get_archive().archive(identity.uid, session_id, request_id, data, response)
    except Exception:
        logger.exception(
            "Cloud archive failed",
            extra={"request_id": request_id, "session_id": session_id},
        )
        metrics["archive_failed"] = True
        repo.settle_failure(identity.uid, request_id, "ARCHIVE_FAILED", metrics)
        raise api_error(
            503,
            "SERVICE_BUSY",
            "Result was processed but cloud archival is temporarily unavailable",
            retry_after=2,
        )
    repo.settle_success(identity.uid, request_id, response, metrics)
    return processed_response


@app.post("/v1/stations/{station_id}/audio/process", response_model=ProcessingResponse)
def process_station_audio(
    station_id: str,
    audio: UploadFile = File(),
    target_language: str = Form(),
    session_id: str = Form(),
    sequence: int = Form(),
    request_id: str = Form(),
    signed_station_id: str = Header(alias="X-Station-ID"),
    request_timestamp: str = Header(alias="X-Timestamp"),
    signature: str = Header(alias="X-Signature"),
    repo: Repository = Depends(get_repository),
):
    settings = get_settings()
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    if target_language not in {"vi", "en", "zh", "ja", "ko"}:
        raise api_error(422, "INVALID_REQUEST", "Unsupported target language")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id) or sequence < 0:
        raise api_error(422, "INVALID_REQUEST", "Invalid session or sequence")
    try:
        uuid.UUID(request_id)
    except ValueError as exc:
        raise api_error(422, "INVALID_REQUEST", "request_id must be a UUID") from exc

    data = audio.file.read(settings.max_audio_bytes + 1)
    info = validate_wav(data, settings.max_audio_bytes, settings.max_audio_seconds)
    digest = body_hash(data)
    verify_timestamp(request_timestamp, settings.signature_clock_skew_seconds)
    station = repo.get_station_registry(station_id)
    if not station or not station.get("active", True):
        raise api_error(403, "STATION_REVOKED", "Station is not active")
    owner_uid = station.get("owner_uid")
    if not owner_uid:
        raise api_error(403, "STATION_NOT_PAIRED", "Station has not been paired")
    stored_audio_filename, stored_date_path = station_audio_filename(
        audio.filename,
        sequence,
    )
    verify_device_signature(
        station["public_key"],
        signature,
        canonical_request(
            request_id,
            request_timestamp,
            digest,
            target_language,
            session_id,
            sequence,
        ),
    )
    account = repo.get_account(owner_uid)
    if not account or not account.subscription_active or not account.plan_id:
        raise api_error(403, "SUBSCRIPTION_INACTIVE", "Station owner's subscription is not active")
    plan = repo.get_plan(account.plan_id)
    request_hash = idempotency_hash(digest, target_language, session_id, sequence)
    reservation = repo.reserve(owner_uid, plan, request_id, request_hash, info.seconds)
    if reservation.state == "completed":
        # Projection writes are idempotent. Repeating this heals a transient
        # Firestore publication failure without charging or invoking Gemini again.
        try:
            repo.publish_station_result(
                owner_uid,
                station_id,
                reservation.cached_response or {},
            )
        except Exception:
            raise api_error(
                503,
                "SERVICE_BUSY",
                "Result synchronization is temporarily unavailable",
                retry_after=2,
            )
        return ProcessingResponse.model_validate(reservation.cached_response)

    started = time.perf_counter()
    try:
        model_result = get_processor().process(
            data, target_language, session_id, sequence, request_id
        )
    except Exception:
        repo.settle_failure(
            owner_uid,
            request_id,
            "PROVIDER_ERROR",
            {
                "audio_seconds": info.seconds,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "station_id": station_id,
            },
        )
        raise api_error(
            503,
            "SERVICE_USAGE_LIMIT_REACHED",
            "Translation service is temporarily unavailable",
        )

    processed_response = model_result.response.model_copy(
        update={
            "target_language": target_language,
            "audio_file": stored_audio_filename,
        }
    )
    response = {
        **processed_response.model_dump(mode="json"),
        "request_id": request_id,
        "station_id": station_id,
    }
    metrics = dict(model_result.metrics)
    metrics.update(
        {
            "audio_seconds": info.seconds,
            "request_id": request_id,
            "station_id": station_id,
        }
    )
    try:
        audio_object = get_archive().archive_station(
            station_id,
            str(station.get("name") or ""),
            stored_audio_filename,
            stored_date_path,
            data,
            response,
        )
        if audio_object:
            response["_source_audio_object"] = audio_object
    except Exception:
        logger.exception(
            "Station cloud archive failed",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "station_id": station_id,
            },
        )
        metrics["archive_failed"] = True
        repo.settle_failure(owner_uid, request_id, "ARCHIVE_FAILED", metrics)
        raise api_error(
            503,
            "SERVICE_BUSY",
            "Result was processed but archival is temporarily unavailable",
            retry_after=2,
        )

    repo.settle_success(owner_uid, request_id, response, metrics)
    try:
        repo.publish_station_result(owner_uid, station_id, response)
    except Exception:
        raise api_error(
            503,
            "SERVICE_BUSY",
            "Result was processed but synchronization is temporarily unavailable",
            retry_after=2,
        )
    return ProcessingResponse.model_validate(response)


def _owned_tx_station(repo: Repository, uid: str, station_id: str) -> dict:
    station = repo.get_station_registry(station_id)
    if not station or station.get("owner_uid") != uid:
        raise api_error(404, "STATION_NOT_FOUND", "Station was not found")
    if not station.get("active", True):
        raise api_error(409, "STATION_REVOKED", "Station is inactive")
    return station


def _require_tx_running(station: dict) -> None:
    desired = station.get("desired_state") or {}
    if not bool(desired.get("running")):
        raise api_error(409, "TX_NOT_STARTED", "Start the Station before using TX")


def _require_tx_ready(station: dict) -> None:
    now = datetime.now(timezone.utc)
    last_seen = station.get("last_seen_at")
    if last_seen is None or last_seen <= now - timedelta(seconds=20):
        raise api_error(409, "STATION_OFFLINE", "Station is offline")
    if not bool(station.get("ptt_ready", True)):
        raise api_error(409, "PTT_UNAVAILABLE", "Station PTT is unavailable")


def _reconcile_stale_tx(station: dict, station_id: str, tx_repo) -> dict | None:
    now = datetime.now(timezone.utc)
    last_seen = station.get("last_seen_at")
    stale = last_seen is None or last_seen <= now - timedelta(seconds=20)
    return tx_repo.expire_stale_active(station_id, stale, now)


@app.post("/v1/stations/{station_id}/tx/drafts", response_model=TxDraft)
def create_tx_draft(
    station_id: str,
    audio: UploadFile = File(),
    target_language: str = Form(),
    request_id: str = Header(alias="X-Request-ID"),
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
    tx_repo=Depends(get_tx_repository),
):
    _validate_request_id(request_id)
    if target_language not in {"vi", "en", "zh", "ja", "ko"}:
        raise api_error(422, "INVALID_REQUEST", "Unsupported target language")
    _account, plan = active_account(identity, repo)
    station = _owned_tx_station(repo, identity.uid, station_id)
    _reconcile_stale_tx(station, station_id, tx_repo)
    _require_tx_running(station)
    _require_tx_ready(station)
    settings = get_settings()
    source = audio.file.read(settings.max_audio_bytes + 1)
    info = validate_wav(
        source,
        settings.max_audio_bytes,
        min(plan.tx_max_recording_seconds, settings.max_audio_seconds),
        too_long_code="TX_AUDIO_TOO_LONG",
    )
    if info.seconds < 0.3:
        raise api_error(422, "AUDIO_TOO_SHORT", "Hold to talk for at least 300 ms")
    created_at = datetime.now(timezone.utc)
    request_hash = hashlib.sha256(
        source + b"\0" + target_language.encode("ascii") + b"\0" + station_id.encode("ascii")
    ).hexdigest()
    reserved, created = tx_repo.reserve_processing(
        {
            "id": request_id,
            "uid": identity.uid,
            "station_id": station_id,
            "duration_ms": round(info.seconds * 1000),
            "target_language": target_language,
            "detected_language": "",
            "transcript": "",
            "translation": "",
            "translation_original": "",
            "translation_edited": False,
            "audio_filename": "",
            "output_available": False,
            "error": None,
            "attempt": 1,
            "retry_of": None,
            "created_at": created_at,
            "source_object": "",
            "output_object": "",
            "confirmed": False,
        },
        request_hash,
    )
    if not created:
        return TxDraft.model_validate(reserved)
    # created_at stays UTC in Firestore; only the stored filename and the date
    # folder derived from it follow the owner's timezone.
    local_created_at = created_at.astimezone(_account_timezone(_account))
    audio_filename = tx_repo.next_filename(station_id, local_created_at)
    date_path = tx_date_path(audio_filename, fallback=local_created_at)
    try:
        model = get_processor().process(
            source, target_language, f"tx-{request_id}", 0, request_id
        ).response
        if model.error:
            tx_repo.release_processing(request_id)
            raise api_error(422, "NO_SPEECH", model.error)
        metadata = {
            "detected_language": model.detected_language,
            "transcript": model.transcript_restored,
            "translation": model.translation,
            "translation_original": model.translation,
            "audio_filename": audio_filename,
        }
        source_object = get_archive().archive_tx_source(
            station_id,
            str(station.get("name") or ""),
            audio_filename,
            date_path,
            source,
        )
    except HTTPException:
        raise
    except Exception:
        tx_repo.release_processing(request_id)
        logger.exception("TX synthesis/archive failed", extra={"station_id": station_id, "tx_job_id": request_id})
        raise api_error(503, "TX_PROCESSING_FAILED", "TX audio could not be created")
    updates = {
        **metadata,
        "source_object": source_object,
    }
    return TxDraft.model_validate(tx_repo.complete_processing(request_id, updates))


@app.get("/v1/stations/{station_id}/tx/drafts/{job_id}", response_model=TxDraft)
def get_tx_draft(station_id: str, job_id: str, identity: Identity = Depends(require_identity),
                 repo: Repository = Depends(get_repository), tx_repo=Depends(get_tx_repository)):
    station = _owned_tx_station(repo, identity.uid, station_id)
    _reconcile_stale_tx(station, station_id, tx_repo)
    item = tx_repo.get(job_id)
    if not item or item.get("uid") != identity.uid or item.get("station_id") != station_id:
        raise api_error(404, "TX_NOT_FOUND", "TX draft was not found")
    return TxDraft.model_validate(item)


def _synthesize_tx_draft(item: dict, tx_repo, uid: str, station_id: str, station_name: str) -> TxDraft:
    try:
        output = get_tx_synthesizer().synthesize_with_over(
            item["translation"],
            item["target_language"],
        )
        if wav_duration_seconds(output) > MAX_TX_OUTPUT_SECONDS:
            tx_repo.fail_synthesis(
                uid, station_id, item["id"], "TX_OUTPUT_TOO_LONG"
            )
            raise api_error(
                422,
                "TX_OUTPUT_TOO_LONG",
                "TX audio exceeds the 120 second safety limit",
            )
        audio_filename = item["audio_filename"]
        output_object = get_archive().archive_tx_output(
            station_id,
            station_name,
            audio_filename,
            tx_date_path(
                audio_filename,
                fallback=_record_timestamp(item) or datetime.now(timezone.utc),
            ),
            output,
            {
                **{
                    key: value
                    for key, value in item.items()
                    if key not in {"uid", "source_object", "output_object"}
                },
                "status": "queued",
                "output_available": True,
            },
        )
        return TxDraft.model_validate(
            tx_repo.finish_confirm(uid, station_id, item["id"], output_object)
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "TX synthesis/archive failed",
            extra={"station_id": station_id, "tx_job_id": item.get("id")},
        )
        tx_repo.fail_synthesis(uid, station_id, item["id"], "TX_PROCESSING_FAILED")
        raise api_error(503, "TX_PROCESSING_FAILED", "TX audio could not be created")


@app.post("/v1/stations/{station_id}/tx/drafts/{job_id}/confirm", response_model=TxDraft)
def confirm_tx_draft(
    station_id: str,
    job_id: str,
    request: TxConfirmRequest,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
    tx_repo=Depends(get_tx_repository),
):
    station = _owned_tx_station(repo, identity.uid, station_id)
    _reconcile_stale_tx(station, station_id, tx_repo)
    _require_tx_running(station)
    _require_tx_ready(station)
    existing = tx_repo.get(job_id)
    if (
        existing
        and existing.get("uid") == identity.uid
        and existing.get("station_id") == station_id
        and existing.get("status") != "review_ready"
    ):
        if existing.get("translation") != request.translation:
            raise api_error(
                409,
                "TX_INVALID_STATE",
                "TX draft was already confirmed with different content",
            )
        return TxDraft.model_validate(existing)
    item = tx_repo.begin_confirm(
        identity.uid,
        station_id,
        job_id,
        request.translation,
    )
    return _synthesize_tx_draft(item, tx_repo, identity.uid, station_id, str(station.get("name") or ""))


@app.delete("/v1/stations/{station_id}/tx/drafts/{job_id}", status_code=204)
def cancel_tx_draft(station_id: str, job_id: str, identity: Identity = Depends(require_identity),
                    repo: Repository = Depends(get_repository), tx_repo=Depends(get_tx_repository)):
    _owned_tx_station(repo, identity.uid, station_id)
    tx_repo.cancel(identity.uid, station_id, job_id)
    return Response(status_code=204)


@app.post("/v1/stations/{station_id}/tx/drafts/{job_id}/retry", response_model=TxDraft)
def retry_tx_draft(station_id: str, job_id: str, identity: Identity = Depends(require_identity),
                   repo: Repository = Depends(get_repository), tx_repo=Depends(get_tx_repository)):
    station = _owned_tx_station(repo, identity.uid, station_id)
    _reconcile_stale_tx(station, station_id, tx_repo)
    _require_tx_running(station)
    _require_tx_ready(station)
    clone = tx_repo.retry(identity.uid, station_id, job_id, str(uuid.uuid4()))
    item = tx_repo.begin_confirm(
        identity.uid,
        station_id,
        clone["id"],
        clone["translation"],
    )
    if item.get("output_object"):
        return TxDraft.model_validate(
            tx_repo.finish_confirm(
                identity.uid,
                station_id,
                item["id"],
                item["output_object"],
            )
        )
    return _synthesize_tx_draft(item, tx_repo, identity.uid, station_id, str(station.get("name") or ""))


def _tx_history_values(tx_repo, uid: str, station_id: str) -> list[dict]:
    return tx_repo.history(uid, station_id)


@app.get("/v1/stations/{station_id}/tx/history/days", response_model=list[StationHistoryDay])
def list_tx_history_days(
    station_id: str,
    timezone_offset_minutes: int = 0,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
    tx_repo=Depends(get_tx_repository),
):
    account, plan = active_account(identity, repo)
    _owned_tx_station(repo, account.uid, station_id)
    local_timezone = _history_timezone(timezone_offset_minutes)
    local_today = datetime.now(timezone.utc).astimezone(local_timezone).date()
    grouped: dict[date, list[datetime]] = {}
    for value in _tx_history_values(tx_repo, account.uid, station_id):
        timestamp = _history_timestamp(value)
        grouped.setdefault(timestamp.astimezone(local_timezone).date(), []).append(timestamp)
    return [
        StationHistoryDay(
            date=history_date,
            result_count=len(timestamps),
            first_result_at=min(timestamps),
            last_result_at=max(timestamps),
            locked=not _history_unlocked(history_date, plan, local_today),
        )
        for history_date, timestamps in sorted(grouped.items(), reverse=True)
    ]


@app.get("/v1/stations/{station_id}/tx/history/days/{history_date}/jobs", response_model=TxHistoryPage)
def list_tx_history_day_jobs(
    station_id: str,
    history_date: date,
    timezone_offset_minutes: int = 0,
    limit: int = 200,
    cursor: str | None = None,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
    tx_repo=Depends(get_tx_repository),
):
    account, plan = active_account(identity, repo)
    _owned_tx_station(repo, account.uid, station_id)
    local_timezone = _history_timezone(timezone_offset_minutes)
    local_today = datetime.now(timezone.utc).astimezone(local_timezone).date()
    if not _history_unlocked(history_date, plan, local_today):
        raise api_error(403, "HISTORY_LOCKED", "Full history is not available until the configured unlock date")
    try:
        offset = int(cursor or "0")
    except ValueError as exc:
        raise api_error(422, "INVALID_CURSOR", "History cursor is invalid") from exc
    if offset < 0:
        raise api_error(422, "INVALID_CURSOR", "History cursor is invalid")
    values = [
        item
        for item in _tx_history_values(tx_repo, account.uid, station_id)
        if _history_timestamp(item).astimezone(local_timezone).date() == history_date
    ]
    safe_limit = max(1, min(limit, 1000))
    page = values[offset : offset + safe_limit]
    next_offset = offset + len(page)
    return TxHistoryPage(
        items=[TxDraft.model_validate(item) for item in page],
        next_cursor=str(next_offset) if next_offset < len(values) else None,
    )


@app.get("/v1/stations/{station_id}/tx/history/{job_id}/audio")
def get_tx_history_audio(
    station_id: str,
    job_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
    tx_repo=Depends(get_tx_repository),
):
    _owned_tx_station(repo, identity.uid, station_id)
    item = tx_repo.get(job_id)
    if not item or item.get("uid") != identity.uid or item.get("station_id") != station_id:
        raise api_error(404, "TX_NOT_FOUND", "TX job was not found")
    object_name = item.get("output_object")
    if not object_name:
        raise api_error(404, "TX_AUDIO_UNAVAILABLE", "TX audio is unavailable")
    audio = get_archive().download_audio(object_name)
    if audio is None:
        raise api_error(404, "TX_AUDIO_UNAVAILABLE", "TX audio is unavailable")
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})


def _signed_tx_station(station_id: str, method: str, path: str, request_id: str,
                       request_timestamp: str, signature: str, payload: dict, repo: Repository) -> dict:
    return _authenticate_station_request(
        station_id=station_id, method=method, path=path, request_id=request_id,
        request_timestamp=request_timestamp, signature=signature, payload=payload, repo=repo,
    )


@app.post("/v1/stations/{station_id}/tx/jobs/claim", response_model=TxJob | None)
def claim_tx_job(station_id: str, signed_station_id: str = Header(alias="X-Station-ID"),
                 request_id: str = Header(alias="X-Request-ID"), request_timestamp: str = Header(alias="X-Timestamp"),
                 signature: str = Header(alias="X-Signature"), repo: Repository = Depends(get_repository),
                 tx_repo=Depends(get_tx_repository)):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    path = f"/v1/stations/{station_id}/tx/jobs/claim"
    station = _signed_tx_station(station_id, "POST", path, request_id, request_timestamp, signature, {}, repo)
    if not bool((station.get("desired_state") or {}).get("running")):
        return None
    if not bool(station.get("ptt_ready", True)):
        return None
    item = tx_repo.claim(station_id)
    return TxJob.model_validate(item) if item else None


@app.get("/v1/stations/{station_id}/tx/jobs/{job_id}/audio")
def download_tx_job(station_id: str, job_id: str, signed_station_id: str = Header(alias="X-Station-ID"),
                    request_id: str = Header(alias="X-Request-ID"), request_timestamp: str = Header(alias="X-Timestamp"),
                    signature: str = Header(alias="X-Signature"), repo: Repository = Depends(get_repository),
                    tx_repo=Depends(get_tx_repository), kind: str = "output"):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    path = f"/v1/stations/{station_id}/tx/jobs/{job_id}/audio"
    _signed_tx_station(station_id, "GET", path, request_id, request_timestamp, signature, {}, repo)
    item = tx_repo.get(job_id)
    if not item or item.get("station_id") != station_id or item.get("status") not in {"claimed", "transmitting"}:
        raise api_error(404, "TX_NOT_FOUND", "TX job was not found")
    if kind not in {"source", "output"}:
        raise api_error(422, "INVALID_REQUEST", "kind must be source or output")
    audio = get_archive().download_audio(item[f"{kind}_object"])
    if audio is None:
        raise api_error(404, "TX_AUDIO_UNAVAILABLE", "TX audio is unavailable")
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, no-store"})


@app.post("/v1/stations/{station_id}/tx/jobs/{job_id}/status", response_model=TxDraft)
def update_tx_job(station_id: str, job_id: str, request: TxJobUpdate,
                  signed_station_id: str = Header(alias="X-Station-ID"), request_id: str = Header(alias="X-Request-ID"),
                  request_timestamp: str = Header(alias="X-Timestamp"), signature: str = Header(alias="X-Signature"),
                  repo: Repository = Depends(get_repository), tx_repo=Depends(get_tx_repository)):
    if signed_station_id != station_id:
        raise api_error(403, "STATION_REVOKED", "Station identity does not match")
    path = f"/v1/stations/{station_id}/tx/jobs/{job_id}/status"
    payload = request.model_dump(exclude_none=True)
    _signed_tx_station(station_id, "POST", path, request_id, request_timestamp, signature, payload, repo)
    return TxDraft.model_validate(tx_repo.station_update(station_id, job_id, request.status, request.error))
