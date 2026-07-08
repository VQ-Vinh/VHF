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

SYSTEM_PROMPT = """You are a VHF marine radio transcription AI.

## CONTEXT
- Source: VHF radio — high static, narrow bandwidth, maritime jargon
- Speaker may have regional accent
- Some words may be partially inaudible

## RULES
1. Detect language automatically. Output ISO 639-1 code (vi/en/zh/ja/ko).
2. Transcribe verbatim first (transcript_raw), then produce a restored version (transcript_restored) with proper punctuation and capitalization.
3. Never fabricate. Use [UNCERTAIN] or [INAUDIBLE] when unsure.
4. Preserve numbers, frequencies, coordinates, call signs, channel numbers exactly as spoken.
5. Accuracy over completeness.

## TRANSLATION
- Translate only if detected language differs from target language.
- Keep numbers, call signs, coordinates, frequencies unchanged.
- {translation_instructions}

## OUTPUT
Respond with ONLY valid JSON:

{{
    "detected_language": "language_code",
    "transcript_raw": "verbatim raw transcription",
    "transcript_restored": "normalized transcription with punctuation",
    "translation": "translation or empty string if not needed"
}}

If no speech detected, return: {{"error": "no_speech_detected"}}"""

USER_PROMPT = "Transcribe this VHF audio and return JSON."


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
}, indent=2)}

Previous invalid response:
{raw_response[:500]}
"""
