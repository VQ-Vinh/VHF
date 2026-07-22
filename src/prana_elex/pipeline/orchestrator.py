from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from pathlib import Path

import numpy as np

from prana_elex.audio.recorder import AudioRecorder
from prana_elex.config.schema import AppConfig
from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.pipeline.audio_utils import split_audio_buffer
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.pipeline.segment_processor import SegmentJob, SegmentProcessor
from prana_elex.storage.local import LocalStorage
from prana_elex.common.logger import get_logger
from prana_elex.vad.base import VADBackend, VADState
from prana_elex.vad.silero import SileroVAD
from prana_elex.vad.webrtc import WebRTCVAD
from prana_elex.pipeline.session import SessionManager
from prana_elex.pipeline.events import event_bus

logger = get_logger(__name__)

SpeechBuffer = list[np.ndarray]


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
            config.backend.google_oauth_client_id,
        )
        self._segment_processor = SegmentProcessor(config, self._backend, self._storage)
        self._vad = self._create_vad()

        self._vad_buffer: SpeechBuffer = []
        self._vad_sample_count = 0
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
        self._vad_sample_count = 0
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
            self._segment_processor.backend_error = None

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
            if e.code in {"AUTH_REQUIRED", "EMAIL_NOT_VERIFIED", "SUBSCRIPTION_INACTIVE", "DEVICE_REVOKED", "DEVICE_LIMIT_REACHED", "STATION_REVOKED", "STATION_NOT_PAIRED"}:
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

            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None

            self._worker_futures.clear()
            # Workers exit after observing _stop_event. Pending jobs and any
            # shutdown sentinels must never leak into the next start/restart.
            self._job_queue = queue.Queue(maxsize=32)
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
        # _do_stop sets this flag so workers can exit. A restart must clear it
        # before creating the replacement worker pool.
        self._stop_event.clear()
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
                self._vad_sample_count = len(audio)
                self._recording = True
                self._speech_frame_count = 1
            else:
                self._vad_buffer.append(audio)
                self._vad_sample_count += len(audio)
                self._speech_frame_count += 1
            self._flush_max_duration_segments(sr, state, frame_size)
        else:
            if self._recording:
                self._vad_buffer.append(audio)
                self._vad_sample_count += len(audio)
                self._samples_since_speech += 1
                self._flush_max_duration_segments(sr, state, frame_size)

                if self._samples_since_speech >= min_silence_frames:
                    if self._speech_frame_count >= min_speech_frames:
                        self._enqueue_audio_data(
                            np.concatenate(self._vad_buffer, axis=0), sr
                        )
                    else:
                        logger.debug("Speech segment too short, discarded")
                    self._recording = False
                    self._vad_buffer.clear()
                    self._vad_sample_count = 0
                    self._samples_since_speech = 0
                    self._speech_frame_count = 0

    def _flush_max_duration_segments(
        self, sample_rate: int, state: VADState, frame_size: int
    ) -> None:
        max_samples = int(
            sample_rate * self._config.vad.max_segment_duration_ms / 1000
        )
        if self._vad_sample_count < max_samples:
            return

        chunks, remainder = split_audio_buffer(self._vad_buffer, max_samples)
        for chunk in chunks:
            self._enqueue_audio_data(chunk, sample_rate)

        self._vad_buffer = remainder
        self._vad_sample_count = sum(len(part) for part in remainder)
        if state == VADState.SPEECH:
            self._samples_since_speech = 0
            self._speech_frame_count = 1 if self._vad_sample_count else 0
        else:
            self._samples_since_speech = (
                (self._vad_sample_count + frame_size - 1) // frame_size
            )
            self._speech_frame_count = 0

    def _enqueue_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> None:
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
        job = SegmentJob(
            audio_data=audio_data,
            session_id=self._session.session_id,
            sequence=self._session.next_sequence(),
            sample_rate=sample_rate,
        )
        try:
            self._job_queue.put_nowait(job)
        except queue.Full:
            logger.warning("Processing queue full, dropping segment")

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

    # ── Process segment ─────────────────────────────────────────────
    def _process_segment(self, job: SegmentJob) -> None:
        self._segment_processor.process(job)

    # ── Batch processing ────────────────────────────────────────────
    def process_file(self, file_path: str | Path) -> ProcessingResult:
        path = Path(file_path)
        sequence = self._session.next_sequence() if path.exists() else 0
        return self._segment_processor.process_file(
            path,
            self._session.session_id,
            sequence,
        )

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
            "backend_error": self._segment_processor.backend_error,
            "backend_last_request_ok": self._segment_processor.last_backend_ok,
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
        self._segment_processor.clear_failures()
        return self.state == PipelineState.IDLE

    def retry_last_failed(self) -> bool:
        return self._segment_processor.retry_last_failed()
