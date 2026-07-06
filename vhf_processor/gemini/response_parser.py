from __future__ import annotations

import json
import re
from pathlib import Path

from vhf_processor.models.result import ProcessingResult
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)

MIN_CONFIDENCE_REQUIRED = 0.1


class GeminiResponseParser:
    @staticmethod
    def parse(text: str, session_id: str, sequence: int, audio_file: str, latency_ms: float) -> ProcessingResult:
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

        confidence = float(data.get("confidence", 0.0))
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
                uncertain_segments=data.get("uncertain_segments", []),
                latency_ms=latency_ms,
                processing_notes=["Confidence below minimum threshold"] + data.get("processing_notes", []),
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
            uncertain_segments=data.get("uncertain_segments", []),
            processing_notes=data.get("processing_notes", []),
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
