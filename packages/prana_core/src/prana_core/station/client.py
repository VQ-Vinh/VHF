from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

import httpx

from prana_core.backend.client import BackendApiError, canonical_request
from prana_core.pipeline.models import ProcessingResult
from prana_core.station.identity import StationIdentity


def payload_hash(payload: dict | None = None) -> str:
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_station_request(
    method: str, path: str, request_id: str, timestamp: str, digest: str
) -> bytes:
    return "\n".join([method.upper(), path, request_id, timestamp, digest]).encode("utf-8")


class StationApiClient:
    def __init__(
        self,
        api_url: str,
        identity: StationIdentity,
        timeout_seconds: float = 150,
    ):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout_seconds
        # Signed station endpoints perform multiple Firestore operations
        # (registry lookup, replay protection and projection update). Staging
        # can legitimately exceed the old fixed 20-second timeout.
        self.control_timeout = min(60.0, max(30.0, timeout_seconds))
        self.identity = identity

    @property
    def ready(self) -> bool:
        return bool(self.api_url)

    @staticmethod
    def _raise(response: httpx.Response) -> None:
        if not response.is_error:
            return
        try:
            raw = response.json().get("detail", {})
            detail = raw if isinstance(raw, dict) else {}
            code = detail.get("code", "API_ERROR")
            message = detail.get("message", str(raw) or response.text)
        except Exception:
            code, message, detail = "API_ERROR", response.text, {}
        raise BackendApiError(code, message, response.status_code, detail)

    def _signed_headers(self, method: str, path: str, payload: dict | None = None) -> dict[str, str]:
        request_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        message = canonical_station_request(
            method, path, request_id, timestamp, payload_hash(payload)
        )
        return {
            "X-Station-ID": self.identity.id,
            "X-Request-ID": request_id,
            "X-Timestamp": timestamp,
            "X-Signature": self.identity.sign(message),
        }

    def create_pairing(self) -> dict:
        path = "/v1/station-pairings"
        payload = {
            "station_id": self.identity.id,
            "name": self.identity.name,
            "platform": self.identity.platform,
            "public_key": self.identity.public_key,
        }
        try:
            response = httpx.post(
                f"{self.api_url}{path}",
                json=payload,
                headers=self._signed_headers("POST", path, payload),
                timeout=20,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def provision(self, activation_hash: str) -> dict:
        path = "/v1/station-provisions"
        payload = {
            "station_id": self.identity.id,
            "name": self.identity.name,
            "platform": self.identity.platform,
            "public_key": self.identity.public_key,
            "activation_hash": activation_hash,
            "activation_version": 1,
        }
        try:
            response = httpx.post(
                f"{self.api_url}{path}",
                json=payload,
                headers=self._signed_headers("POST", path, payload),
                timeout=20,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def desired_state(self) -> dict:
        path = f"/v1/stations/{self.identity.id}/desired-state"
        try:
            response = httpx.get(
                f"{self.api_url}{path}",
                headers=self._signed_headers("GET", path),
                timeout=self.control_timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)
        return response.json()

    def heartbeat(self, payload: dict) -> None:
        path = f"/v1/stations/{self.identity.id}/heartbeat"
        try:
            response = httpx.post(
                f"{self.api_url}{path}",
                json=payload,
                headers=self._signed_headers("POST", path, payload),
                timeout=self.control_timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        self._raise(response)

    def publish_capabilities(self, payload: dict) -> None:
        path = f"/v1/stations/{self.identity.id}/capabilities"
        try:
            response = httpx.post(
                f"{self.api_url}{path}",
                json=payload,
                headers=self._signed_headers("POST", path, payload),
                timeout=self.control_timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError(
                "NETWORK_ERROR", "Cannot publish station capabilities"
            ) from exc
        self._raise(response)

    def claim_tx_job(self) -> dict | None:
        path = f"/v1/stations/{self.identity.id}/tx/jobs/claim"
        try:
            response = httpx.post(f"{self.api_url}{path}", headers=self._signed_headers("POST", path), timeout=self.control_timeout)
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot claim TX job") from exc
        self._raise(response)
        return response.json() if response.content and response.json() else None

    def download_tx_audio(self, job_id: str, kind: str = "output") -> bytes:
        path = f"/v1/stations/{self.identity.id}/tx/jobs/{job_id}/audio"
        try:
            response = httpx.get(
                f"{self.api_url}{path}", params={"kind": kind},
                headers=self._signed_headers("GET", path), timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot download TX audio") from exc
        self._raise(response)
        return response.content

    def update_tx_job(self, job_id: str, status: str, error: str | None = None) -> dict:
        path = f"/v1/stations/{self.identity.id}/tx/jobs/{job_id}/status"
        payload = {"status": status, **({"error": error} if error else {})}
        try:
            response = httpx.post(
                f"{self.api_url}{path}", json=payload,
                headers=self._signed_headers("POST", path, payload), timeout=self.control_timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot update TX job") from exc
        self._raise(response)
        return response.json()

    def me(self) -> dict:
        path = f"/v1/stations/{self.identity.id}/profile"
        try:
            response = httpx.get(
                f"{self.api_url}{path}",
                headers=self._signed_headers("GET", path),
                timeout=self.control_timeout,
            )
        except httpx.RequestError as exc:
            raise BackendApiError(
                "NETWORK_ERROR",
                "Cannot reach PRANA API",
            ) from exc
        self._raise(response)
        return response.json()

    def ensure_device(self) -> StationIdentity:
        return self.identity

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
        stable_name = f"{self.identity.id}:{session_id}:{sequence}:{digest}"
        request_id = request_id or str(uuid.uuid5(uuid.NAMESPACE_URL, stable_name))
        timestamp = str(int(time.time()))
        signature = self.identity.sign(
            canonical_request(request_id, timestamp, digest, target_language, session_id, sequence)
        )
        endpoint = f"/v1/stations/{self.identity.id}/audio/process"
        try:
            response = httpx.post(
                f"{self.api_url}{endpoint}",
                headers={
                    "X-Station-ID": self.identity.id,
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                },
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
            raise BackendApiError(
                "NETWORK_ERROR", "Cannot reach PRANA API; the WAV remains saved locally"
            ) from exc
        self._raise(response)
        return ProcessingResult.model_validate(response.json())

    def close(self) -> None:
        pass
