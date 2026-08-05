from datetime import datetime, timezone

from services.prana_api.google_services import (
    normalize_language_code,
    normalize_same_language_translation,
    station_audio_filename,
    station_storage_folder,
    station_storage_objects,
)


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
