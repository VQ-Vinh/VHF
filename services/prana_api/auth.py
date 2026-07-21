from __future__ import annotations

from dataclasses import dataclass

import firebase_admin
from fastapi import Header
from firebase_admin import auth

from services.prana_api.errors import api_error


@dataclass(frozen=True)
class Identity:
    uid: str
    email: str
    email_verified: bool


@dataclass(frozen=True)
class FirebaseSession:
    identity: Identity
    id_token: str


def _ensure_firebase() -> None:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()


def verify_id_token_value(token: str) -> Identity:
    _ensure_firebase()
    try:
        decoded = auth.verify_id_token(token, check_revoked=True)
    except Exception as exc:
        raise api_error(401, "AUTH_REQUIRED", "Firebase ID token is invalid or expired") from exc
    return Identity(
        uid=decoded["uid"],
        email=decoded.get("email", ""),
        email_verified=bool(decoded.get("email_verified")),
    )


def require_identity(authorization: str | None = Header(default=None)) -> Identity:
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(401, "AUTH_REQUIRED", "Bearer token is required")
    return verify_id_token_value(authorization[7:].strip())


def require_firebase_session(
    authorization: str | None = Header(default=None),
) -> FirebaseSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(401, "AUTH_REQUIRED", "Bearer token is required")
    token = authorization[7:].strip()
    return FirebaseSession(identity=verify_id_token_value(token), id_token=token)
