from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from google import genai
from google.cloud import storage
from google.genai import types

from services.prana_api.config import Settings
from services.prana_api.models import ProcessingResponse


SYSTEM_PROMPT = """You are a VHF marine radio transcription AI.
The audio may contain static, narrow bandwidth, accents and maritime jargon.
Detect the language and use an ISO 639-1 code. Transcribe verbatim, then restore
punctuation and capitalization. Never invent content: use [UNCERTAIN] or
[INAUDIBLE]. Preserve numbers, coordinates, frequencies, callsigns and channel
numbers. Translate all detected speech into {target_language}.
Return only JSON with detected_language, transcript_raw, transcript_restored,
translation. If there is no speech, return an error field.
"""


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
                system_instruction=SYSTEM_PROMPT.format(target_language=target_language),
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
        data = json.loads(response.text)
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
            confidence=confidence,
            latency_ms=latency_ms,
            error=data.get("error"),
        )
        return ModelResult(response=result, metrics=metrics)


class CloudStorageArchive:
    def __init__(self, settings: Settings):
        self.bucket = storage.Client(project=settings.google_cloud_project or None).bucket(settings.storage_bucket)

    def archive(self, uid: str, session_id: str, request_id: str, audio: bytes, response: dict) -> None:
        date = datetime.now(timezone.utc)
        prefix = f"customers/{uid}/{date:%Y/%m/%d}/{session_id}/{request_id}"
        self.bucket.blob(f"{prefix}.wav").upload_from_string(audio, content_type="audio/wav")
        self.bucket.blob(f"{prefix}.json").upload_from_string(
            json.dumps(response, ensure_ascii=False), content_type="application/json"
        )
