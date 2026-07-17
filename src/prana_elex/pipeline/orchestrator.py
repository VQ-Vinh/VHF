from __future__ import annotations

import io
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import numpy as np
import soundfile as sf

from prana_elex.audio.recorder import AudioRecorder
from prana_elex.config.schema import AppConfig
from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.storage.local import LocalStorage
from prana_elex.common.logger import get_logger
from prana_elex.common.timing import LatencyTracker
from prana_elex.vad.base import VADBackend, VADState
from prana_elex.vad.silero import SileroVAD
from prana_elex.vad.webrtc import WebRTCVAD
from prana_elex.pipeline.session import SessionManager
from prana_elex.pipeline.events import event_bus

logger = get_logger(__name__)

SpeechBuffer = list[np.ndarray]
TARGET_SR = 16000


@dataclass
class SegmentJob:
    audio_data: np.ndarray
    session_id: str
    sequence: int
    sample_rate: int
    timestamp: float = field(default_factory=time.time)


class PipelineState(Enum):
    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    ERROR = auto()


# ── PipelineOrchestrator ────────────────────────────────────────────
class PipelineOrchestrator:
    def __init__(self, config: AppConfig, backend: BackendClient | None = None):
        self._config = config
        self._state = PipelineState.IDLE
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()

        self._session = SessionManager(config.general.session_prefix)
        self._storage = LocalStorage(config.storage.local)
        self._backend = backend or BackendClient(
            config.backend.api_url,
            config.backend.firebase_api_key,
            config.backend.timeout_seconds,
        )
        self._vad = self._create_vad()

        self._backend_error: str | None = None
        self._last_backend_ok: bool | None = None
        self._failed_audio: dict[tuple[str, int], Path] = {}

        self._vad_buffer: SpeechBuffer = []
        self._recording = False
        self._samples_since_speech = 0
        self._speech_frame_count = 0
        self._recorder: AudioRecorder | None = None

        self._num_workers = config.general.num_workers
        self._job_queue: queue.Queue[SegmentJob | None] = queue.Queue(maxsize=32)
        self._executor: ThreadPoolExecutor | None = None
        self._worker_futures: list = []
        self._cleanup_timer: threading.Timer | None = None

    # ── State ───────────────────────────────────────────────────────
    @property
    def state(self) -> PipelineState:
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, value: PipelineState):
        with self._state_lock:
            self._state = value

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._state in (PipelineState.RUNNING, PipelineState.STARTING)

    def _is_state(self, *states: PipelineState) -> bool:
        with self._state_lock:
            return self._state in states

    def _set_state(self, value: PipelineState, message: str = "") -> None:
        with self._state_lock:
            self._state = value
        event_bus.emit("state_changed", value, message)
        logger.info("Pipeline state: %s %s", value.name, message)

    # ── VAD factory ─────────────────────────────────────────────────
    def _create_vad(self) -> VADBackend:
        vad_cfg = self._config.vad
        if vad_cfg.backend == "silero":
            return SileroVAD(threshold=vad_cfg.threshold, model_path=vad_cfg.silero_model_path or None)
        return WebRTCVAD(threshold=vad_cfg.threshold)

    # ── Session ─────────────────────────────────────────────────────
    def start_session(self) -> str:
        return self._session.start_session()

    # ── Start ───────────────────────────────────────────────────────
    def start(self) -> None:
        if not self._is_state(PipelineState.IDLE, PipelineState.ERROR):
            logger.warning("Cannot start: state=%s", self.state.name)
            return
        logger.info("start() called")
        self._stop_event.clear()
        self._set_state(PipelineState.STARTING, "Starting...")
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_start(self) -> None:
        logger.info("_do_start entered")
        self._vad_buffer.clear()
        self._recording = False
        self._samples_since_speech = 0
        self._speech_frame_count = 0
        try:
            self._session.start_session()
            sid = self._session.session_id
            logger.info("Session started", extra={"session_id": sid, "workers": self._num_workers})

            profile = self._backend.me()
            if profile.get("status") != "active":
                raise RuntimeError("SUBSCRIPTION_INACTIVE: Your account is waiting for activation or has expired")
            self._backend.ensure_device()
            self._backend_error = None

            self._executor = ThreadPoolExecutor(max_workers=self._num_workers)
            for i in range(self._num_workers):
                self._worker_futures.append(
                    self._executor.submit(self._processor_loop)
                )

            self._recorder = AudioRecorder(
                config=self._config.audio,
                callback=self._audio_callback,
            )
            self._recorder.start()

            with self._state_lock:
                self._state = PipelineState.RUNNING
            event_bus.emit("state_changed", PipelineState.RUNNING, "")
            event_bus.emit("pipeline_started")
        except BackendApiError as e:
            logger.error("Start failed", exc_info=e)
            if e.code in {"AUTH_REQUIRED", "EMAIL_NOT_VERIFIED", "SUBSCRIPTION_INACTIVE", "DEVICE_REVOKED", "DEVICE_LIMIT_REACHED"}:
                event_bus.emit("access_denied", e.code, str(e))
            with self._state_lock:
                self._state = PipelineState.ERROR
            event_bus.emit("state_changed", PipelineState.ERROR, str(e))
            event_bus.emit("error_occurred", str(e))
        except Exception as e:
            logger.error("Start failed", exc_info=e)
            with self._state_lock:
                self._state = PipelineState.ERROR
            event_bus.emit("state_changed", PipelineState.ERROR, str(e))
            event_bus.emit("error_occurred", str(e))

    # ── Stop ────────────────────────────────────────────────────────
    def stop(self) -> None:
        with self._state_lock:
            if self._state in (PipelineState.IDLE, PipelineState.STOPPING):
                return
            self._state = PipelineState.STOPPING
        event_bus.emit("state_changed", PipelineState.STOPPING, "Stopping...")
        self._stop_event.set()
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_stop(self) -> None:
        try:
            self._stop_event.set()

            if self._cleanup_timer is not None:
                self._cleanup_timer.cancel()
                self._cleanup_timer = None
            if self._recorder is not None:
                self._recorder.stop()
                self._recorder = None

            for _ in range(self._num_workers):
                self._job_queue.put(None)
            if self._executor is not None:
                self._executor.shutdown(wait=True)

            self._worker_futures.clear()
            self._backend.close()
            logger.info(
                "Pipeline stopped",
                extra={
                    "session_id": self._session.session_id,
                    "sequences": self._session.sequence,
                },
            )
            with self._state_lock:
                self._state = PipelineState.IDLE
            event_bus.emit("state_changed", PipelineState.IDLE, "")
        except Exception as e:
            logger.error("Stop failed", exc_info=e)
            with self._state_lock:
                self._state = PipelineState.ERROR
            event_bus.emit("state_changed", PipelineState.ERROR, str(e))

    # ── Restart ─────────────────────────────────────────────────────
    def restart(self) -> None:
        if not self._is_state(PipelineState.RUNNING):
            logger.warning("Cannot restart: state=%s", self.state.name)
            return
        with self._state_lock:
            self._state = PipelineState.STOPPING
        event_bus.emit("state_changed", PipelineState.STOPPING, "Restarting...")
        threading.Thread(target=self._do_restart, daemon=True).start()

    def _do_restart(self) -> None:
        self._do_stop()
        self._do_start()

    # ── Cleanup ─────────────────────────────────────────────────────
    def _run_cleanup(self) -> None:
        cfg = self._config.storage
        try:
            deleted_local = self._storage.cleanup_old_files(cfg.retention_days)
            if deleted_local:
                logger.info(f"Local cleanup: removed {deleted_local} files older than {cfg.retention_days} days")

            # Cloud retention is enforced by the bucket lifecycle. Local recordings
            # remain under user control and are never deleted based on cloud policy.
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

        interval_hours = cfg.cleanup_interval_hours
        self._cleanup_timer = threading.Timer(interval_hours * 3600, self._run_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    # ── Audio callback ──────────────────────────────────────────────
    def _audio_callback(self, audio: np.ndarray) -> None:
        with self._state_lock:
            if self._state != PipelineState.RUNNING:
                return
        self._process_vad_frame(audio)

    def _process_vad_frame(self, audio: np.ndarray) -> None:
        sr = self._recorder.sample_rate if self._recorder and self._recorder.sample_rate > 0 else self._config.audio.sample_rate
        frame_size = self._config.audio.frame_size
        vad_cfg = self._config.vad

        min_silence_frames = int(
            vad_cfg.min_silence_duration_ms * sr / 1000 / frame_size
        )
        min_speech_frames = int(
            vad_cfg.min_speech_duration_ms * sr / 1000 / frame_size
        )

        energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
        if energy < vad_cfg.energy_threshold:
            state = VADState.SILENCE
        else:
            state = self._vad.process(audio, sr)

        logger.debug("VAD: E=%.1f thr=%d state=%s", energy, vad_cfg.energy_threshold, state.name if hasattr(state, 'name') else str(state))

        if state == VADState.SPEECH:
            self._samples_since_speech = 0
            if not self._recording:
                self._vad_buffer = [audio]
                self._recording = True
                self._speech_frame_count = 1
            else:
                self._vad_buffer.append(audio)
                self._speech_frame_count += 1
        else:
            if self._recording:
                self._vad_buffer.append(audio)
                self._samples_since_speech += 1

                if self._samples_since_speech >= min_silence_frames:
                    if self._speech_frame_count >= min_speech_frames:
                        audio_data = np.concatenate(
                            self._vad_buffer, axis=0
                        )
                        if audio_data.dtype != np.int16:
                            audio_data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
                        job = SegmentJob(
                            audio_data=audio_data,
                            session_id=self._session.session_id,
                            sequence=self._session.next_sequence(),
                            sample_rate=sr,
                        )
                        try:
                            self._job_queue.put_nowait(job)
                        except queue.Full:
                            logger.warning("Processing queue full, dropping segment")
                    else:
                        logger.debug("Speech segment too short, discarded")
                    self._recording = False
                    self._vad_buffer.clear()
                    self._samples_since_speech = 0
                    self._speech_frame_count = 0

    # ── Processor loop (worker thread) ──────────────────────────────
    def _processor_loop(self) -> None:
        logger.info("Segment processor thread started")
        while not self._stop_event.is_set():
            try:
                job = self._job_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if job is None:
                break

            try:
                self._process_segment(job)
            except Exception:
                logger.exception(
                    "Segment processing failed",
                    extra={
                        "session": job.session_id,
                        "sequence": job.sequence,
                    },
                )

            self._job_queue.task_done()

        logger.info("Segment processor thread stopped")

    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return audio
        if audio.ndim > 1:
            audio = audio.squeeze()
        ratio = target_sr / orig_sr
        new_len = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(audio.dtype)

    @staticmethod
    def _trim_trailing_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        if len(audio) == 0:
            return audio
        threshold = 50
        frame_length = int(sample_rate * 0.032)
        if len(audio) <= frame_length:
            return audio
        audio_float = audio.astype(np.float32)
        end = len(audio)
        while end > frame_length:
            frame = audio_float[end - frame_length:end]
            if np.sqrt(np.mean(frame ** 2)) >= threshold:
                break
            end -= frame_length
        return audio[:end]

    # ── Process segment ─────────────────────────────────────────────
    def _process_segment(self, job: SegmentJob) -> None:
        tracker = LatencyTracker()
        tracker.mark("segment_received")

        queue_wait_ms = max(0.0, (time.time() - job.timestamp) * 1000)

        sid = job.session_id
        seq = job.sequence
        sr = job.sample_rate

        audio_data = job.audio_data
        peak = np.abs(audio_data).max()
        if 0 < peak < 5000:
            gain = 30000.0 / peak
            audio_data = (audio_data.astype(np.float32) * gain).clip(-32768, 32767).astype(np.int16)

        sr = TARGET_SR
        audio_data = self._resample(audio_data, job.sample_rate, sr)

        segment_rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        if segment_rms < 50:
            return

        audio_data = self._trim_trailing_silence(audio_data, sr)
        duration_ms = int(len(audio_data) / sr * 1000)
        if duration_ms < 100:
            return

        buf = io.BytesIO()
        sf.write(buf, audio_data, sr, subtype="PCM_16", format="WAV")
        wav_bytes = buf.getvalue()

        audio_path = self._storage.save_audio(audio_data, sr, sid, seq)

        tracker.mark("backend_start")
        try:
            result = self._backend.process_audio(
                audio_path,
                sid,
                seq,
                self._config.translation.target_language,
                audio_bytes=wav_bytes,
            )
            self._last_backend_ok = True
            self._backend_error = None
            self._failed_audio.pop((sid, seq), None)
        except BackendApiError as exc:
            self._last_backend_ok = False
            self._backend_error = f"{exc.code}: {exc}"
            if exc.code in {"AUTH_REQUIRED", "EMAIL_NOT_VERIFIED", "SUBSCRIPTION_INACTIVE", "DEVICE_REVOKED", "DEVICE_LIMIT_REACHED"}:
                event_bus.emit("access_denied", exc.code, str(exc))
            result = ProcessingResult(
                session_id=sid,
                sequence=seq,
                audio_file=audio_path.name,
                error=exc.code,
                processing_notes=[str(exc)],
            )
            self._failed_audio[(sid, seq)] = audio_path
        tracker.mark("backend_done")

        process_ms = tracker.total_ms()
        result.latency_ms = process_ms + queue_wait_ms
        result.queue_wait_ms = queue_wait_ms

        event_bus.emit("result_ready", result)
        if result.detected_language:
            event_bus.emit("language_detected", result.detected_language)

        tracker.mark("save_result")
        self._storage.save_result(result)

        self._print_result(result)

        seg_duration = duration_ms / 1000
        logger.info(
            "Segment processed",
            extra={
                "session": sid,
                "sequence": seq,
                "audio": audio_path.name,
                "duration_s": round(seg_duration, 1),
                "latency_s": round(result.latency_ms / 1000, 1),
                "queue_wait_ms": round(queue_wait_ms, 1),
                "process_ms": round(process_ms, 1),
                "confidence": result.confidence,
                "language": result.detected_language,
                "error": result.error,
            },
        )

        if result.has_error:
            logger.warning(
                "Segment ended with error",
                extra={
                    "session": sid,
                    "sequence": seq,
                    "error": result.error,
                },
            )

    @staticmethod
    def _print_result(result: ProcessingResult) -> None:
        if sys.stdout is None:
            return
        sep = "-" * 60
        lines = [f"\n{sep}"]
        lines.append(f"  [#{result.sequence}] {result.timestamp.strftime('%H:%M:%S')}")
        lines.append(f"  LANG: {result.detected_language.upper() or '?'}  |  CONF: {result.confidence:.0%}")
        if result.transcript_restored:
            lines.append(f"  TXT:  {result.transcript_restored}")
        if result.translation:
            lines.append(f"  TRN:  {result.translation}")
        if result.corrections:
            for c in result.corrections:
                lines.append(f"  ! {c}")
        if result.uncertain_segments:
            lines.append(f"  UNCERTAIN: {', '.join(result.uncertain_segments)}")
        if result.error:
            lines.append(f"  ERROR: {result.error}")
        if result.latency_ms:
            process_ms = result.latency_ms - result.queue_wait_ms
            if result.queue_wait_ms > 0:
                lines.append(f"  LATENCY: {result.latency_ms:.0f}ms (process: {process_ms:.0f}ms | queue: {result.queue_wait_ms:.0f}ms)")
            else:
                lines.append(f"  LATENCY: {result.latency_ms:.0f}ms")
        lines.append(f"{sep}\n")
        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()

    # ── Batch processing ────────────────────────────────────────────
    def process_file(self, file_path: str | Path) -> ProcessingResult:
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return ProcessingResult(
                session_id=self._session.session_id,
                sequence=0,
                audio_file=file_path.name,
                error="file_not_found",
            )

        audio, sr = sf.read(str(file_path))

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        target_sr = 16000
        if sr != target_sr:
            ratio = target_sr / sr
            new_len = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_len)
            audio = np.interp(indices, np.arange(len(audio)), audio)
            sr = target_sr

        peak = np.abs(audio).max()
        if peak > 0.99:
            audio = audio / peak * 0.95

        audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)

        seq = self._session.next_sequence()
        sid = self._session.session_id

        audio_path = self._storage.save_audio(audio_int16, sr, sid, seq)

        return self._process_segment_sync(audio_path, sid, seq)

    def _process_segment_sync(self, audio_path: Path, sid: str, seq: int) -> ProcessingResult:
        tracker = LatencyTracker()
        tracker.mark("start")

        tracker.mark("backend_start")
        result = self._backend.process_audio(
            audio_path, sid, seq, self._config.translation.target_language
        )
        tracker.mark("backend_done")

        result.latency_ms = tracker.total_ms()

        self._print_result(result)
        self._storage.save_result(result)

        logger.info(
            "Batch file processed",
            extra={
                "file": audio_path.name,
                "session": sid,
                "sequence": seq,
                "latency_ms": round(result.latency_ms, 1),
                "confidence": result.confidence,
                "language": result.detected_language,
                "error": result.error,
            },
        )

        return result

    # ── Status ──────────────────────────────────────────────────────
    def get_status(self) -> dict:
        with self._state_lock:
            running = self._state in (PipelineState.RUNNING, PipelineState.STARTING)
        return {
            "running": running,
            "session_id": self._session.session_id,
            "sequences_processed": self._session.sequence,
            "elapsed_seconds": round(self._session.elapsed_seconds, 1),
            "recording": self._recording,
            "queue_size": self._job_queue.qsize(),
            "vad_backend": self._vad.name,
            "backend_enabled": bool(self._config.backend.api_url),
            "backend_ready": self._backend.ready,
            "backend_error": self._backend_error,
            "backend_last_request_ok": self._last_backend_ok,
        }

    def get_account(self) -> dict:
        return self._backend.me()

    def list_devices(self) -> list[dict]:
        return self._backend.list_devices()

    def revoke_device(self, device_id: str) -> None:
        self._backend.revoke_device(device_id)

    def sign_out(self) -> None:
        self._backend.sign_out()

    def shutdown(self, timeout: float = 15.0) -> bool:
        """Stop all pipeline work and wait for cleanup before an account switch."""
        self.stop()
        deadline = time.monotonic() + timeout
        while self.state not in (PipelineState.IDLE, PipelineState.ERROR):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
        self._failed_audio.clear()
        return self.state == PipelineState.IDLE

    def retry_last_failed(self) -> bool:
        if not self._failed_audio:
            return False
        (sid, seq), audio_path = next(reversed(self._failed_audio.items()))
        threading.Thread(target=self._retry_failed, args=(audio_path, sid, seq), daemon=True).start()
        return True

    def _retry_failed(self, audio_path: Path, sid: str, seq: int) -> None:
        try:
            result = self._backend.process_audio(
                audio_path, sid, seq, self._config.translation.target_language
            )
            self._storage.save_result(result)
            self._failed_audio.pop((sid, seq), None)
            self._last_backend_ok = True
            self._backend_error = None
            event_bus.emit("result_ready", result)
            if result.detected_language:
                event_bus.emit("language_detected", result.detected_language)
        except BackendApiError as exc:
            self._last_backend_ok = False
            self._backend_error = f"{exc.code}: {exc}"
            if exc.code in {"AUTH_REQUIRED", "EMAIL_NOT_VERIFIED", "SUBSCRIPTION_INACTIVE", "DEVICE_REVOKED", "DEVICE_LIMIT_REACHED"}:
                event_bus.emit("access_denied", exc.code, str(exc))
            event_bus.emit("error_occurred", self._backend_error)
