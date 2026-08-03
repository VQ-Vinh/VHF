from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from google import genai
from google.cloud import storage
from google.genai import types

from services.prana_api.config import Settings
from services.prana_api.models import ProcessingResponse

logger = logging.getLogger(__name__)

_STATION_AUDIO_FILENAME = re.compile(
    r"^(?P<date>\d{8})_\d{6}_(?P<sequence>\d{4})\.wav$"
)


def station_storage_folder(station_name: str, station_id: str) -> str:
    """Return a readable, path-safe and collision-resistant Station folder."""
    cleaned = []
    previous_separator = False
    for character in station_name.strip():
        if character.isalnum() or character in {"-", "_", "."}:
            cleaned.append(character)
            previous_separator = False
        elif character.isspace() or character in {"/", "\\"}:
            if cleaned and not previous_separator:
                cleaned.append("-")
                previous_separator = True
    slug = "".join(cleaned).strip("-_.")[:64].rstrip("-_.")
    if not slug:
        slug = "PRANA-Station"
    return f"{slug}_{station_id[:8]}"


def station_audio_filename(
    uploaded_filename: str | None,
    sequence: int,
    *,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Validate a local WAV basename and return it with its date path."""
    candidate = uploaded_filename or ""
    match = _STATION_AUDIO_FILENAME.fullmatch(candidate)
    if match:
        try:
            date = datetime.strptime(match.group("date"), "%Y%m%d")
        except ValueError:
            match = None
    if not match:
        date = now or datetime.now(timezone.utc)
        candidate = f"{date:%Y%m%d_%H%M%S}_{sequence:04d}.wav"
    return candidate, f"{date:%Y/%m/%d}"


def station_storage_objects(
    station_id: str,
    station_name: str,
    audio_filename: str,
    date_path: str,
) -> tuple[str, str]:
    station_folder = station_storage_folder(station_name, station_id)
    result_filename = f"{audio_filename.removesuffix('.wav')}.json"
    root = f"VHF-Storage/{station_folder}"
    return (
        f"{root}/audio/{date_path}/{audio_filename}",
        f"{root}/result/{date_path}/{result_filename}",
    )


LANGUAGE_NAMES = {
    "vi": "Vietnamese",
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}


SYSTEM_PROMPT = """You are a VHF marine radio transcription AI.
The audio may contain static, narrow bandwidth, accents and maritime jargon.
Detect the language and use an ISO 639-1 code. Transcribe verbatim, then restore
punctuation and capitalization. Never invent content: use [UNCERTAIN] or
[INAUDIBLE]. Preserve numbers, coordinates, frequencies, callsigns and channel
numbers. The required output language is {target_language}. Always write the
translation in exactly that language; never choose an alternative output language.
If the detected language already matches the required output language, copy the
restored transcript into translation without translating it to another language.
Return only JSON with detected_language, transcript_raw, transcript_restored,
translation. If there is no speech, return an error field.
"""


def normalize_language_code(value: str) -> str:
    return value.strip().lower().replace("_", "-").split("-", 1)[0]


def normalize_same_language_translation(data: dict, target_language: str) -> dict:
    normalized = dict(data)
    detected = normalize_language_code(str(normalized.get("detected_language", "")))
    target = normalize_language_code(target_language)
    if detected and detected == target:
        normalized["translation"] = (
            normalized.get("transcript_restored")
            or normalized.get("transcript_raw")
            or ""
        )
    return normalized


@dataclass(frozen=True)
class ModelResult:
    response: ProcessingResponse
    metrics: dict


class GeminiProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    def process(
        self,
        audio: bytes,
        target_language: str,
        session_id: str,
        sequence: int,
        request_id: str,
    ) -> ModelResult:
        started = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.settings.gemini_model,
            contents=[
                "Transcribe this VHF audio and return JSON.",
                types.Part.from_bytes(data=audio, mime_type="audio/wav"),
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT.format(
                    target_language=(
                        f"{LANGUAGE_NAMES.get(target_language, target_language)} "
                        f"({target_language})"
                    )
                ),
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "detected_language": {"type": "STRING"},
                        "transcript_raw": {"type": "STRING"},
                        "transcript_restored": {"type": "STRING"},
                        "translation": {"type": "STRING"},
                        "error": {"type": "STRING", "nullable": True},
                    },
                },
                response_logprobs=True,
            ),
        )
        latency_ms = (time.perf_counter() - started) * 1000
        data = normalize_same_language_translation(
            json.loads(response.text),
            target_language,
        )
        candidate = response.candidates[0] if response.candidates else None
        avg_logprobs = getattr(candidate, "avg_logprobs", None)
        confidence = math.exp(avg_logprobs) if avg_logprobs is not None and avg_logprobs <= 0 else 0.0
        usage = getattr(response, "usage_metadata", None)
        metrics = {
            "model": self.settings.gemini_model,
            "latency_ms": round(latency_ms, 1),
            "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
            "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
        }
        metrics["estimated_cost_usd"] = round(
            metrics["input_tokens"] * self.settings.input_cost_per_million_tokens / 1_000_000
            + metrics["output_tokens"] * self.settings.output_cost_per_million_tokens / 1_000_000,
            6,
        )
        result = ProcessingResponse(
            session_id=session_id,
            sequence=sequence,
            audio_file=f"{session_id}_{sequence:04d}.wav",
            detected_language=data.get("detected_language", ""),
            transcript_raw=data.get("transcript_raw", ""),
            transcript_restored=data.get("transcript_restored", ""),
            translation=data.get("translation", ""),
            target_language=target_language,
            confidence=confidence,
            latency_ms=latency_ms,
            error=data.get("error"),
        )
        return ModelResult(response=result, metrics=metrics)


class CloudStorageArchive:
    def __init__(self, settings: Settings):
        if not settings.storage_bucket.strip():
            raise ValueError("PRANA_API_STORAGE_BUCKET is not configured")
        self.bucket = storage.Client(project=settings.google_cloud_project or None).bucket(settings.storage_bucket)

    def archive(
        self,
        uid: str,
        session_id: str,
        request_id: str,
        audio: bytes,
        response: dict,
    ) -> str:
        date = datetime.now(timezone.utc)
        prefix = f"customers/{uid}/{date:%Y/%m/%d}/{session_id}/{request_id}"
        audio_object = f"{prefix}.wav"
        self.bucket.blob(audio_object).upload_from_string(
            audio,
            content_type="audio/wav",
        )
        self.bucket.blob(f"{prefix}.json").upload_from_string(
            json.dumps(response, ensure_ascii=False), content_type="application/json"
        )
        logger.info(
            "Archived processing result",
            extra={"bucket": self.bucket.name, "object_prefix": prefix},
        )
        return audio_object

    def archive_station(
        self,
        station_id: str,
        station_name: str,
        audio_filename: str,
        date_path: str,
        audio: bytes,
        response: dict,
    ) -> str:
        audio_object, result_object = station_storage_objects(
            station_id,
            station_name,
            audio_filename,
            date_path,
        )
        self.bucket.blob(audio_object).upload_from_string(
            audio,
            content_type="audio/wav",
        )
        self.bucket.blob(result_object).upload_from_string(
            json.dumps(response, ensure_ascii=False),
            content_type="application/json",
        )
        logger.info(
            "Archived Station processing result",
            extra={
                "bucket": self.bucket.name,
                "audio_object": audio_object,
                "result_object": result_object,
            },
        )
        return audio_object

    def download_audio(self, object_name: str) -> bytes | None:
        blob = self.bucket.blob(object_name)
        if not blob.exists():
            return None
        return blob.download_as_bytes()
