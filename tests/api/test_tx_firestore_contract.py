from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from services.prana_api.tx_repository import FirestoreTxRepository


pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"),
    reason="Firestore Emulator is not running",
)


def _job(job_id: str, station_id: str) -> dict:
    return {
        "id": job_id,
        "uid": "contract-user",
        "station_id": station_id,
        "status": "review_ready",
        "duration_ms": 1000,
        "target_language": "vi",
        "detected_language": "en",
        "transcript": "Channel eighteen",
        "translation": "Kênh mười tám",
        "translation_original": "Kênh mười tám",
        "translation_edited": False,
        "audio_filename": "20260817_120000_0001.wav",
        "source_object": "source.wav",
        "output_object": "",
        "output_available": False,
        "error": None,
        "attempt": 1,
        "retry_of": None,
        "created_at": datetime.now(timezone.utc),
    }


def test_firestore_tx_repository_matches_transaction_contract() -> None:
    station_id = f"contract-{uuid.uuid4().hex}"
    job_id = uuid.uuid4().hex
    repository = FirestoreTxRepository(project="prana-ci")
    repository.create(_job(job_id, station_id))

    synthesizing = repository.begin_confirm(
        "contract-user", station_id, job_id, "Kênh 18"
    )
    assert synthesizing["status"] == "synthesizing"

    with pytest.raises(HTTPException) as cancel_error:
        repository.cancel("contract-user", station_id, job_id)
    assert cancel_error.value.detail["code"] == "TX_INVALID_STATE"

    repository.collection.document(job_id).update(
        {
            "synthesis_lease_expires_at": datetime.now(timezone.utc)
            - timedelta(seconds=1)
        }
    )
    expired = repository.expire_stale_active(
        station_id, False, datetime.now(timezone.utc)
    )
    assert expired["status"] == "failed"
    assert expired["error"] == "TX_SYNTHESIS_TIMEOUT"

    with pytest.raises(HTTPException) as late_finish:
        repository.finish_confirm(
            "contract-user", station_id, job_id, "late-output.wav"
        )
    assert late_finish.value.detail["code"] == "TX_INVALID_STATE"
