from __future__ import annotations

import time
import json
import io
import threading
import inspect
import wave
import signal
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from prana_core import __version__
from prana_core.backend.client import BackendApiError
from prana_core.common.logger import get_logger
from prana_core.config.schema import AppConfig
from prana_core.pipeline.orchestrator import PipelineOrchestrator, PipelineState
from prana_core.audio.base import AudioBackend
from prana_core.audio.capabilities import capability_hash, normalize_audio_devices
from prana_core.station.client import StationApiClient
from prana_core.station.ptt import NullPttController, PttController

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
        ptt_controller: PttController | None = None,
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
        self._command_failed_generation = 0
        self._command_error: str | None = None
        self._audio_backend_factory = audio_backend_factory
        self._ptt_controller = ptt_controller or NullPttController()
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
        if generation != getattr(self, "_command_failed_generation", 0):
            self._command_error = None
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

        self._apply_timezone(str(desired.get("timezone", "") or ""))

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
            self._command_failed_generation = 0
            self._command_error = None
            self._station_error = None
        elif (
            should_run
            and self.observed_generation < generation
            and self.orchestrator.state == PipelineState.ERROR
            and self._last_start_attempt == start_attempt
        ):
            status = self.orchestrator.get_status()
            self._command_failed_generation = generation
            self._command_error = str(
                status.get("startup_error") or "STATION_RX_START_FAILED"
            )

    def _apply_timezone(self, name: str) -> None:
        """Adopt the owner's timezone for storage paths.

        LocalStorage reads this config object on every write, so no pipeline
        restart is needed. An unusable name keeps whatever was working before.
        """
        storage = self.config.storage.local
        if name == storage.timezone:
            return
        if name:
            try:
                ZoneInfo(name)
            except (ZoneInfoNotFoundError, ValueError):
                logger.warning("Ignoring unknown timezone %r from desired state", name)
                return
        storage.timezone = name
        logger.info("Storage timezone set to %s", name or "system clock")

    def _storage_now(self) -> datetime:
        tz_name = self.config.storage.local.timezone
        if tz_name:
            try:
                return datetime.now(ZoneInfo(tz_name))
            except (ZoneInfoNotFoundError, ValueError):
                pass
        return datetime.now()

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
            "command_failed_generation": getattr(
                self, "_command_failed_generation", 0
            ),
            "command_error": getattr(self, "_command_error", None),
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
            "ptt_mode": getattr(self._ptt_controller, "mode", "manual"),
            "ptt_ready": bool(getattr(self._ptt_controller, "ready", True)),
            "ptt_error": getattr(self._ptt_controller, "error", None),
            "active_timezone": self.config.storage.local.timezone,
        }

    def _save_tx_files(self, job: dict, source: bytes, output: bytes, status: str, error: str | None = None) -> None:
        filename = str(job.get("audio_filename") or f"{job['id']}.wav")
        try:
            file_date = datetime.strptime(filename[:8], "%Y%m%d")
        except (ValueError, TypeError):
            file_date = self._storage_now()
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

    def _play_tx_audio(self, output: bytes, device_index: int) -> None:
        try:
            with wave.open(io.BytesIO(output), "rb") as wav_file:
                duration_seconds = wav_file.getnframes() / wav_file.getframerate()
        except (wave.Error, ZeroDivisionError) as exc:
            raise RuntimeError("TX_AUDIO_INVALID") from exc
        if duration_seconds > 120.0:
            raise RuntimeError("TX_OUTPUT_TOO_LONG")
        player = self._audio_backend_factory()
        play = getattr(player, "play_wav", None)
        if not callable(play):
            raise RuntimeError("Audio output is not supported on this Station")
        stop_event = threading.Event()
        completed = threading.Event()
        playback_error: list[BaseException] = []
        release_lock = threading.Lock()
        released = False
        asserted_at: float | None = None
        watchdog_expired = False

        def release_ptt() -> None:
            nonlocal released
            with release_lock:
                if released:
                    return
                released = True
            self._ptt_controller.release()

        def watchdog_release() -> None:
            nonlocal watchdog_expired
            watchdog_expired = True
            stop_event.set()
            logger.error(
                "PTT watchdog expired",
                extra={"watchdog_seconds": watchdog_seconds},
            )
            release_ptt()

        def playback() -> None:
            try:
                parameters = inspect.signature(play).parameters
                if "stop_event" in parameters:
                    play(output, device_index, stop_event=stop_event)
                else:
                    play(output, device_index)
            except BaseException as exc:
                playback_error.append(exc)
            finally:
                completed.set()

        ptt_config = getattr(getattr(self, "config", None), "ptt", None)
        watchdog_seconds = float(getattr(ptt_config, "watchdog_seconds", 122.0))
        watchdog = threading.Timer(watchdog_seconds, watchdog_release)
        watchdog.daemon = True
        try:
            self._ptt_controller.engage()
            asserted_at = time.monotonic()
            watchdog.start()
            stop_tx = getattr(self, "_stop_tx", threading.Event())
            key_up_seconds = float(getattr(ptt_config, "key_up_delay_ms", 0)) / 1000
            tail_seconds = float(getattr(ptt_config, "tail_delay_ms", 0)) / 1000
            if stop_tx.wait(key_up_seconds):
                raise RuntimeError("TX_PLAYBACK_CANCELLED")
            worker = threading.Thread(
                target=playback,
                name="station-tx-playback",
                daemon=True,
            )
            worker.start()
            deadline = time.monotonic() + max(
                0.0,
                watchdog_seconds - key_up_seconds,
            )
            while not completed.wait(0.1):
                if stop_tx.is_set() or time.monotonic() >= deadline:
                    stop_event.set()
                    worker.join(timeout=1.0)
                    raise RuntimeError("TX_PLAYBACK_TIMEOUT")
            if playback_error:
                raise playback_error[0]
            if time.monotonic() + tail_seconds > deadline:
                stop_event.set()
                raise RuntimeError("TX_PLAYBACK_TIMEOUT")
            if stop_tx.wait(tail_seconds):
                raise RuntimeError("TX_PLAYBACK_CANCELLED")
        finally:
            stop_event.set()
            watchdog.cancel()
            release_ptt()
            logger.info(
                "TX playback finished",
                extra={
                    "audio_duration_seconds": round(duration_seconds, 3),
                    "ptt_asserted_seconds": (
                        round(time.monotonic() - asserted_at, 3)
                        if asserted_at is not None
                        else 0.0
                    ),
                    "watchdog_expired": watchdog_expired,
                },
            )

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
                if not self._ptt_controller.ready:
                    self._tx_state = "idle"
                    self._tx_error = self._ptt_controller.error or "PTT_UNAVAILABLE"
                    continue
                job = self.client.claim_tx_job()
                if not job:
                    continue
                self._tx_active = True
                self._tx_job_id = str(job["id"])
                self._tx_state = "claimed"
                self._tx_error = None
                source = self.client.download_tx_audio(self._tx_job_id, "source")
                output = self.client.download_tx_audio(self._tx_job_id, "output")
                pause_error: list[BaseException] = []
                pause_done = threading.Event()
                pause_started_at = time.monotonic()

                def pause_capture() -> None:
                    try:
                        self.orchestrator.pause_capture_for_tx()
                    except BaseException as exc:
                        pause_error.append(exc)
                    finally:
                        pause_done.set()

                threading.Thread(target=pause_capture, daemon=True).start()
                if not pause_done.wait(7.0):
                    raise RuntimeError("RX did not pause before TX")
                if pause_error or self.orchestrator.state != PipelineState.PAUSED:
                    raise RuntimeError("RX did not stop before TX")
                logger.info(
                    "RX capture paused for TX",
                    extra={
                        "tx_job_id": self._tx_job_id,
                        "rx_pause_ms": round(
                            (time.monotonic() - pause_started_at) * 1000, 1
                        ),
                    },
                )
                self.client.update_tx_job(self._tx_job_id, "transmitting")
                self._tx_state = "transmitting"
                if self._tx_device_id and self._tx_device_id not in self._device_indices:
                    raise RuntimeError("TX_AUDIO_DEVICE_UNAVAILABLE")
                device_index = self._device_indices.get(self._tx_device_id, -1)
                self._play_tx_audio(output, device_index)
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
                    if self._desired_running and self.orchestrator.state == PipelineState.PAUSED:
                        try:
                            self.orchestrator.resume_capture_after_tx()
                        except Exception:
                            logger.exception("RX resume after TX failed")
                    elif not self._desired_running and self.orchestrator.state == PipelineState.PAUSED:
                        self.orchestrator.stop()
                if self._tx_state == "completed":
                    time.sleep(0.5)
                    self._tx_state = "idle"
                    self._tx_job_id = ""

    def run_forever(self) -> None:
        shutdown_requested = threading.Event()
        previous_handlers: dict[int, object] = {}

        def request_shutdown(signum, _frame) -> None:
            logger.info("Station shutdown requested", extra={"signal": signum})
            shutdown_requested.set()
            self._stop_tx.set()
            try:
                self._ptt_controller.release()
            except Exception:
                logger.exception("Failed to release PTT during signal handling")

        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, request_shutdown)
        next_poll = 0.0
        next_heartbeat = 0.0
        tx_thread = threading.Thread(target=self._tx_loop, name="station-tx", daemon=True)
        tx_thread.start()
        try:
            try:
                self._scan_capabilities(force=True)
            except Exception as exc:
                logger.warning("Initial capability scan failed: %s", exc)
            while not shutdown_requested.is_set():
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
            self._ptt_controller.close()
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
