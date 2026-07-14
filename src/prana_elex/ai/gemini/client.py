from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError

from prana_elex.config.schema import GeminiConfig
from prana_elex.common.google_credentials import load_google_credentials
from prana_elex.pipeline.models import ProcessingResult
from prana_elex.common.logger import get_logger
from prana_elex.ai.gemini.prompts import PromptBuilder
from prana_elex.ai.gemini.response_parser import GeminiResponseParser

logger = get_logger(__name__)


class GeminiClient:
    def __init__(
        self,
        config: GeminiConfig,
        prompt_builder: PromptBuilder,
        response_parser: type[GeminiResponseParser] = GeminiResponseParser,
        *,
        credentials_path: str,
    ):
        self._config = config
        self._prompt_builder = prompt_builder
        self._response_parser = response_parser
        self._credentials_path = credentials_path
        self._client: genai.Client | None = None
        self._api_lock = threading.Lock()
        self._init_client()

    def _init_client(self) -> None:
        try:
            credentials, project, _ = load_google_credentials(self._credentials_path)
            self._client = genai.Client(
                vertexai=True,
                credentials=credentials,
                project=project,
                location=self._config.location,
            )
            logger.info(
                "Gemini initialized with service-account JSON: model=%s, project=%s",
                self._config.model,
                project,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def process_audio(
        self,
        audio_path: str | Path,
        session_id: str,
        sequence: int,
        audio_bytes: bytes | None = None,
    ) -> ProcessingResult:
        start_time = time.perf_counter()
        audio_path = Path(audio_path)

        if audio_bytes is None:
            if not audio_path.exists():
                elapsed = (time.perf_counter() - start_time) * 1000
                return ProcessingResult(
                    session_id=session_id,
                    sequence=sequence,
                    audio_file=audio_path.name,
                    error="audio_file_not_found",
                    latency_ms=elapsed,
                    processing_notes=[f"Audio file not found: {audio_path}"],
                )
            audio_bytes = audio_path.read_bytes()

        system_prompt = self._prompt_builder.build_system_prompt()
        user_prompt = self._prompt_builder.build_user_prompt()

        last_error: Exception | None = None
        for attempt in range(1, self._config.max_retries + 1):
            try:
                with self._api_lock:
                    response = self._client.models.generate_content(
                        model=self._config.model,
                        contents=[
                            user_prompt,
                            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.1,
                            max_output_tokens=2048,
                            response_logprobs=True,
                        ),
                    )

                elapsed = (time.perf_counter() - start_time) * 1000

                avg_logprobs = None
                token_logprobs = None
                candidate = response.candidates[0] if response.candidates else None
                if candidate is not None:
                    avg_logprobs = candidate.avg_logprobs
                    if candidate.logprobs_result is not None:
                        token_logprobs = candidate.logprobs_result.chosen_candidates

                result = self._response_parser.parse(
                    text=response.text,
                    session_id=session_id,
                    sequence=sequence,
                    audio_file=audio_path.name,
                    latency_ms=elapsed,
                    avg_logprobs=avg_logprobs,
                    token_logprobs=token_logprobs,
                )

                if result.has_error:
                    logger.warning(
                        f"Processing result has error: {result.error}",
                        extra={
                            "session": session_id,
                            "sequence": sequence,
                            "attempt": attempt,
                        },
                    )
                    if result.error and ("json_decode" in result.error or "no_valid_json" in result.error):
                        logger.warning(
                            f"Gemini response parse failed, raw preview: {response.text[:500]}",
                            extra={"session": session_id, "sequence": sequence},
                        )

                logger.info(
                    "Audio processed by Gemini",
                    extra={
                        "session": session_id,
                        "sequence": sequence,
                        "latency_ms": round(elapsed, 1),
                        "confidence": result.confidence,
                        "language": result.detected_language,
                        "attempt": attempt,
                    },
                )

                return result

            except ClientError as e:
                last_error = e
                logger.warning(
                    f"Gemini API attempt {attempt}/{self._config.max_retries} failed",
                    exc_info=e,
                    extra={
                        "session": session_id,
                        "sequence": sequence,
                        "attempt": attempt,
                    },
                )
                if attempt < self._config.max_retries:
                    backoff = min(2 ** (attempt + 1), 30)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    break
            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error in Gemini processing",
                    exc_info=e,
                    extra={
                        "session": session_id,
                        "sequence": sequence,
                        "attempt": attempt,
                    },
                )
                break

        elapsed = (time.perf_counter() - start_time) * 1000
        return ProcessingResult(
            session_id=session_id,
            sequence=sequence,
            audio_file=audio_path.name,
            error=f"gemini_processing_failed: {last_error}",
            latency_ms=elapsed,
            processing_notes=[f"All {self._config.max_retries} attempts failed"],
        )

    async def process_audio_async(
        self,
        audio_path: str | Path,
        session_id: str,
        sequence: int,
    ) -> ProcessingResult:
        return await asyncio.to_thread(
            self.process_audio,
            audio_path,
            session_id,
            sequence,
        )

    def close(self) -> None:
        self._client = None
        logger.info("Gemini client closed")
