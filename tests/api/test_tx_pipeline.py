from __future__ import annotations

import io
import wave
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from services.prana_api.tx_audio import append_over
from services.prana_api.tx_repository import MemoryTxRepository


def wav(frames: int, rate: int = 24_000) -> bytes:
    target = io.BytesIO()
    with wave.open(target, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"\x01\x00" * frames)
    return target.getvalue()


def job(job_id: str = "job-1") -> dict:
    return {
        "id": job_id,
        "uid": "user-1",
        "station_id": "station-1",
        "status": "review_ready",
        "duration_ms": 1000,
        "target_language": "vi",
        "detected_language": "en",
        "transcript": "Channel eighteen",
        "translation": "Kênh mười tám",
        "source_object": "source.wav",
        "output_object": "output.wav",
        "error": None,
        "attempt": 1,
        "retry_of": None,
        "created_at": datetime.now(timezone.utc),
    }


def test_append_over_adds_300ms_silence_and_both_clips() -> None:
    combined = append_over(wav(2400), wav(1200))
    with wave.open(io.BytesIO(combined), "rb") as result:
        assert result.getframerate() == 24_000
        assert result.getnchannels() == 1
        assert result.getnframes() == 2400 + 7200 + 1200


def test_tx_queue_claims_once_and_never_requeues_failed_job() -> None:
    repository = MemoryTxRepository()
    repository.create(job())
    repository.confirm("user-1", "station-1", "job-1")
    assert repository.claim("station-1")["status"] == "claimed"
    assert repository.claim("station-1") is None
    repository.station_update("station-1", "job-1", "failed", "OUTPUT_FAILED")
    assert repository.claim("station-1") is None


def test_stale_active_tx_expires_once_and_rejects_late_completion() -> None:
    repository = MemoryTxRepository()
    repository.create(job())
    repository.confirm("user-1", "station-1", "job-1")
    repository.claim("station-1")
    repository.station_update("station-1", "job-1", "transmitting")

    now = datetime.now(timezone.utc)
    assert repository.expire_stale_active("station-1", False, now) is None
    expired = repository.expire_stale_active("station-1", True, now)
    assert expired is not None
    assert expired["status"] == "failed"
    assert expired["error"] == "STATION_OFFLINE_DURING_TX"
    assert repository.expire_stale_active("station-1", True, now) is None

    with pytest.raises(HTTPException) as error:
        repository.station_update("station-1", "job-1", "completed")
    assert error.value.detail["code"] == "TX_INVALID_STATE"

    repository.create(job("job-2"))
    repository.confirm("user-1", "station-1", "job-2")


def test_active_tx_lease_expires_after_station_reconnects() -> None:
    repository = MemoryTxRepository()
    value = job()
    value["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=3)
    repository.create(value)
    repository.confirm("user-1", "station-1", "job-1")
    repository.claim("station-1")
    repository.items["job-1"]["claimed_at"] = datetime.now(
        timezone.utc
    ) - timedelta(seconds=91)

    expired = repository.expire_stale_active(
        "station-1", False, datetime.now(timezone.utc)
    )

    assert expired is not None
    assert expired["status"] == "failed"
    assert expired["error"] == "STATION_OFFLINE_DURING_TX"


def test_one_active_tx_job_per_station_and_manual_retry_attempt() -> None:
    repository = MemoryTxRepository()
    repository.create(job())
    repository.confirm("user-1", "station-1", "job-1")
    repository.create(job("job-2"))
    with pytest.raises(HTTPException) as error:
        repository.confirm("user-1", "station-1", "job-2")
    assert error.value.detail["code"] == "TX_BUSY"

    repository.claim("station-1")
    repository.station_update("station-1", "job-1", "failed", "OUTPUT_FAILED")
    retried = repository.retry("user-1", "station-1", "job-1", "job-3")
    assert retried["status"] == "review_ready"
    assert retried["attempt"] == 2
    assert retried["retry_of"] == "job-1"


def test_tx_filename_sequence_is_daily_and_independent() -> None:
    repository = MemoryTxRepository()
    created_at = datetime(2026, 8, 5, 15, 59, 23, tzinfo=timezone.utc)

    assert repository.next_filename("station-1", created_at) == "20260805_155923_0001.wav"
    assert repository.next_filename("station-1", created_at) == "20260805_155923_0002.wav"
    assert repository.next_filename("station-2", created_at) == "20260805_155923_0001.wav"
