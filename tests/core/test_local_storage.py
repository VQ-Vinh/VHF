from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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


def _saved_audio(tmp_path, timezone_name: str):
    storage = LocalStorage(
        LocalStorageConfig(
            audio_dir=tmp_path / "audio",
            result_dir=tmp_path / "results",
            timezone=timezone_name,
        )
    )
    path = storage.save_audio(np.ones(1600, dtype=np.int16), 16000, "session001", 1)
    return storage, path


def test_audio_is_stored_under_the_configured_timezone_date(tmp_path) -> None:
    # Kiritimati (UTC+14) and Midway (UTC-11) are 25 hours apart, so their
    # local dates always differ -- at least one differs from this host's date.
    seen = {}
    for index, zone in enumerate(("Pacific/Kiritimati", "Pacific/Midway")):
        storage, path = _saved_audio(tmp_path / str(index), zone)
        expected = datetime.now(ZoneInfo(zone)).strftime("%Y%m%d")
        assert path.name.startswith(expected)
        assert path.relative_to(storage.audio_dir).parts[:3] == (
            expected[:4],
            expected[4:6],
            expected[6:],
        )
        seen[zone] = expected
    assert seen["Pacific/Kiritimati"] != seen["Pacific/Midway"]


def test_date_folder_always_matches_the_filename(tmp_path) -> None:
    # Guards the midnight race: reading the clock once for the name and again
    # for the folder can file a recording under the previous day.
    storage, path = _saved_audio(tmp_path, "Pacific/Kiritimati")
    folder = "".join(path.relative_to(storage.audio_dir).parts[:3])
    assert folder == path.name[:8]


def test_unknown_timezone_falls_back_to_the_system_clock(tmp_path) -> None:
    storage, path = _saved_audio(tmp_path, "Not/AZone")
    assert path.name.startswith(datetime.now().strftime("%Y%m%d"))
