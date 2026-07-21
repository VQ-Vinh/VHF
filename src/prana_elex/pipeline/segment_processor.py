from __future__ import annotations

import io
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.common.logger import get_logger
from prana_elex.common.timing import LatencyTracker
from prana_elex.config.schema import AppConfig
from prana_elex.pipeline.audio_utils import resample_audio, trim_trailing_silence
from prana_elex.pipeline.events import event_bus
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.storage.local import LocalStorage


logger = get_logger(__name__)
TARGET_SAMPLE_RATE = 16000
ACCESS_ERROR_CODES = {
    "AUTH_REQUIRED",
    "EMAIL_NOT_VERIFIED",
    "SUBSCRIPTION_INACTIVE",
    "DEVICE_REVOKED",
    "DEVICE_LIMIT_REACHED",
}
QUOTA_ERROR_CODES = {"DAILY_QUOTA_EXCEEDED", "MONTHLY_QUOTA_EXCEEDED"}


@dataclass
class SegmentJob:
    audio_data: np.ndarray
    session_id: str
    sequence: int
    sample_rate: int
    timestamp: float = field(default_factory=time.time)


class SegmentProcessor:
    """Process, persist and retry individual speech segments."""

    def __init__(self, config: AppConfig, backend: BackendClient, storage: LocalStorage):
        self._config = config
        self._backend = backend
        self._storage = storage
        self.backend_error: str | None = None
        self.last_backend_ok: bool | None = None
        self._failed_audio: dict[tuple[str, int], Path] = {}

    def process(self, job: SegmentJob) -> ProcessingResult | None:
        tracker = LatencyTracker()
        tracker.mark("segment_received")
        queue_wait_ms = max(0.0, (time.time() - job.timestamp) * 1000)
        sid, seq = job.session_id, job.sequence

        audio_data = job.audio_data
        peak = np.abs(audio_data).max()
        if 0 < peak < 5000:
            gain = 30000.0 / peak
            audio_data = (audio_data.astype(np.float32) * gain).clip(-32768, 32767).astype(np.int16)

        audio_data = resample_audio(audio_data, job.sample_rate, TARGET_SAMPLE_RATE)
        segment_rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        if segment_rms < 50:
            return None

        audio_data = trim_trailing_silence(audio_data, TARGET_SAMPLE_RATE)
        duration_ms = int(len(audio_data) / TARGET_SAMPLE_RATE * 1000)
        if duration_ms < 100:
            return None

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, TARGET_SAMPLE_RATE, subtype="PCM_16", format="WAV")
        audio_path = self._storage.save_audio(audio_data, TARGET_SAMPLE_RATE, sid, seq)

        tracker.mark("backend_start")
        try:
            result = self._backend.process_audio(
                audio_path,
                sid,
                seq,
                self._config.translation.target_language,
                audio_bytes=buffer.getvalue(),
            )
            self.last_backend_ok = True
            self.backend_error = None
            self._failed_audio.pop((sid, seq), None)
        except BackendApiError as exc:
            self.last_backend_ok = False
            self.backend_error = f"{exc.code}: {exc}"
            self._emit_access_error(exc)
            self._emit_quota_error(exc)
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
        self._publish_result(result)
        self._storage.save_result(result)
        self.print_result(result)

        logger.info(
            "Segment processed",
            extra={
                "session": sid,
                "sequence": seq,
                "audio": audio_path.name,
                "duration_s": round(duration_ms / 1000, 1),
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
                extra={"session": sid, "sequence": seq, "error": result.error},
            )
        return result

    def process_file(self, file_path: str | Path, session_id: str, sequence: int) -> ProcessingResult:
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found: %s", path)
            return ProcessingResult(
                session_id=session_id,
                sequence=0,
                audio_file=path.name,
                error="file_not_found",
            )

        audio, sample_rate = sf.read(str(path))
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = resample_audio(audio, sample_rate, TARGET_SAMPLE_RATE)
        peak = np.abs(audio).max()
        if peak > 0.99:
            audio = audio / peak * 0.95
        audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        audio_path = self._storage.save_audio(
            audio_int16, TARGET_SAMPLE_RATE, session_id, sequence
        )
        return self._process_saved_file(audio_path, session_id, sequence)

    def _process_saved_file(self, audio_path: Path, session_id: str, sequence: int) -> ProcessingResult:
        tracker = LatencyTracker()
        tracker.mark("start")
        tracker.mark("backend_start")
        result = self._backend.process_audio(
            audio_path,
            session_id,
            sequence,
            self._config.translation.target_language,
        )
        tracker.mark("backend_done")
        result.latency_ms = tracker.total_ms()
        self.print_result(result)
        self._storage.save_result(result)
        logger.info(
            "Batch file processed",
            extra={
                "file": audio_path.name,
                "session": session_id,
                "sequence": sequence,
                "latency_ms": round(result.latency_ms, 1),
                "confidence": result.confidence,
                "language": result.detected_language,
                "error": result.error,
            },
        )
        return result

    def retry_last_failed(self) -> bool:
        if not self._failed_audio:
            return False
        (session_id, sequence), audio_path = next(reversed(self._failed_audio.items()))
        threading.Thread(
            target=self._retry_failed,
            args=(audio_path, session_id, sequence),
            daemon=True,
        ).start()
        return True

    def _retry_failed(self, audio_path: Path, session_id: str, sequence: int) -> None:
        try:
            result = self._backend.process_audio(
                audio_path,
                session_id,
                sequence,
                self._config.translation.target_language,
            )
            self._storage.save_result(result)
            self._failed_audio.pop((session_id, sequence), None)
            self.last_backend_ok = True
            self.backend_error = None
            self._publish_result(result)
        except BackendApiError as exc:
            self.last_backend_ok = False
            self.backend_error = f"{exc.code}: {exc}"
            self._emit_access_error(exc)
            self._emit_quota_error(exc)
            event_bus.emit("error_occurred", self.backend_error)

    def clear_failures(self) -> None:
        self._failed_audio.clear()

    @staticmethod
    def _publish_result(result: ProcessingResult) -> None:
        event_bus.emit("result_ready", result)
        if result.detected_language:
            event_bus.emit("language_detected", result.detected_language)

    @staticmethod
    def _emit_access_error(error: BackendApiError) -> None:
        if error.code in ACCESS_ERROR_CODES:
            event_bus.emit("access_denied", error.code, str(error))

    @staticmethod
    def _emit_quota_error(error: BackendApiError) -> None:
        if error.code in QUOTA_ERROR_CODES:
            event_bus.emit(
                "quota_exhausted",
                error.code,
                str(error),
                str(error.detail.get("resets_at") or ""),
            )

    @staticmethod
    def print_result(result: ProcessingResult) -> None:
        if sys.stdout is None:
            return
        separator = "-" * 60
        lines = [f"\n{separator}"]
        lines.append(f"  [#{result.sequence}] {result.timestamp.strftime('%H:%M:%S')}")
        lines.append(f"  LANG: {result.detected_language.upper() or '?'}  |  CONF: {result.confidence:.0%}")
        if result.transcript_restored:
            lines.append(f"  TXT:  {result.transcript_restored}")
        if result.translation:
            lines.append(f"  TRN:  {result.translation}")
        for correction in result.corrections:
            lines.append(f"  ! {correction}")
        if result.uncertain_segments:
            lines.append(f"  UNCERTAIN: {', '.join(result.uncertain_segments)}")
        if result.error:
            lines.append(f"  ERROR: {result.error}")
        if result.latency_ms:
            process_ms = result.latency_ms - result.queue_wait_ms
            if result.queue_wait_ms > 0:
                lines.append(
                    f"  LATENCY: {result.latency_ms:.0f}ms "
                    f"(process: {process_ms:.0f}ms | queue: {result.queue_wait_ms:.0f}ms)"
                )
            else:
                lines.append(f"  LATENCY: {result.latency_ms:.0f}ms")
        lines.append(f"{separator}\n")
        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()


__all__ = ["SegmentJob", "SegmentProcessor"]
