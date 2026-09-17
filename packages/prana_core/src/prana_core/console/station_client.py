"""HTTP transport for the fleet operator console.

Composed onto `BackendClient` rather than folded into it: account/auth/device
concerns and remote-Station concerns have different lifetimes, and the console
needs none of the audio-upload path.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

from prana_core.backend.client import (
    BackendApiError,
    BackendClient,
    raise_for_api_error,
)
from prana_core.console.models import (
    ControlLease,
    DesiredState,
    StationSummary,
    TranslationResult,
    sort_results,
)

# Renew well inside the server's 120s TTL so two missed beats are survivable.
CONTROL_RENEW_SECONDS = 45
# The console never transmits longer than the owner's plan allows; this is only
# the absolute ceiling the API itself enforces.
MAX_TX_SECONDS = 120


class OperatorStationClient:
    """Fleet-wide Station operations for an account holding `fleet_operator`."""

    def __init__(
        self,
        backend: BackendClient,
        operator_uid: str = "",
        timeout_seconds: float = 20,
    ):
        self._backend = backend
        self._timeout = timeout_seconds
        # Supplied by the caller from /v1/me. Used only to tell "my lease" from
        # somebody else's; the server never trusts it.
        self.operator_uid = operator_uid

    # -- plumbing ---------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._backend.api_url}/v1/operator{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
        files: dict | None = None,
        data: dict | None = None,
    ) -> httpx.Response:
        merged = {**self._backend.auth_headers(), **(headers or {})}
        try:
            response = httpx.request(
                method,
                self._url(path),
                params=params,
                json=json,
                headers=merged,
                timeout=timeout or self._timeout,
                files=files,
                data=data,
            )
        except httpx.RequestError as exc:
            raise BackendApiError("NETWORK_ERROR", "Cannot reach PRANA API") from exc
        raise_for_api_error(response)
        return response

    @staticmethod
    def _local_timezone_params() -> dict:
        offset = datetime.now(timezone.utc).astimezone().utcoffset() or timedelta()
        return {"timezone_offset_minutes": int(offset.total_seconds() // 60)}

    # -- fleet ------------------------------------------------------------

    def list_stations(
        self,
        limit: int = 50,
        cursor: str | None = None,
        query: str = "",
        online_only: bool = False,
    ) -> tuple[list[StationSummary], str | None]:
        params: dict = {"limit": limit, "online_only": online_only}
        if cursor:
            params["cursor"] = cursor
        if query:
            params["query"] = query
        payload = self._request("GET", "/stations", params=params).json()
        return (
            [StationSummary.from_wire(item) for item in payload.get("items", [])],
            payload.get("next_cursor"),
        )

    def get_station(self, station_id: str) -> StationSummary:
        return StationSummary.from_wire(
            self._request("GET", f"/stations/{station_id}").json()
        )

    # -- control lease ----------------------------------------------------

    def acquire_control(
        self,
        station_id: str,
        force: bool = False,
        label: str = "",
    ) -> ControlLease:
        payload = self._request(
            "POST",
            f"/stations/{station_id}/control",
            json={"force": force, "label": label},
        ).json()
        return ControlLease.from_wire(payload)

    def renew_control(self, station_id: str, epoch: int) -> ControlLease:
        payload = self._request(
            "POST",
            f"/stations/{station_id}/control/renew",
            headers={"X-Control-Epoch": str(epoch)},
        ).json()
        return ControlLease.from_wire(payload)

    def release_control(self, station_id: str, epoch: int) -> None:
        self._request(
            "DELETE",
            f"/stations/{station_id}/control",
            headers={"X-Control-Epoch": str(epoch)},
            timeout=5,
        )

    # -- control ----------------------------------------------------------

    def set_desired_state(
        self,
        station_id: str,
        epoch: int,
        *,
        running: bool | None = None,
        target_language: str | None = None,
        capture_mode: str | None = None,
        audio_device_id: str | None = None,
        tx_audio_device_id: str | None = None,
        refresh_capabilities: bool = False,
        retry: bool = False,
    ) -> DesiredState:
        body: dict = {}
        for key, value in (
            ("running", running),
            ("target_language", target_language),
            ("capture_mode", capture_mode),
            ("audio_device_id", audio_device_id),
            ("tx_audio_device_id", tx_audio_device_id),
        ):
            if value is not None:
                body[key] = value
        if refresh_capabilities:
            body["refresh_capabilities"] = True
        if retry:
            body["retry"] = True
        if not body:
            raise BackendApiError("INVALID_REQUEST", "No desired state change was supplied")
        payload = self._request(
            "PATCH",
            f"/stations/{station_id}/desired-state",
            json=body,
            headers={"X-Control-Epoch": str(epoch)},
        ).json()
        return DesiredState.from_wire(payload)

    # -- content ----------------------------------------------------------

    def live_results(self, station_id: str, limit: int = 1000) -> list[TranslationResult]:
        payload = self._request(
            "GET",
            f"/stations/{station_id}/live/results",
            params={**self._local_timezone_params(), "limit": limit},
        ).json()
        return sort_results([TranslationResult.from_wire(item) for item in payload])

    def history_days(self, station_id: str) -> list[dict]:
        return self._request(
            "GET",
            f"/stations/{station_id}/history/days",
            params=self._local_timezone_params(),
        ).json()

    def history_results(
        self,
        station_id: str,
        history_date: str,
        cursor: str | None = None,
        limit: int = 200,
    ) -> tuple[list[TranslationResult], str | None]:
        params = {**self._local_timezone_params(), "limit": limit}
        if cursor:
            params["cursor"] = cursor
        payload = self._request(
            "GET",
            f"/stations/{station_id}/history/days/{history_date}/results",
            params=params,
        ).json()
        return (
            sort_results(
                [TranslationResult.from_wire(item) for item in payload.get("items", [])]
            ),
            payload.get("next_cursor"),
        )

    def result_audio(self, station_id: str, session_id: str, request_id: str) -> bytes:
        return self._request(
            "GET",
            f"/stations/{station_id}/sessions/{session_id}/results/{request_id}/audio",
            timeout=60,
        ).content

    # -- TX ---------------------------------------------------------------

    def create_tx_draft(
        self,
        station_id: str,
        epoch: int,
        audio: bytes,
        target_language: str,
        request_id: str | None = None,
    ) -> tuple[dict, str]:
        """Upload a recording for transmission.

        `request_id` is the idempotency key. Callers keep it so that a timeout can
        be resolved by fetching the draft rather than re-uploading, which would
        risk transmitting the same audio twice.

        Every TX call carries the control epoch: the server refuses to key a
        radio for anyone not holding the current lease, and the epoch is what
        proves it.
        """
        request_id = request_id or str(uuid.uuid4())
        payload = self._request(
            "POST",
            f"/stations/{station_id}/tx/drafts",
            files={"audio": ("tx.wav", audio, "audio/wav")},
            data={"target_language": target_language},
            headers={"X-Request-ID": request_id, "X-Control-Epoch": str(epoch)},
            timeout=180,
        ).json()
        return payload, request_id

    def get_tx_draft(self, station_id: str, epoch: int, draft_id: str) -> dict:
        return self._request(
            "GET",
            f"/stations/{station_id}/tx/drafts/{draft_id}",
            headers={"X-Control-Epoch": str(epoch)},
        ).json()

    def confirm_tx_draft(
        self, station_id: str, epoch: int, draft_id: str, translation: str
    ) -> dict:
        return self._request(
            "POST",
            f"/stations/{station_id}/tx/drafts/{draft_id}/confirm",
            json={"translation": translation},
            headers={"X-Control-Epoch": str(epoch)},
            timeout=120,
        ).json()

    def cancel_tx_draft(self, station_id: str, epoch: int, draft_id: str) -> None:
        self._request(
            "DELETE",
            f"/stations/{station_id}/tx/drafts/{draft_id}",
            headers={"X-Control-Epoch": str(epoch)},
        )

    def retry_tx_draft(self, station_id: str, epoch: int, draft_id: str) -> dict:
        return self._request(
            "POST",
            f"/stations/{station_id}/tx/drafts/{draft_id}/retry",
            headers={"X-Control-Epoch": str(epoch)},
        ).json()


__all__ = ["CONTROL_RENEW_SECONDS", "MAX_TX_SECONDS", "OperatorStationClient"]
