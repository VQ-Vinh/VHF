from __future__ import annotations

import time
import re
import uuid
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Form, Header, Response, UploadFile
from fastapi.responses import JSONResponse

from services.prana_api.audio import validate_wav
from services.prana_api.auth import Identity, require_identity
from services.prana_api.config import get_settings
from services.prana_api.errors import api_error
from services.prana_api.google_services import CloudStorageArchive, GeminiProcessor
from services.prana_api.models import (
    Device,
    DeviceRegisterRequest,
    MeResponse,
    ProcessingResponse,
)
from services.prana_api.repository import FirestoreRepository, Repository
from services.prana_api.security import (
    body_hash,
    canonical_request,
    idempotency_hash,
    verify_device_signature,
    verify_timestamp,
)

app = FastAPI(title="PRANA ELEX API", version="1.1.0", docs_url=None, redoc_url=None)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/me", response_model=MeResponse)
def me(identity: Identity = Depends(require_identity), repo: Repository = Depends(get_repository)):
    account = repo.sync_identity(identity.uid, identity.email, identity.email_verified)
    usage = None
    if account.plan_id:
        usage = repo.get_usage(identity.uid, repo.get_plan(account.plan_id))
    return MeResponse(**account.model_dump(), usage=usage)


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
