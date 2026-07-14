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

from prana_elex.core.audio.recorder import AudioRecorder
from prana_elex.core.config.schema import AppConfig
from prana_elex.core.gemini.client import GeminiClient
from prana_elex.core.gemini.prompt_builder import PromptBuilder
from prana_elex.core.gemini.response_parser import GeminiResponseParser
from prana_elex.core.models.result import ProcessingResult
from prana_elex.core.storage.local import LocalStorage
from prana_elex.core.storage.gcs import GCSStorage
from prana_elex.core.utils.logger import get_logger
from prana_elex.core.utils.timing import LatencyTracker
from prana_elex.core.vad.base import VADBackend, VADState
from prana_elex.core.vad.silero_vad import SileroVAD
from prana_elex.core.vad.webrtc_vad import WebRTCVAD
from prana_elex.core.pipeline.session import SessionManager
from prana_elex.core.pipeline.events import event_bus

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
    def __init__(self, config: AppConfig):
        self._config = config
        self._state = PipelineState.IDLE
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()

        self._session = SessionManager(config.general.session_prefix)
        self._storage = LocalStorage(config.storage.local)
        self._gcs = GCSStorage(config.storage.gcs, config.storage.local)
        self._vad = self._create_vad()

        self._prompt_builder = PromptBuilder(config.translation)
        self._gemini: GeminiClient | None = None

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

            if self._gemini is not None:
                self._gemini.close()
            self._gemini = GeminiClient(self._config.gemini, self._prompt_builder, GeminiResponseParser)

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

            self._run_cleanup()

            with self._state_lock:
                self._state = PipelineState.RUNNING
            event_bus.emit("state_changed", PipelineState.RUNNING, "")
            event_bus.emit("pipeline_started")
        except Exception as e:
            logger.error("Start failed", exc_info=e)
            with self._state_lock:
                self._state = PipelineState.ERROR
            event_bus.emit("state_changed", PipelineState.ERROR, str(e))
            event_bus.emit("error_occurred", str(e))

    # ── Stop ────────────────────────────────────────────────────────
    def stop(self) -> None:
        with self._state_lock:
            if self._state == PipelineState.IDLE:
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
            if self._gemini is not None:
                self._gemini.close()
                self._gemini = None
            self._gcs.close()
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

            if cfg.gcs.enabled:
                deleted_gcs = self._gcs.cleanup_old_files(cfg.retention_days)
                if deleted_gcs:
                    logger.info(f"GCS cleanup: removed {deleted_gcs} files older than {cfg.retention_days} days")
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

        tracker.mark("gemini_start")
        result = self._gemini.process_audio(audio_path, sid, seq, audio_bytes=wav_bytes)
        tracker.mark("gemini_done")

        process_ms = tracker.total_ms()
        result.latency_ms = process_ms + queue_wait_ms
        result.queue_wait_ms = queue_wait_ms

        event_bus.emit("result_ready", result)
        if result.detected_language:
            event_bus.emit("language_detected", result.detected_language)

        tracker.mark("save_result")
        self._storage.save_result(result)

        gcs_audio = None
        gcs_result = None
        gcs_pending = 0
        if self._config.storage.gcs.enabled:
            gcs_audio, gcs_result = self._gcs.upload_result(result)
            gcs_pending = self._gcs.retry_queue_size

        self._print_result(result)
        self._print_gcs_status(gcs_audio, gcs_result, gcs_pending)

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

    @staticmethod
    def _print_gcs_status(audio_ok: bool | None, result_ok: bool | None, queue_size: int = 0) -> None:
        if sys.stdout is None:
            return
        if audio_ok is None:
            return
        parts = []
        parts.append(f"  GCS: audio={'OK' if audio_ok else 'FAIL'}, result={'OK' if result_ok else 'FAIL'}")
        if queue_size:
            parts.append(f"  GCS: {queue_size} file(s) pending retry")
        sys.stdout.write("\n".join(parts) + "\n")
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

        if self._gemini is None:
            self._gemini = GeminiClient(self._config.gemini, self._prompt_builder, GeminiResponseParser)
        tracker.mark("gemini_start")
        result = self._gemini.process_audio(audio_path, sid, seq)
        tracker.mark("gemini_done")

        result.latency_ms = tracker.total_ms()

        self._print_result(result)
        self._storage.save_result(result)

        gcs_audio = None
        gcs_result = None
        gcs_pending = 0
        if self._config.storage.gcs.enabled:
            gcs_audio, gcs_result = self._gcs.upload_result(result)
            gcs_pending = self._gcs.retry_queue_size
        self._print_gcs_status(gcs_audio, gcs_result, gcs_pending)

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
            "gcs_enabled": self._config.storage.gcs.enabled,
            "gcs_ready": self._gcs.ready,
            "gcs_error": self._gcs.last_error,
            "gcs_retry_queue": self._gcs.retry_queue_size,
            "gcs_last_upload_ok": self._gcs.last_upload_ok,
        }
