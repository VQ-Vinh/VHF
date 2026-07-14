from __future__ import annotations

import json
import math
import re
from pathlib import Path

from prana_elex.pipeline.models import ProcessingResult
from prana_elex.common.logger import get_logger

logger = get_logger(__name__)

MIN_CONFIDENCE_REQUIRED = 0.1
LOGPROB_UNCERTAIN_THRESHOLD = -1.5


class GeminiResponseParser:
    @staticmethod
    def parse(
        text: str,
        session_id: str,
        sequence: int,
        audio_file: str,
        latency_ms: float,
        avg_logprobs: float | None = None,
        token_logprobs: list | None = None,
    ) -> ProcessingResult:
        json_str = GeminiResponseParser._extract_json(text)
        if not json_str:
            return ProcessingResult(
                session_id=session_id,
                sequence=sequence,
                audio_file=audio_file,
                error="no_valid_json_in_response",
                latency_ms=latency_ms,
                processing_notes=["Failed to parse Gemini response as JSON"],
            )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return ProcessingResult(
                session_id=session_id,
                sequence=sequence,
                audio_file=audio_file,
                error=f"json_decode_error: {e}",
                latency_ms=latency_ms,
                processing_notes=[f"JSON parse failed: {e}"],
            )

        if isinstance(data, dict) and "error" in data:
            return ProcessingResult(
                session_id=session_id,
                sequence=sequence,
                audio_file=audio_file,
                error=data["error"],
                latency_ms=latency_ms,
                processing_notes=[f"Gemini returned error: {data['error']}"],
            )

        confidence = 0.0
        uncertain_segments: list[str] = []
        processing_notes: list[str] = []

        if avg_logprobs is not None and avg_logprobs <= 0.0:
            confidence = math.exp(avg_logprobs)
            processing_notes.append(f"Confidence from token logprobs (avg_logprob={avg_logprobs:.4f})")

        if token_logprobs:
            for tc in token_logprobs:
                lp = getattr(tc, "log_probability", None)
                token = getattr(tc, "token", None)
                if lp is not None and lp < LOGPROB_UNCERTAIN_THRESHOLD:
                    token_text = (token or "").strip()
                    if token_text and token_text not in uncertain_segments:
                        uncertain_segments.append(token_text)

        if confidence < MIN_CONFIDENCE_REQUIRED:
            return ProcessingResult(
                session_id=session_id,
                sequence=sequence,
                audio_file=audio_file,
                error="low_confidence",
                confidence=confidence,
                transcript_raw=data.get("transcript_raw", ""),
                transcript_restored=data.get("transcript_restored", ""),
                translation=data.get("translation", ""),
                detected_language=data.get("detected_language", ""),
                uncertain_segments=uncertain_segments,
                latency_ms=latency_ms,
                processing_notes=["Confidence below minimum threshold"] + processing_notes,
            )

        return ProcessingResult(
            session_id=session_id,
            sequence=sequence,
            audio_file=audio_file,
            detected_language=data.get("detected_language", ""),
            transcript_raw=data.get("transcript_raw", ""),
            transcript_restored=data.get("transcript_restored", ""),
            translation=data.get("translation", ""),
            confidence=confidence,
            uncertain_segments=uncertain_segments,
            processing_notes=processing_notes,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_json(text: str) -> str | None:
        text = text.strip()

        if text.startswith("```"):
            pattern = r"```(?:json)?\s*([\s\S]*?)```"
            matches = re.findall(pattern, text)
            if matches:
                return matches[-1].strip()

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            return text[brace_start : brace_end + 1]

        return text if text.startswith("{") else None
