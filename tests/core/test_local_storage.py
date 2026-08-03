from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import numpy as np

from prana_core.config.schema import LocalStorageConfig
from prana_core.pipeline.models import ProcessingResult
from prana_core.storage.local import LocalStorage


def _storage(tmp_path) -> LocalStorage:
    return LocalStorage(
        LocalStorageConfig(
            audio_dir=tmp_path / "audio",
            result_dir=tmp_path / "results",
        )
    )


def test_cleanup_removes_expired_files_and_empty_date_folders(tmp_path) -> None:
    storage = _storage(tmp_path)
    old_directory = storage.audio_dir / "2026" / "07" / "01"
    old_directory.mkdir(parents=True)
    expired = old_directory / "legacy-name.wav"
    expired.write_bytes(b"wav")
    old_timestamp = (datetime.now() - timedelta(days=15)).timestamp()
    os.utime(expired, (old_timestamp, old_timestamp))

    recent_directory = storage.result_dir / "2026" / "08" / "03"
    recent_directory.mkdir(parents=True)
    recent = recent_directory / "recent.json"
    recent.write_text("{}", encoding="utf-8")

    assert storage.cleanup_old_files(14) == 1
    assert not expired.exists()
    assert not old_directory.exists()
    assert recent.exists()
    assert storage.audio_dir.exists()
    assert storage.result_dir.exists()


def test_result_filename_matches_timestamped_local_audio(tmp_path) -> None:
    storage = _storage(tmp_path)
    audio_path = storage.save_audio(
        np.ones(1600, dtype=np.int16),
        16000,
        "session001",
        7,
    )
    result = ProcessingResult(
        session_id="session001",
        sequence=7,
        audio_file=audio_path.name,
        transcript_restored="Test",
    )

    result_path = storage.save_result(result)

    assert result_path.stem == audio_path.stem
    assert result_path.name != "session001_0007.json"
    assert json.loads(result_path.read_text(encoding="utf-8"))["audio_file"] == audio_path.name
