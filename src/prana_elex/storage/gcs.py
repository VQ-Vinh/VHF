from __future__ import annotations

import asyncio
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prana_elex.config.schema import GCSStorageConfig, LocalStorageConfig
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.common.logger import get_logger
from prana_elex.common.google_credentials import load_google_credentials

logger = get_logger(__name__)

RETRY_INTERVAL = 30


class GCSStorage:
    def __init__(
        self,
        config: GCSStorageConfig,
        local_config: LocalStorageConfig | None = None,
        credentials_path: str = "",
    ):
        self._config = config
        self._client = None
        self._bucket = None
        self._last_error: str | None = None
        self._last_upload_ok: bool | None = None
        self._audio_dir: Path | None = None
        self._result_dir: Path | None = None
        self._credentials_path = credentials_path
        if local_config is not None:
            self._audio_dir = Path(local_config.audio_dir)
            self._result_dir = Path(local_config.result_dir)
        self._retry_queue: deque[tuple[Path, str]] = deque()
        self._retry_timer: threading.Timer | None = None
        self._lock = threading.RLock()
        if config.enabled:
            self._init_client()

    @property
    def ready(self) -> bool:
        return self._client is not None and self._bucket is not None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_upload_ok(self) -> bool | None:
        with self._lock:
            return self._last_upload_ok

    def _init_client(self) -> None:
        try:
            from google.cloud import storage
        except ImportError as e:
            self._last_error = "google-cloud-storage not installed. Install with: pip install google-cloud-storage"
            logger.warning(self._last_error)
            return

        try:
            credentials, project, _ = load_google_credentials(self._credentials_path)
            self._client = storage.Client(project=project, credentials=credentials)

            self._bucket = self._client.bucket(self._config.bucket_name)
            self._last_error = None
            logger.info(
                "GCS initialized with service-account JSON: bucket=%s",
                self._config.bucket_name,
            )

        except Exception as e:
            err_msg = str(e)
            if "not found" in err_msg.lower() or "404" in err_msg:
                self._last_error = (
                    f"GCS bucket '{self._config.bucket_name}' not found. "
                    f"Create it or update bucket_name in config."
                )
            elif "forbidden" in err_msg.lower() or "403" in err_msg:
                self._last_error = (
                    f"GCS: no permission to access bucket '{self._config.bucket_name}'. "
                    f"Check IAM permissions."
                )
            else:
                self._last_error = f"GCS init failed: {err_msg}"
            logger.error(self._last_error)
            self._client = None
            self._bucket = None

    @staticmethod
    def _date_path() -> str:
        now = datetime.now()
        return f"{now.year:04d}/{now.month:02d}/{now.day:02d}"

    @staticmethod
    def _build_path(*parts: str) -> str:
        return "/".join(p for p in parts if p)

    def cleanup_old_files(self, max_days: int) -> int:
        if self._client is None or self._bucket is None:
            return 0

        threshold = datetime.now(timezone.utc) - timedelta(days=max_days)
        count = 0
        prefixes = ["audio", "results"]

        for subdir in prefixes:
            prefix = self._build_path(self._config.prefix, subdir) + "/"
            for blob in self._bucket.list_blobs(prefix=prefix):
                if blob.time_created and blob.time_created < threshold:
                    blob.delete()
                    count += 1

        if count:
            logger.info(f"Cleaned up {count} old GCS files (> {max_days} days)")
        return count

    def _process_retry_queue(self) -> None:
        if self._client is None or self._bucket is None:
            return
        with self._lock:
            remaining: deque[tuple[Path, str]] = deque()
            while self._retry_queue:
                local_path, remote_path = self._retry_queue.popleft()
                if not local_path.exists():
                    logger.warning(f"File removed before retry: {local_path.name}")
                    continue
                try:
                    blob = self._bucket.blob(remote_path)
                    blob.upload_from_filename(str(local_path))
                    logger.info(f"Retry uploaded to GCS: gs://{self._config.bucket_name}/{remote_path}")
                except Exception as e:
                    logger.warning(f"Retry upload failed for {local_path.name}: {e}")
                    remaining.append((local_path, remote_path))

            self._retry_queue = remaining
            if self._retry_queue:
                self._last_upload_ok = False
                self._start_retry_timer()
            else:
                self._last_upload_ok = True
                logger.info("GCS retry queue empty, timer stopped")

    def _start_retry_timer(self) -> None:
        with self._lock:
            self._stop_retry_timer()
            self._retry_timer = threading.Timer(RETRY_INTERVAL, self._retry_timer_tick)
            self._retry_timer.daemon = True
            self._retry_timer.start()

    def _stop_retry_timer(self) -> None:
        with self._lock:
            if self._retry_timer is not None:
                self._retry_timer.cancel()
                self._retry_timer = None

    def _retry_timer_tick(self) -> None:
        self._process_retry_queue()

    @property
    def retry_queue_size(self) -> int:
        with self._lock:
            return len(self._retry_queue)

    def upload_file(self, local_path: str | Path, remote_path: str | None = None) -> bool:
        if self._client is None or self._bucket is None:
            logger.warning("GCS not configured, skipping upload")
            return False

        local_path = Path(local_path)
        if not local_path.exists():
            logger.error(f"File not found for GCS upload: {local_path}")
            return False

        if remote_path is None:
            remote_path = self._build_path(
                self._config.prefix,
                self._date_path(),
                local_path.name,
            )

        try:
            blob = self._bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            logger.info(f"Uploaded to GCS: gs://{self._config.bucket_name}/{remote_path}")
            return True
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return False

    async def upload_file_async(self, local_path: str | Path, remote_path: str | None = None) -> bool:
        return await asyncio.to_thread(self.upload_file, local_path, remote_path)

    def upload_result(self, result: ProcessingResult) -> tuple[bool, bool]:
        if not result.audio_file or not result.audio_file.strip():
            logger.error(f"Empty audio_file in result (session={result.session_id}, seq={result.sequence})")
            with self._lock:
                self._last_upload_ok = False
            return False, False
        if not result.json_path or not result.json_path.strip():
            logger.error(f"Empty json_path in result (session={result.session_id}, seq={result.sequence})")
            with self._lock:
                self._last_upload_ok = False
            return False, False

        audio_file = (
            next(Path(self._audio_dir).rglob(result.audio_file), None)
            if self._audio_dir
            else Path(result.audio_file)
        )
        result_file = (
            next(Path(self._result_dir).rglob(result.json_path), None)
            if self._result_dir
            else Path(result.json_path)
        )

        if audio_file is None or result_file is None:
            logger.error(f"Local files not found for GCS upload (audio={result.audio_file}, result={result.json_path})")
            with self._lock:
                self._last_upload_ok = False
            return False, False

        date_path = self._date_path()
        audio_remote = self._build_path(self._config.prefix, "audio", date_path, audio_file.name)
        result_remote = self._build_path(self._config.prefix, "results", date_path, result_file.name)

        with self._lock:
            self._process_retry_queue()

            audio_ok = self.upload_file(audio_file, audio_remote)
            if not audio_ok:
                self._retry_queue.append((audio_file, audio_remote))

            result_ok = self.upload_file(result_file, result_remote)
            if not result_ok:
                self._retry_queue.append((result_file, result_remote))

            if not audio_ok or not result_ok:
                self._start_retry_timer()

            self._last_upload_ok = audio_ok and result_ok

        return audio_ok, result_ok

    async def upload_result_async(self, result: ProcessingResult) -> tuple[bool, bool]:
        return await asyncio.to_thread(self.upload_result, result)

    def close(self) -> None:
        self._stop_retry_timer()
        if self._client:
            self._client.close()
            logger.info("GCS client closed")
