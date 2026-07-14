from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from prana_elex.config.schema import LocalStorageConfig
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.common.logger import get_logger

logger = get_logger(__name__)


class LocalStorage:
    def __init__(self, config: LocalStorageConfig):
        self._config = config
        self._audio_dir = Path(config.audio_dir)
        self._result_dir = Path(config.result_dir)
        self._ensure_dirs()

    @property
    def audio_dir(self) -> Path:
        return self._audio_dir

    @property
    def result_dir(self) -> Path:
        return self._result_dir

    def _ensure_dirs(self) -> None:
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._result_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _date_subdir() -> str:
        now = datetime.now()
        return f"{now.year:04d}/{now.month:02d}/{now.day:02d}"

    def save_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        session_id: str,
        sequence: int,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{sequence:04d}.wav"
        subdir = self._date_subdir()
        filepath = self._audio_dir / subdir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if audio_data.dtype != np.int16:
            if audio_data.dtype == np.float32:
                audio_data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        sf.write(str(filepath), audio_data, sample_rate)
        logger.info(f"Audio saved: {filepath.name} ({len(audio_data) / sample_rate:.1f}s)")

        return filepath

    def save_result(self, result: ProcessingResult) -> Path:
        try:
            subdir = self._date_subdir()
            filepath = self._result_dir / subdir / result.json_path
            filepath.parent.mkdir(parents=True, exist_ok=True)

            data = result.model_dump(exclude={
                "session_id",
                "sequence",
                "uncertain_segments",
                "processing_notes",
                "latency_ms",
                "queue_wait_ms",
            })
            if data.get("confidence") is not None:
                data["confidence"] = round(data["confidence"], 2)
            data.pop("corrections", None)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Result saved: {filepath}")
            return filepath
        except Exception:
            logger.exception("save_result failed")
            raise

    def get_audio_path(self, session_id: str, sequence: int) -> Path | None:
        pattern = f"*_{sequence:04d}.wav"
        matches = list(self._audio_dir.rglob(pattern))
        return matches[0] if matches else None

    def get_result_path(self, session_id: str, sequence: int) -> Path | None:
        pattern = f"*_{sequence:04d}.json"
        matches = list(self._result_dir.rglob(pattern))
        return matches[0] if matches else None

    def cleanup_old_files(self, max_days: int = 30) -> int:
        import time
        from datetime import datetime, timedelta

        threshold_date = datetime.now() - timedelta(days=max_days)
        threshold_ts = time.time() - (max_days * 86400)
        count = 0

        for path in list(self._audio_dir.rglob("*")) + list(self._result_dir.rglob("*")):
            if not path.is_file():
                continue
            try:
                stem = path.stem
                date_part = stem.split("_", 2)[:2]
                if len(date_part) == 2:
                    file_dt = datetime.strptime(f"{date_part[0]}_{date_part[1]}", "%Y%m%d_%H%M%S")
                    if file_dt < threshold_date:
                        path.unlink()
                        count += 1
                else:
                    if path.stat().st_mtime < threshold_ts:
                        path.unlink()
                        count += 1
            except (ValueError, OSError):
                if path.stat().st_mtime < threshold_ts:
                    path.unlink()
                    count += 1

        if count:
            logger.info(f"Cleaned up {count} old files (> {max_days} days)")

        return count
