from __future__ import annotations

import time
from importlib.metadata import PackageNotFoundError, version

from prana_elex.backend.client import BackendApiError
from prana_elex.common.logger import get_logger
from prana_elex.config.schema import AppConfig
from prana_elex.pipeline.orchestrator import PipelineOrchestrator, PipelineState
from prana_elex.station.client import StationApiClient

logger = get_logger(__name__)


def _app_version() -> str:
    try:
        return version("prana-elex")
    except PackageNotFoundError:
        return "dev"


class StationRuntime:
    """Poll desired state and expose observed state without user credentials."""

    def __init__(self, config: AppConfig, client: StationApiClient):
        self.config = config
        self.client = client
        self.orchestrator = PipelineOrchestrator(config, backend=client)
        self.observed_generation = 0
        self.retry_generation = 0
        self._pairing_expires_at = 0.0
        self._provisioning_notice_shown = False

    def _show_pairing(self, pairing: dict) -> None:
        print("\nPair this station in PRANA ELEX Mobile")
        print(f"Code: {pairing['pairing_code']}")
        print(f"Link: {pairing['qr_payload']}")
        try:
            import qrcode

            qr = qrcode.QRCode(border=1)
            qr.add_data(pairing["qr_payload"])
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except ImportError:
            logger.info("Install the qrcode extra to render an ASCII QR code")
        self._pairing_expires_at = time.monotonic() + 9 * 60

    def _desired(self) -> dict | None:
        try:
            return self.client.desired_state()
        except BackendApiError as exc:
            if exc.code == "STATION_NOT_PAIRED":
                if self.client.identity.store.get("station_provisioned") == "1":
                    if not self._provisioning_notice_shown:
                        logger.info("Station is provisioned. Scan the printed device label in PRANA ELEX Mobile.")
                        self._provisioning_notice_shown = True
                    return None
                if time.monotonic() >= self._pairing_expires_at:
                    self._show_pairing(self.client.create_pairing())
                return None
            raise

    def _apply(self, desired: dict) -> None:
        generation = int(desired.get("generation", 0))
        target = str(desired.get("target_language", "en"))
        if target != self.config.translation.target_language:
            self.config.translation.target_language = target

        retry_generation = int(desired.get("retry_generation", 0))
        if retry_generation > self.retry_generation:
            self.orchestrator.retry_last_failed()
            self.retry_generation = retry_generation

        should_run = bool(desired.get("running"))
        if should_run and self.orchestrator.state in {PipelineState.IDLE, PipelineState.ERROR}:
            self.orchestrator.start()
        elif not should_run and self.orchestrator.state not in {PipelineState.IDLE, PipelineState.STOPPING}:
            self.orchestrator.stop()

        applied = (
            should_run
            and self.orchestrator.state == PipelineState.RUNNING
            or not should_run
            and self.orchestrator.state == PipelineState.IDLE
        )
        if applied:
            self.observed_generation = generation

    def _heartbeat_payload(self) -> dict:
        status = self.orchestrator.get_status()
        state = self.orchestrator.state
        capture_state = "error" if state == PipelineState.ERROR else "idle"
        if state in {PipelineState.RUNNING, PipelineState.STARTING}:
            capture_state = "recording" if status["recording"] else "listening"
        return {
            "capture_state": capture_state,
            "session_id": status["session_id"],
            "sequence": status["sequences_processed"],
            "app_version": _app_version(),
            "observed_generation": self.observed_generation,
            "target_language": self.config.translation.target_language,
            "error": status.get("backend_error"),
        }

    def run_forever(self) -> None:
        next_poll = 0.0
        next_heartbeat = 0.0
        try:
            while True:
                now = time.monotonic()
                if now >= next_poll:
                    try:
                        desired = self._desired()
                        if desired is not None:
                            self._apply(desired)
                    except BackendApiError as exc:
                        logger.warning("Station poll failed: %s: %s", exc.code, exc)
                    next_poll = now + 2.0
                if now >= next_heartbeat:
                    try:
                        self.client.heartbeat(self._heartbeat_payload())
                    except BackendApiError as exc:
                        if exc.code not in {"STATION_NOT_PAIRED", "NETWORK_ERROR"}:
                            logger.warning("Station heartbeat failed: %s: %s", exc.code, exc)
                    next_heartbeat = now + 5.0
                time.sleep(0.2)
        finally:
            self.orchestrator.shutdown()
