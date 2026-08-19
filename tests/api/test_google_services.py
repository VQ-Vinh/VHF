import json
from datetime import datetime, timezone

from services.prana_api.google_services import (
    CloudStorageArchive,
    normalize_language_code,
    normalize_same_language_translation,
    station_audio_filename,
    station_storage_folder,
    station_storage_objects,
    tx_date_path,
)


class _Blob:
    def __init__(self) -> None:
        self.data = None

    def upload_from_string(self, data, content_type: str) -> None:
        self.data = data


class _Bucket:
    def __init__(self) -> None:
        self.objects: dict[str, _Blob] = {}

    def blob(self, name: str) -> _Blob:
        return self.objects.setdefault(name, _Blob())


def test_station_folder_is_readable_safe_and_unique() -> None:
    assert station_storage_folder("VINH", "0f90cd8ef056") == "VINH_0f90cd8e"
    assert (
        station_storage_folder(" Trạm / Cầu tàu ", "abcdef123456")
        == "Trạm-Cầu-tàu_abcdef12"
    )
    assert station_storage_folder("///", "1234567890") == "PRANA-Station_12345678"


def test_station_audio_filename_preserves_local_name_and_date() -> None:
    assert station_audio_filename("20260803_110002_0001.wav", 1) == (
        "20260803_110002_0001.wav",
        "2026/08/03",
    )


def test_station_audio_filename_rejects_paths_and_uses_safe_fallback() -> None:
    now = datetime(2026, 8, 3, 4, 5, 6, tzinfo=timezone.utc)
    expected = ("20260803_040506_0007.wav", "2026/08/03")
    assert station_audio_filename("../20260803_110002_0001.wav", 7, now=now) == expected
    assert station_audio_filename("C:\\temp\\audio.wav", 7, now=now) == expected
    assert station_audio_filename("20260231_110002_0007.wav", 7, now=now) == expected


def test_station_storage_separates_audio_and_result_with_matching_stems() -> None:
    audio, result = station_storage_objects(
        "0f90cd8ef056",
        "VINH",
        "20260803_110002_0001.wav",
        "2026/08/03",
    )
    assert audio == (
        "VHF-Storage/VINH_0f90cd8e/RX/audio/2026/08/03/"
        "20260803_110002_0001.wav"
    )
    assert result == (
        "VHF-Storage/VINH_0f90cd8e/RX/result/2026/08/03/"
        "20260803_110002_0001.json"
    )


def test_tx_date_path_uses_filename_date_and_falls_back_when_unusable() -> None:
    fallback = datetime(2026, 8, 19, 4, 5, 6, tzinfo=timezone.utc)
    assert tx_date_path("20260805_155923_0001.wav", fallback=fallback) == "2026/08/05"
    # Unusable names must not silently produce year 1.
    assert tx_date_path("", fallback=fallback) == "2026/08/19"
    assert tx_date_path("not-a-timestamp.wav", fallback=fallback) == "2026/08/19"
    assert tx_date_path("20260231_155923_0001.wav", fallback=fallback) == "2026/08/19"


def test_language_code_normalization_accepts_case_and_locale() -> None:
    assert normalize_language_code("VI") == "vi"
    assert normalize_language_code("vi-VN") == "vi"
    assert normalize_language_code("vi_VN") == "vi"


def test_same_language_uses_restored_transcript() -> None:
    result = normalize_same_language_translation(
        {
            "detected_language": "vi-VN",
            "transcript_raw": "xin chao",
            "transcript_restored": "Xin chào.",
            "translation": "Hello.",
        },
        "vi",
    )

    assert result["translation"] == "Xin chào."


def test_same_language_falls_back_to_raw_transcript() -> None:
    result = normalize_same_language_translation(
        {
            "detected_language": "VI",
            "transcript_raw": "xin chao",
            "transcript_restored": "",
            "translation": "Hello.",
        },
        "vi",
    )

    assert result["translation"] == "xin chao"


def test_tx_output_archive_serializes_firestore_datetime_metadata() -> None:
    archive = CloudStorageArchive.__new__(CloudStorageArchive)
    archive.bucket = _Bucket()
    created_at = datetime(2026, 8, 5, 15, 59, 23, tzinfo=timezone.utc)

    output_object = archive.archive_tx_output(
        "station-1",
        "VINH",
        "20260805_155923_0001.wav",
        "2026/08/05",
        b"wav-output",
        {"id": "job-1", "created_at": created_at, "status": "queued"},
    )

    assert output_object.endswith("/TX/output/2026/08/05/20260805_155923_0001.wav")
    station_folder = station_storage_folder("VINH", "station-1")
    result_object = (
        f"VHF-Storage/{station_folder}/TX/result/2026/08/05/"
        "20260805_155923_0001.json"
    )
    metadata = json.loads(archive.bucket.objects[result_object].data)
    assert metadata["created_at"] == "2026-08-05 15:59:23+00:00"
    assert archive.bucket.objects[output_object].data == b"wav-output"


def test_tx_and_rx_archives_share_the_same_station_folder_prefix() -> None:
    archive = CloudStorageArchive.__new__(CloudStorageArchive)
    archive.bucket = _Bucket()
    station_folder = station_storage_folder("VINH", "0f90cd8ef056")

    rx_audio, _rx_result = station_storage_objects(
        "0f90cd8ef056",
        "VINH",
        "20260803_110002_0001.wav",
        "2026/08/03",
    )
    assert rx_audio.startswith(f"VHF-Storage/{station_folder}/")

    tx_source = archive.archive_tx_source(
        "0f90cd8ef056",
        "VINH",
        "20260803_110002_0001.wav",
        "2026/08/03",
        b"wav-source",
    )
    tx_output = archive.archive_tx_output(
        "0f90cd8ef056",
        "VINH",
        "20260803_110002_0001.wav",
        "2026/08/03",
        b"wav-output",
        {"id": "job-1", "status": "queued"},
    )

    assert tx_source.startswith(f"VHF-Storage/{station_folder}/")
    assert tx_output.startswith(f"VHF-Storage/{station_folder}/")


def test_different_language_preserves_model_translation() -> None:
    result = normalize_same_language_translation(
        {
            "detected_language": "en",
            "transcript_restored": "Mayday.",
            "translation": "Cấp cứu.",
        },
        "vi",
    )

    assert result["translation"] == "Cấp cứu."
