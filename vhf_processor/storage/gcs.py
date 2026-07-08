from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from vhf_processor.config.schema import GCSStorageConfig, LocalStorageConfig
from vhf_processor.models.result import ProcessingResult
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)


class GCSStorage:
    def __init__(self, config: GCSStorageConfig, local_config: LocalStorageConfig | None = None):
        self._config = config
        self._client = None
        self._bucket = None
        self._audio_dir: Path | None = None
        self._result_dir: Path | None = None
        if local_config is not None:
            self._audio_dir = Path(local_config.audio_dir)
            self._result_dir = Path(local_config.result_dir)
        if config.enabled:
            self._init_client()

    def _init_client(self) -> None:
        try:
            from google.cloud import storage

            if self._config.credentials_path:
                self._client = storage.Client.from_service_account_json(
                    self._config.credentials_path
                )
            else:
                self._client = storage.Client()

            self._bucket = self._client.bucket(self._config.bucket_name)
            logger.info(
                f"GCS initialized: bucket={self._config.bucket_name}"
            )
        except ImportError:
            logger.warning(
                "google-cloud-storage not installed. "
                "Install with: pip install google-cloud-storage"
            )
            self._client = None
        except Exception as e:
            logger.warning(f"Failed to initialize GCS: {e}")
            self._client = None

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

        threshold = datetime.now() - timedelta(days=max_days)
        count = 0
        prefixes = ["audio", "results"]

        for subdir in prefixes:
            prefix = self._build_path(self._config.prefix, subdir) + "/"
            for blob in self._bucket.list_blobs(prefix=prefix):
                if blob.time_created and blob.time_created.replace(tzinfo=None) < threshold:
                    blob.delete()
                    count += 1

        if count:
            logger.info(f"Cleaned up {count} old GCS files (> {max_days} days)")
        return count

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

    def upload_file_async(self, local_path: str | Path, remote_path: str | None = None) -> bool:
        return self.upload_file(local_path, remote_path)

    def upload_result(self, result: ProcessingResult) -> tuple[bool, bool]:
        audio_file = (
            self._audio_dir / result.audio_file
            if self._audio_dir
            else Path(result.audio_file)
        )
        result_file = (
            self._result_dir / result.json_path
            if self._result_dir
            else Path(result.json_path)
        )

        date_path = self._date_path()
        audio_remote = self._build_path(self._config.prefix, "audio", date_path, audio_file.name)
        result_remote = self._build_path(self._config.prefix, "results", date_path, result_file.name)

        audio_ok = self.upload_file(audio_file, audio_remote)
        result_ok = self.upload_file(result_file, result_remote)

        return audio_ok, result_ok

    async def upload_result_async(self, result: ProcessingResult) -> tuple[bool, bool]:
        return await asyncio.to_thread(self.upload_result, result)

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("GCS client closed")
