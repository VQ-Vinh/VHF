from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path

import httpx

from prana_core.backend.auth import FirebaseAuthClient
from prana_core.backend.google_oauth import GoogleOAuthAuthorization
from prana_core.backend.device import DeviceIdentity
from prana_core.backend.credential_store import CredentialStore, MemoryCredentialStore
from prana_core.pipeline.models import ProcessingResult


class BackendApiError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 0, detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.detail = dict(detail or {})


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


class BackendClient:
    def __init__(
        self,
        api_url: str,
        firebase_api_key: str,
        timeout_seconds: float = 150,
        google_oauth_client_id: str = "",
        credential_store: CredentialStore | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.credential_store = credential_store or MemoryCredentialStore()
        self.auth = FirebaseAuthClient(
            firebase_api_key,
            store=self.credential_store,
            google_oauth_client_id=google_oauth_client_id,
        )
        self.device: DeviceIdentity | None = None
        self.timeout = timeout_seconds
        self._registered = False

    @property
    def ready(self) -> bool:
        return bool(self.api_url and self.auth.has_session)

    @property
    def local_device_id(self) -> str:
        if self.device is None:
            self.device = DeviceIdentity(self.credential_store)
        return self.device.id

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth.id_token()}"}

    @staticmethod
    def _raise(response: httpx.Response) -> None:
        if not response.is_error:
            return
        detail = {}
        try:
            raw_detail = response.json().get("detail", {})
            detail = raw_detail if isinstance(raw_detail, dict) else {}
            code = detail.get("code", "API_ERROR")
            message = detail.get("message", str(raw_detail) or response.text)
        except Exception:
            code, message = "API_ERROR", response.text
        raise BackendApiError(code, message, response.status_code, detail)

    def me(self) -> dict:
        try:
            response = httpx.get(f"{self.api_url}/v1/me", headers=self._headers(), timeout=20)
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def sign_in_with_google(self, authorization: GoogleOAuthAuthorization) -> bool:
        data = self._google_auth_request("exchange", authorization, authenticated=False)
        return self.auth.accept_firebase_session(data)

    def link_google(self, authorization: GoogleOAuthAuthorization) -> None:
        data = self._google_auth_request("link", authorization, authenticated=True)
        self.auth.accept_firebase_session(data)

    def _google_auth_request(
        self,
        operation: str,
        authorization: GoogleOAuthAuthorization,
        *,
        authenticated: bool,
    ) -> dict:
        headers = self._headers() if authenticated else {}
        try:
            response = httpx.post(
                f"{self.api_url}/v1/auth/google/{operation}",
                headers=headers,
                json={
                    "code": authorization.code,
                    "code_verifier": authorization.code_verifier,
                    "redirect_uri": authorization.redirect_uri,
                },
                timeout=30,
            )
        except httpx.RequestError as exc:
            raise BackendApiError(
                "NETWORK_ERROR", "Cannot reach PRANA authentication service"
            ) from exc
        self._raise(response)
        return response.json()

    def list_devices(self) -> list[dict]:
        try:
            response = httpx.get(f"{self.api_url}/v1/devices", headers=self._headers(), timeout=20)
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def list_plans(self) -> list[dict]:
        try:
            response = httpx.get(
                f"{self.api_url}/v1/plans", headers=self._headers(), timeout=20
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def select_plan(self, plan_id: str) -> dict:
        try:
            response = httpx.post(
                f"{self.api_url}/v1/subscription/select",
                headers=self._headers(),
                json={"plan_id": plan_id},
                timeout=20,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def revoke_device(self, device_id: str) -> None:
        try:
            response = httpx.delete(
                f"{self.api_url}/v1/devices/{device_id}", headers=self._headers(), timeout=20
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)

    def ensure_device(self) -> DeviceIdentity:
        if self.device is None:
            self.device = DeviceIdentity(self.credential_store)
        if not self._registered:
            response = httpx.post(
                f"{self.api_url}/v1/devices/register",
                headers=self._headers(),
                json={
                    "device_id": self.device.id,
                    "name": self.device.name,
                    "platform": self.device.platform,
                    "public_key": self.device.public_key,
                },
                timeout=20,
            )
            self._raise(response)
            self._registered = True
        return self.device

    def reset_registration(self) -> None:
        self._registered = False

    def sign_out(self) -> None:
        self.auth.sign_out()
        self._registered = False

    def process_audio(
        self,
        audio_path: str | Path,
        session_id: str,
        sequence: int,
        target_language: str,
        audio_bytes: bytes | None = None,
        request_id: str | None = None,
    ) -> ProcessingResult:
        path = Path(audio_path)
        data = audio_bytes if audio_bytes is not None else path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        device = self.ensure_device()
        stable_name = f"{device.id}:{session_id}:{sequence}:{digest}"
        request_id = request_id or str(uuid.uuid5(uuid.NAMESPACE_URL, stable_name))
        timestamp = str(int(time.time()))
        signature = device.sign(
            canonical_request(request_id, timestamp, digest, target_language, session_id, sequence)
        )
        headers = self._headers() | {
            "X-Device-ID": device.id,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }
        try:
            response = httpx.post(
                f"{self.api_url}/v1/audio/process",
                headers=headers,
                data={
                    "target_language": target_language,
                    "session_id": session_id,
                    "sequence": str(sequence),
                    "request_id": request_id,
                },
                files={"audio": (path.name, data, "audio/wav")},
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API; the WAV remains saved locally") from exc
        self._raise(response)
        return ProcessingResult.model_validate(response.json())

    def close(self) -> None:
        pass
