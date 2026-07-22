from __future__ import annotations

import hashlib
import secrets
import time
import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
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
from services.prana_api.google_services import CloudStorageArchive, GeminiProcessor
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
    StationClaimRequest,
    StationDesiredState,
    StationDesiredStatePatch,
    StationHeartbeat,
    StationPairingRequest,
    StationPairingResponse,
    StationProvisionRequest,
    StationProvisionResponse,
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
    if account.plan_id:
        usage = repo.get_usage(identity.uid, repo.get_plan(account.plan_id))
    return MeResponse(**account.model_dump(), usage=usage)


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
    return repo.claim_station_activation(
        identity.uid,
        request.setup_id,
        request.activation_code,
        plan.max_stations,
    )


@app.post("/v1/station-pairings/{pairing_id}/claim", response_model=Station)
def claim_station(
    pairing_id: str,
    request: StationClaimRequest,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    _account, plan = active_account(identity, repo)
    repo.check_pairing_claim_rate(identity.uid, pairing_id)
    return repo.claim_station(
        identity.uid,
        pairing_id,
        _pairing_hash(pairing_id, request.pairing_code.upper()),
        plan.max_stations,
    )


@app.get("/v1/stations", response_model=list[Station])
def list_stations(
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    active_account(identity, repo)
    return repo.list_stations(identity.uid)


@app.delete("/v1/stations/{station_id}", status_code=204)
def revoke_station(
    station_id: str,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    verified_account(identity, repo)
    repo.revoke_station(identity.uid, station_id)
    return Response(status_code=204)


@app.patch("/v1/stations/{station_id}/desired-state", response_model=StationDesiredState)
def update_station_desired_state(
    station_id: str,
    request: StationDesiredStatePatch,
    identity: Identity = Depends(require_identity),
    repo: Repository = Depends(get_repository),
):
    active_account(identity, repo)
    updates = request.model_dump(exclude={"retry"}, exclude_none=True)
    if request.retry:
        updates["retry_generation_increment"] = True
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
        payload=request.model_dump(),
        repo=repo,
    )
    repo.heartbeat_station(station_id, request)
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
    response = model_result.response.model_dump(mode="json")
    metrics = dict(model_result.metrics)
    metrics.update({"audio_seconds": info.seconds, "request_id": request_id})
    try:
        get_archive().archive(identity.uid, session_id, request_id, data, response)
    except Exception:
        metrics["archive_failed"] = True
        repo.settle_success(identity.uid, request_id, response, metrics)
        raise api_error(503, "SERVICE_USAGE_LIMIT_REACHED", "Result was processed but cloud archival is temporarily unavailable")
    repo.settle_success(identity.uid, request_id, response, metrics)
    return model_result.response


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
        repo.publish_station_result(owner_uid, station_id, reservation.cached_response or {})
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

    response = {
        **model_result.response.model_dump(mode="json"),
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
        get_archive().archive(owner_uid, session_id, request_id, data, response)
        repo.publish_station_result(owner_uid, station_id, response)
    except Exception:
        metrics["archive_or_projection_failed"] = True
        repo.settle_success(owner_uid, request_id, response, metrics)
        raise api_error(
            503,
            "SERVICE_USAGE_LIMIT_REACHED",
            "Result was processed but cloud synchronization is temporarily unavailable",
        )
    repo.settle_success(owner_uid, request_id, response, metrics)
    return ProcessingResponse.model_validate(response)
