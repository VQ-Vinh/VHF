from __future__ import annotations

import time

import httpx

from prana_core.backend.google_oauth import (
    GoogleOAuthError,
    GoogleOAuthSession,
)
from prana_core.backend.credential_store import CredentialStore, MemoryCredentialStore


class FirebaseAuthError(RuntimeError):
    def __init__(self, message: str, code: str = "AUTH_REQUEST_FAILED"):
        super().__init__(message)
        self.code = code


class FirebaseAuthClient:
    def __init__(
        self,
        api_key: str,
        store: CredentialStore | None = None,
        timeout: float = 20.0,
        google_oauth_client_id: str = "",
    ):
        self.api_key = api_key
        self.google_oauth_client_id = google_oauth_client_id.strip()
        self.store = store or MemoryCredentialStore()
        self.timeout = timeout
        self._id_token = ""
        self._expires_at = 0.0

    @property
    def has_session(self) -> bool:
        return bool(self.store.get("refresh_token"))

    @property
    def email(self) -> str:
        return self.store.get("email") or ""

    @property
    def google_enabled(self) -> bool:
        return self.google_oauth_client_id.endswith(".apps.googleusercontent.com")

    def _identity(self, method: str, payload: dict) -> dict:
        if not self.api_key:
            raise FirebaseAuthError(
                "Firebase Web API key is not configured", "AUTH_NOT_CONFIGURED"
            )
        try:
            response = httpx.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:{method}",
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise FirebaseAuthError("Cannot reach Firebase Authentication", "NETWORK_ERROR") from exc
        if response.is_error:
            try:
                raw_code = str(response.json()["error"]["message"])
            except Exception:
                raw_code = "AUTH_REQUEST_FAILED"
            code = raw_code.split(" : ", 1)[0].strip()
            raise FirebaseAuthError(raw_code.replace("_", " ").title(), code)
        return response.json()

    def sign_up(self, email: str, password: str) -> None:
        data = self._identity("signUp", {"email": email, "password": password, "returnSecureToken": True})
        self._save_tokens(data, email)
        self.send_verification_email()

    def sign_in(self, email: str, password: str) -> None:
        data = self._identity(
            "signInWithPassword", {"email": email, "password": password, "returnSecureToken": True}
        )
        self._save_tokens(data, email)

    def begin_google_oauth(self, timeout: float = 300.0) -> GoogleOAuthSession:
        return GoogleOAuthSession(self.google_oauth_client_id, timeout=timeout)

    def accept_firebase_session(self, data: dict) -> bool:
        normalized = {
            "idToken": data.get("id_token"),
            "refreshToken": data.get("refresh_token"),
            "expiresIn": data.get("expires_in", 3600),
        }
        if not normalized["idToken"] or not normalized["refreshToken"]:
            raise FirebaseAuthError(
                "Firebase returned an incomplete Google session",
                "INVALID_IDP_RESPONSE",
            )
        self._save_tokens(normalized, str(data.get("email") or ""))
        return bool(data.get("is_new_user"))

    def provider_ids(self) -> list[str]:
        data = self._identity("lookup", {"idToken": self.id_token()})
        users = data.get("users") or []
        if not users:
            return []
        providers = users[0].get("providerUserInfo") or []
        return sorted(
            {
                str(provider.get("providerId"))
                for provider in providers
                if provider.get("providerId")
            }
        )

    def send_verification_email(self) -> None:
        self._identity("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": self.id_token()})

    def request_password_reset(self, email: str) -> None:
        self._identity("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})

    def _save_tokens(self, data: dict, email: str) -> None:
        self._id_token = data["idToken"]
        self._expires_at = time.time() + int(data.get("expiresIn", 3600)) - 60
        self.store.set("refresh_token", data["refreshToken"])
        self.store.set("email", email)

    def id_token(self) -> str:
        if self._id_token and time.time() < self._expires_at:
            return self._id_token
        refresh_token = self.store.get("refresh_token")
        if not refresh_token:
            raise FirebaseAuthError("Sign in is required", "AUTH_REQUIRED")
        try:
            response = httpx.post(
                "https://securetoken.googleapis.com/v1/token",
                params={"key": self.api_key},
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise FirebaseAuthError("Cannot refresh the Firebase session", "NETWORK_ERROR") from exc
        if response.is_error:
            self.sign_out()
            raise FirebaseAuthError("Session expired; sign in again", "AUTH_REQUIRED")
        data = response.json()
        self._id_token = data["id_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600)) - 60
        self.store.set("refresh_token", data["refresh_token"])
        return self._id_token

    def sign_out(self) -> None:
        self._id_token = ""
        self._expires_at = 0
        self.store.delete("refresh_token")
        self.store.delete("email")


__all__ = ["FirebaseAuthClient", "FirebaseAuthError", "GoogleOAuthError"]
