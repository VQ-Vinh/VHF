from __future__ import annotations

import time
import uuid
from typing import Callable
from prana_core import __version__
from prana_core.backend.client import BackendApiError
from prana_core.common.logger import get_logger
from prana_core.config.schema import AppConfig
from prana_core.pipeline.orchestrator import PipelineOrchestrator, PipelineState
from prana_core.audio.base import AudioBackend
from prana_core.audio.capabilities import capability_hash, normalize_audio_devices
from prana_core.station.client import StationApiClient

logger = get_logger(__name__)


def _app_version() -> str:
    return __version__


class StationRuntime:
    """Poll desired state and expose observed state without user credentials."""

    def __init__(
        self,
        config: AppConfig,
        client: StationApiClient,
        audio_backend_factory: Callable[[], AudioBackend],
    ):
        self.config = config
        self.client = client
        self.orchestrator = PipelineOrchestrator(config, client, audio_backend_factory)
        self.observed_generation = 0
        self.retry_generation = 0
        self._pairing_expires_at = 0.0
        self._provisioning_notice_shown = False
        self._boot_id = uuid.uuid4().hex
        self._device_indices: dict[str, int] = {}
        self._device_modes: dict[str, str] = {}
        self._capability_hash = ""
        self._published_capability_hash = ""
        self._last_capability_refresh_generation = -1
        self._next_capability_scan = 0.0
        self._station_error: str | None = None
        self._failed_audio_generation = -1
        self._last_start_attempt: tuple[int, int] | None = None
        self._audio_backend_factory = audio_backend_factory

    def _scan_capabilities(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now < self._next_capability_scan:
            return
        self._next_capability_scan = now + 30
        backend = self._audio_backend_factory()
        devices = backend.list_devices()
        list_loopbacks = getattr(backend, "list_loopback_devices", None)
        loopbacks = list_loopbacks() if callable(list_loopbacks) else []
        public, indices = normalize_audio_devices(devices, loopbacks)
        modes = ["device"]
        if any(item["mode"] == "loopback" for item in public):
            modes.append("loopback")
        body = {
            "capture_modes": modes,
            "audio_devices": public,
            "storage_path": str(self.config.general.data_dir),
        }
        digest = capability_hash(body)
        self._device_indices = indices
        self._device_modes = {item["id"]: item["mode"] for item in public}
        self._capability_hash = digest
        if force or digest != self._published_capability_hash:
            payload = {"capability_hash": digest, **body}
            self.client.publish_capabilities(payload)
            self._published_capability_hash = digest

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
            self._failed_audio_generation = -1

        refresh_generation = int(desired.get("capability_refresh_generation", 0))
        if refresh_generation > getattr(
            self, "_last_capability_refresh_generation", 0
        ):
            self._scan_capabilities(force=True)
            self._last_capability_refresh_generation = refresh_generation

        audio_config = getattr(self.config, "audio", None)
        if audio_config is None:
            capture_mode = "device"
            audio_changed = False
            device_id = ""
            index = -1
        else:
            capture_mode = str(desired.get("capture_mode", audio_config.capture_mode))
            device_id = str(desired.get("audio_device_id", ""))
            audio_changed = capture_mode != audio_config.capture_mode
            if device_id:
                index = getattr(self, "_device_indices", {}).get(device_id)
                if index is None:
                    # Device identifiers can change after an OS/driver update.
                    # Falling back to the platform default keeps STOP/START and
                    # generation acknowledgement from becoming permanently
                    # wedged behind a stale remote selection.
                    self._station_error = "AUDIO_DEVICE_UNAVAILABLE"
                    device_id = ""
                    index = -1
                audio_changed = audio_changed or index != audio_config.device_index
            else:
                index = -1
        if audio_changed and generation != getattr(
            self, "_failed_audio_generation", -1
        ):
            previous = (audio_config.capture_mode, audio_config.device_index)
            was_running = self.orchestrator.state == PipelineState.RUNNING
            audio_config.capture_mode = capture_mode
            audio_config.device_index = index
            if was_running:
                self.orchestrator.restart()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if self.orchestrator.state in {
                        PipelineState.RUNNING,
                        PipelineState.ERROR,
                    }:
                        break
                    time.sleep(0.1)
                if self.orchestrator.state != PipelineState.RUNNING:
                    audio_config.capture_mode, audio_config.device_index = previous
                    self._station_error = "AUDIO_DEVICE_UNAVAILABLE"
                    self._failed_audio_generation = generation
                    if self.orchestrator.state == PipelineState.ERROR:
                        self.orchestrator.start()
                    return
            self._station_error = None

        should_run = bool(desired.get("running"))
        start_attempt = (generation, retry_generation)
        if (
            should_run
            and self.orchestrator.state in {PipelineState.IDLE, PipelineState.ERROR}
            and getattr(self, "_last_start_attempt", None) != start_attempt
        ):
            self._last_start_attempt = start_attempt
            self.orchestrator.start()
        elif not should_run and self.orchestrator.state not in {PipelineState.IDLE, PipelineState.STOPPING}:
            self.orchestrator.stop()
            self._last_start_attempt = None

        applied = (
            should_run
            and self.orchestrator.state == PipelineState.RUNNING
            or not should_run
            and self.orchestrator.state == PipelineState.IDLE
        )
        if applied:
            self.observed_generation = generation
            if hasattr(self, "_station_error"):
                self._station_error = None

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
            "boot_id": self._boot_id,
            "active_capture_mode": self.config.audio.capture_mode,
            "active_audio_device_id": next(
                (
                    device_id
                    for device_id, index in self._device_indices.items()
                    if index == self.config.audio.device_index
                    and getattr(self, "_device_modes", {}).get(device_id)
                    == self.config.audio.capture_mode
                ),
                "",
            ),
            "error": self._station_error or status.get("backend_error"),
            "retrying": bool(status.get("retrying")),
            "retry_code": status.get("retry_code"),
            "retry_attempt": int(status.get("retry_attempt", 0)),
        }

    def run_forever(self) -> None:
        next_poll = 0.0
        next_heartbeat = 0.0
        try:
            try:
                self._scan_capabilities(force=True)
            except Exception as exc:
                logger.warning("Initial capability scan failed: %s", exc)
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
                try:
                    self._scan_capabilities()
                except BackendApiError as exc:
                    if exc.code not in {"STATION_NOT_PAIRED", "NETWORK_ERROR"}:
                        logger.warning("Capability update failed: %s: %s", exc.code, exc)
                except Exception as exc:
                    self._next_capability_scan = time.monotonic() + 5
                    logger.warning("Audio capability scan failed: %s", exc)
                time.sleep(0.2)
        finally:
            self.orchestrator.shutdown()
