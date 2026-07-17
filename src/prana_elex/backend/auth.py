from __future__ import annotations

import time

import httpx

from prana_elex.backend.secure_store import SecureStore


class FirebaseAuthError(RuntimeError):
    pass


class FirebaseAuthClient:
    def __init__(self, api_key: str, store: SecureStore | None = None, timeout: float = 20.0):
        self.api_key = api_key
        self.store = store or SecureStore()
        self.timeout = timeout
        self._id_token = ""
        self._expires_at = 0.0

    @property
    def has_session(self) -> bool:
        return bool(self.store.get("refresh_token"))

    @property
    def email(self) -> str:
        return self.store.get("email") or ""

    def _identity(self, method: str, payload: dict) -> dict:
        if not self.api_key:
            raise FirebaseAuthError("Firebase Web API key is not configured")
        response = httpx.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:{method}",
            params={"key": self.api_key},
            json=payload,
            timeout=self.timeout,
        )
        if response.is_error:
            try:
                code = response.json()["error"]["message"]
            except Exception:
                code = "AUTH_REQUEST_FAILED"
            raise FirebaseAuthError(code.replace("_", " ").title())
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
            raise FirebaseAuthError("Sign in is required")
        response = httpx.post(
            "https://securetoken.googleapis.com/v1/token",
            params={"key": self.api_key},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=self.timeout,
        )
        if response.is_error:
            self.sign_out()
            raise FirebaseAuthError("Session expired; sign in again")
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
