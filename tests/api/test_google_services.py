from services.prana_api.google_services import (
    normalize_language_code,
    normalize_same_language_translation,
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
