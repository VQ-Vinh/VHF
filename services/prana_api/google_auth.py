from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from google.cloud import firestore

from services.prana_api.config import Settings
from services.prana_api.errors import api_error
from services.prana_api.models import FirebaseSessionResponse, GoogleAuthorizationRequest


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
FIREBASE_IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp"


class GoogleAuthBroker:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None):
        self.settings = settings
        self._http = http_client

    def exchange(
        self,
        authorization: GoogleAuthorizationRequest,
        *,
        firebase_id_token: str = "",
        expected_email: str = "",
    ) -> FirebaseSessionResponse:
        self._require_configuration()
        client = self._http or httpx.Client(timeout=20.0)
        owns_client = self._http is None
        try:
            google_tokens = self._exchange_google_code(client, authorization)
            google_email = self._verified_google_email(
                client, str(google_tokens["access_token"])
            )
            if expected_email and google_email.casefold() != expected_email.casefold():
                raise api_error(
                    409,
                    "GOOGLE_EMAIL_MISMATCH",
                    "Choose the same Google email as the current PRANA ELEX account",
                )
            return self._exchange_firebase_session(
                client,
                str(google_tokens["id_token"]),
                firebase_id_token=firebase_id_token,
            )
        finally:
            if owns_client:
                client.close()

    def _require_configuration(self) -> None:
        if not self.settings.google_desktop_oauth_client_id.endswith(
            ".apps.googleusercontent.com"
        ) or not self.settings.google_desktop_oauth_client_secret:
            raise api_error(
                503,
                "GOOGLE_AUTH_NOT_CONFIGURED",
                "Google sign-in is not configured on the service",
            )
        if not self.settings.firebase_web_api_key:
            raise api_error(
                503,
                "GOOGLE_AUTH_NOT_CONFIGURED",
                "Firebase sign-in is not configured on the service",
            )

    def _exchange_google_code(
        self,
        client: httpx.Client,
        authorization: GoogleAuthorizationRequest,
    ) -> dict:
        try:
            response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_desktop_oauth_client_id,
                    "client_secret": self.settings.google_desktop_oauth_client_secret,
                    "code": authorization.code,
                    "code_verifier": authorization.code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": authorization.redirect_uri,
                },
            )
        except httpx.RequestError as exc:
            raise api_error(
                503, "GOOGLE_AUTH_UNAVAILABLE", "Google authentication is unavailable"
            ) from exc
        if response.is_error:
            raise api_error(
                400, "GOOGLE_AUTH_FAILED", "Google rejected the authorization response"
            )
        data = response.json()
        if not data.get("id_token") or not data.get("access_token"):
            raise api_error(
                400, "GOOGLE_AUTH_FAILED", "Google returned incomplete credentials"
            )
        return data

    @staticmethod
    def _verified_google_email(client: httpx.Client, access_token: str) -> str:
        try:
            response = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.RequestError as exc:
            raise api_error(
                503, "GOOGLE_AUTH_UNAVAILABLE", "Google authentication is unavailable"
            ) from exc
        if response.is_error:
            raise api_error(400, "GOOGLE_AUTH_FAILED", "Google profile verification failed")
        data = response.json()
        if data.get("email_verified") not in {True, "true"} or not data.get("email"):
            raise api_error(403, "GOOGLE_EMAIL_UNVERIFIED", "Google email is not verified")
        return str(data["email"]).strip()

    def _exchange_firebase_session(
        self,
        client: httpx.Client,
        google_id_token: str,
        *,
        firebase_id_token: str = "",
    ) -> FirebaseSessionResponse:
        payload = {
            "postBody": urlencode(
                {"id_token": google_id_token, "providerId": "google.com"}
            ),
            "requestUri": "http://localhost",
            "returnIdpCredential": True,
            "returnSecureToken": True,
        }
        if firebase_id_token:
            payload["idToken"] = firebase_id_token
        try:
            response = client.post(
                FIREBASE_IDENTITY_URL,
                params={"key": self.settings.firebase_web_api_key},
                json=payload,
            )
        except httpx.RequestError as exc:
            raise api_error(
                503, "GOOGLE_AUTH_UNAVAILABLE", "Firebase authentication is unavailable"
            ) from exc
        if response.is_error:
            try:
                raw_code = str(response.json()["error"]["message"])
            except Exception:
                raw_code = "AUTH_REQUEST_FAILED"
            code = raw_code.split(" : ", 1)[0].strip()
            status = 409 if code in {
                "EMAIL_EXISTS",
                "FEDERATED_USER_ID_ALREADY_LINKED",
            } else 400
            raise api_error(status, code, "Google could not be linked to Firebase")
        data = response.json()
        conflict = str(data.get("errorMessage") or "")
        if data.get("needConfirmation") or conflict in {
            "EMAIL_EXISTS",
            "FEDERATED_USER_ID_ALREADY_LINKED",
        }:
            raise api_error(
                409,
                conflict or "ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL",
                "Sign in with the existing method, then link Google in Account Center",
            )
        if not data.get("idToken") or not data.get("refreshToken"):
            raise api_error(502, "INVALID_IDP_RESPONSE", "Firebase returned an incomplete session")
        return FirebaseSessionResponse(
            id_token=str(data["idToken"]),
            refresh_token=str(data["refreshToken"]),
            expires_in=int(data.get("expiresIn", 3600)),
            email=str(data.get("email") or ""),
            uid=str(data.get("localId") or ""),
            is_new_user=bool(data.get("isNewUser")),
        )


class AuthRateLimiter:
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = max(1, requests_per_minute)
        self._requests: deque[float] = deque(maxlen=self.requests_per_minute)
        self._lock = threading.Lock()

    def check(self) -> None:
        now = time.monotonic()
        with self._lock:
            while self._requests and self._requests[0] <= now - 60:
                self._requests.popleft()
            if len(self._requests) >= self.requests_per_minute:
                raise api_error(
                    429,
                    "RATE_LIMITED",
                    "Too many Google authentication attempts",
                    retry_after=60,
                )
            self._requests.append(now)


class FirestoreAuthRateLimiter:
    """Cross-instance fixed-window limiter backed by one Firestore document."""

    def __init__(
        self,
        db,
        requests_per_minute: int,
        clock: Callable[[], datetime] | None = None,
    ):
        self.db = db
        self.requests_per_minute = max(1, requests_per_minute)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def check(self) -> None:
        now = self._clock().astimezone(timezone.utc)
        window = now.strftime("%Y-%m-%dT%H:%MZ")
        ref = self.db.collection("system_rate_limits").document("google-auth")

        @firestore.transactional
        def run(tx):
            snapshot = ref.get(transaction=tx)
            data = snapshot.to_dict() if snapshot.exists else {}
            count = int(data.get("count", 0)) if data.get("window") == window else 0
            if count >= self.requests_per_minute:
                raise api_error(
                    429,
                    "RATE_LIMITED",
                    "Too many Google authentication attempts",
                    retry_after=60,
                )
            tx.set(
                ref,
                {
                    "window": window,
                    "count": count + 1,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )

        try:
            run(self.db.transaction())
        except HTTPException:
            raise
        except Exception as exc:
            raise api_error(
                503,
                "GOOGLE_AUTH_UNAVAILABLE",
                "Google authentication is temporarily unavailable",
            ) from exc


__all__ = ["AuthRateLimiter", "FirestoreAuthRateLimiter", "GoogleAuthBroker"]
