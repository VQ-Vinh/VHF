from __future__ import annotations

import base64
import hashlib
import time
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from services.prana_api.errors import api_error


def body_hash(audio: bytes) -> str:
    return hashlib.sha256(audio).hexdigest()


def station_payload_hash(payload: dict | None = None) -> str:
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def idempotency_hash(audio_sha256: str, target_language: str, session_id: str, sequence: int) -> str:
    value = "\n".join([audio_sha256, target_language, session_id, str(sequence)])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_request(
    request_id: str,
    timestamp: str,
    audio_sha256: str,
    target_language: str,
    session_id: str,
    sequence: int,
) -> bytes:
    return "\n".join(
        [request_id, timestamp, audio_sha256, target_language, session_id, str(sequence)]
    ).encode("utf-8")


def canonical_station_request(
    method: str,
    path: str,
    request_id: str,
    timestamp: str,
    payload_sha256: str,
) -> bytes:
    """Canonical form for signed station JSON/control requests."""
    return "\n".join(
        [method.upper(), path, request_id, timestamp, payload_sha256]
    ).encode("utf-8")


def verify_device_signature(public_key_b64: str, signature_b64: str, message: bytes) -> None:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
        signature = base64.b64decode(signature_b64, validate=True)
        public_key.verify(signature, message)
    except (ValueError, InvalidSignature) as exc:
        raise api_error(403, "DEVICE_REVOKED", "Invalid device signature") from exc


def verify_timestamp(value: str, max_skew_seconds: int) -> None:
    try:
        timestamp = int(value)
    except ValueError as exc:
        raise api_error(403, "DEVICE_REVOKED", "Invalid request timestamp") from exc
    if abs(int(time.time()) - timestamp) > max_skew_seconds:
        raise api_error(403, "DEVICE_REVOKED", "Request timestamp is outside the replay window")
