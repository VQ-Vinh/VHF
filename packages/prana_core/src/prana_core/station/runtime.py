from __future__ import annotations

import time
import json
import threading
from datetime import datetime
from pathlib import Path
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
        self._desired_running = False
        self._tx_active = False
        self._tx_state = "idle"
        self._tx_job_id = ""
        self._tx_error: str | None = None
        self._tx_device_id = ""
        self._stop_tx = threading.Event()

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
                if self.orchestrator.state not in {
                    PipelineState.IDLE,
                    PipelineState.STOPPING,
                }:
                    self.orchestrator.stop()
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
        self._desired_running = should_run
        self._tx_device_id = str(desired.get("tx_audio_device_id", ""))
        start_attempt = (generation, retry_generation)
        if (
            should_run
            and not getattr(self, "_tx_active", False)
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
            "tx_state": self._tx_state,
            "tx_job_id": self._tx_job_id,
            "active_tx_audio_device_id": self._tx_device_id if self._tx_active else "",
            "tx_error": self._tx_error,
        }

    def _save_tx_files(self, job: dict, source: bytes, output: bytes, status: str, error: str | None = None) -> None:
        filename = str(job.get("audio_filename") or f"{job['id']}.wav")
        try:
            file_date = datetime.strptime(filename[:8], "%Y%m%d")
        except (ValueError, TypeError):
            file_date = datetime.now()
        date_path = file_date.strftime("%Y/%m/%d")
        storage = self.config.storage.local
        source_path = Path(storage.tx_source_dir) / date_path / filename
        output_path = Path(storage.tx_output_dir) / date_path / filename
        result_path = Path(storage.tx_result_dir) / date_path / f"{Path(filename).stem}.json"
        for path in (source_path, output_path, result_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(source)
        output_path.write_bytes(output)
        result_path.write_text(json.dumps({**job, "status": status, "error": error}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _tx_loop(self) -> None:
        if not callable(getattr(self.client, "claim_tx_job", None)):
            return
        while not self._stop_tx.wait(1.0):
            if self._tx_active:
                continue
            if self._tx_state == "failed" and self._tx_job_id:
                try:
                    self.client.update_tx_job(self._tx_job_id, "failed", self._tx_error or "TX_FAILED")
                    self._tx_job_id = ""
                except Exception:
                    continue
            job = None
            source = b""
            output = b""
            try:
                job = self.client.claim_tx_job()
                if not job:
                    continue
                self._tx_active = True
                self._tx_job_id = str(job["id"])
                self._tx_state = "claimed"
                self._tx_error = None
                source = self.client.download_tx_audio(self._tx_job_id, "source")
                output = self.client.download_tx_audio(self._tx_job_id, "output")
                self.orchestrator.stop()
                deadline = time.monotonic() + 10
                while self.orchestrator.state != PipelineState.IDLE and time.monotonic() < deadline:
                    time.sleep(0.05)
                if self.orchestrator.state != PipelineState.IDLE:
                    raise RuntimeError("RX did not stop before TX")
                self.client.update_tx_job(self._tx_job_id, "transmitting")
                self._tx_state = "transmitting"
                if self._tx_device_id and self._tx_device_id not in self._device_indices:
                    raise RuntimeError("TX_AUDIO_DEVICE_UNAVAILABLE")
                device_index = self._device_indices.get(self._tx_device_id, -1)
                player = self._audio_backend_factory()
                play = getattr(player, "play_wav", None)
                if not callable(play):
                    raise RuntimeError("Audio output is not supported on this Station")
                play(output, device_index)
                self._save_tx_files(job, source, output, "completed")
                self.client.update_tx_job(self._tx_job_id, "completed")
                self._tx_state = "completed"
            except BackendApiError as exc:
                if exc.code != "NETWORK_ERROR":
                    logger.warning("TX worker failed: %s: %s", exc.code, exc)
                self._tx_error = exc.code
                if job and source and output:
                    self._save_tx_files(job, source, output, "failed", exc.code)
                if self._tx_job_id and self._tx_state in {"claimed", "transmitting"}:
                    try:
                        self.client.update_tx_job(self._tx_job_id, "failed", exc.code)
                        self._tx_job_id = ""
                    except Exception:
                        pass
                self._tx_state = "failed" if self._tx_job_id else "idle"
            except Exception as exc:
                logger.exception("TX playback failed")
                self._tx_error = str(exc)[:500]
                if job and source and output:
                    self._save_tx_files(job, source, output, "failed", self._tx_error)
                if self._tx_job_id:
                    try:
                        self.client.update_tx_job(self._tx_job_id, "failed", self._tx_error)
                        self._tx_job_id = ""
                    except Exception:
                        pass
                self._tx_state = "failed"
            finally:
                if self._tx_active:
                    self._tx_active = False
                    if self._desired_running and self.orchestrator.state in {PipelineState.IDLE, PipelineState.ERROR}:
                        self.orchestrator.start()
                if self._tx_state == "completed":
                    time.sleep(0.5)
                    self._tx_state = "idle"
                    self._tx_job_id = ""

    def run_forever(self) -> None:
        next_poll = 0.0
        next_heartbeat = 0.0
        tx_thread = threading.Thread(target=self._tx_loop, name="station-tx", daemon=True)
        tx_thread.start()
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
            self._stop_tx.set()
            tx_thread.join(timeout=5)
            self.orchestrator.shutdown()
