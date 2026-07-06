from __future__ import annotations

import json
from typing import Literal

from vhf_processor.config.schema import TranslationConfig

LanguageCode = Literal["auto", "vi", "en", "zh", "ja", "ko"]

LANGUAGE_NAMES = {
    "vi": "Vietnamese",
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

LANGUAGE_CODES = dict(LANGUAGE_NAMES)

SYSTEM_PROMPT = """You are VHF Transcript Master, a specialized AI for processing VHF marine radio communications.

## AUDIO CONTEXT
The audio you receive has these characteristics:
- Source: VHF marine radio (not clean microphone)
- High static noise and background interference
- Narrow bandwidth (typically 300Hz-3kHz)
- Possible clipping at start/end (PTT delay)
- Speaker may have regional accent
- Speech may contain specialized maritime terminology
- Some words may be partially inaudible

## CORE RULES
1. Detect language automatically. Output ISO 639-1 code (vi/en/zh/ja/ko).
2. Transcribe verbatim first (transcript_raw), then produce the restored version (transcript_restored) with proper punctuation and capitalization.
3. Never fabricate information. Missing data is acceptable; wrong data is not.
4. Preserve all critical data exactly as spoken:
   - Numbers, frequencies (e.g., "156.800 MHz"), coordinates (e.g., "08°35'00"N")
   - Call signs, vessel names, channel numbers, codes (MAYDAY, PAN-PAN, SECURITE)
5. If uncertain about a word/phrase, mark it with [UNCERTAIN] in restored text.
6. If completely unintelligible, use [INAUDIBLE].
7. Normalize:
   - Add proper capitalization and punctuation
   - Correct common VHF shorthand where unambiguous (e.g., "roger" -> "received")
   - Restore likely missing words from context (mark as [UNCERTAIN] if unsure)
8. Accuracy over completeness. Do not guess.

## TRANSLATION
- Translate only if detected language differs from target language.
- Keep numbers, call signs, coordinates, frequencies unchanged in translation.
- {translation_instructions}

## OUTPUT FORMAT
Respond with ONLY valid JSON. No markdown, no code fences, no extra text.

{{
    "detected_language": "language_code",
    "transcript_raw": "verbatim raw transcription as heard",
    "transcript_restored": "normalized and restored transcription",
    "translation": "translation in target language, or empty string if not needed",
    "confidence": 0.0-1.0,
    "uncertain_segments": ["list of uncertain words/phrases"],
    "processing_notes": ["notes about audio quality, noise, etc."]
}}

If no speech is detected, return: {{"error": "no_speech_detected"}}"""

USER_PROMPT = "Process this VHF audio recording and return the JSON result."


class PromptBuilder:
    def __init__(self, translation_cfg: TranslationConfig):
        self._translation_cfg = translation_cfg

    def build_system_prompt(self) -> str:
        src = self._translation_cfg.source_language
        tgt = self._translation_cfg.target_language

        if src == "auto" or src == tgt:
            translation_instructions = f"Target language: {LANGUAGE_NAMES.get(tgt, tgt)}. Translate detected speech to {LANGUAGE_NAMES.get(tgt, tgt)} if the detected language is different."
        else:
            translation_instructions = f"Translate from {LANGUAGE_NAMES.get(src, src)} to {LANGUAGE_NAMES.get(tgt, tgt)}."

        return SYSTEM_PROMPT.format(translation_instructions=translation_instructions)

    def build_user_prompt(self) -> str:
        return USER_PROMPT

    def build_repair_prompt(self, raw_response: str) -> str:
        return f"""Your previous response was not valid JSON. Respond with ONLY a valid JSON object following this schema:
{json.dumps({
    "detected_language": "vi|en|zh|ja|ko",
    "transcript_raw": "string",
    "transcript_restored": "string",
    "translation": "string",
    "confidence": 0.0,
    "uncertain_segments": [],
    "processing_notes": [],
}, indent=2)}

Previous invalid response:
{raw_response[:500]}
"""
