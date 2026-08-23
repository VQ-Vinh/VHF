"""What GeminiProcessor needs from the google-genai SDK, and from a response.

The processor had no coverage at all, so a major SDK bump could pass the whole
suite and break translation in production only. These tests make no network
call: the first pins the SDK surface the processor calls, the second drives
process() through a stub client to cover the parsing it does on the way out.
"""

from __future__ import annotations

import json
import math
import unittest
from types import SimpleNamespace

from google import genai
from google.genai import types

from services.prana_api.google_services import GeminiProcessor


class GenaiSurfaceTests(unittest.TestCase):
    def test_client_accepts_the_vertex_arguments_the_processor_passes(self) -> None:
        import inspect

        parameters = set(inspect.signature(genai.Client.__init__).parameters)
        self.assertLessEqual({"vertexai", "project", "location"}, parameters)

    def test_audio_parts_are_built_from_raw_bytes(self) -> None:
        part = types.Part.from_bytes(data=b"RIFF....", mime_type="audio/wav")
        self.assertEqual(part.inline_data.mime_type, "audio/wav")

    def test_the_generation_config_keeps_every_option_the_processor_sets(self) -> None:
        # response_logprobs is the fragile one: confidence is derived from the
        # avg_logprobs it turns on, and a silent drop would pin confidence to 0.
        config = types.GenerateContentConfig(
            system_instruction="x",
            temperature=0.1,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema={"type": "OBJECT", "properties": {}},
            response_logprobs=True,
        )
        self.assertTrue(config.response_logprobs)
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertEqual(config.max_output_tokens, 2048)


class _StubModels:
    def __init__(self, response):
        self._response = response
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return self._response


class GeminiProcessorResponseTests(unittest.TestCase):
    def _processor(self, response) -> GeminiProcessor:
        processor = GeminiProcessor.__new__(GeminiProcessor)
        processor.settings = SimpleNamespace(
            gemini_model="gemini-test",
            input_cost_per_million_tokens=1.0,
            output_cost_per_million_tokens=2.0,
        )
        processor.client = SimpleNamespace(models=_StubModels(response))
        return processor

    @staticmethod
    def _response(payload: dict, avg_logprobs: float | None):
        return SimpleNamespace(
            text=json.dumps(payload),
            candidates=[SimpleNamespace(avg_logprobs=avg_logprobs)],
            usage_metadata=SimpleNamespace(
                prompt_token_count=1000, candidates_token_count=500
            ),
        )

    def test_a_response_becomes_a_result_with_confidence_and_cost(self) -> None:
        payload = {
            "detected_language": "en",
            "transcript_raw": "mayday",
            "transcript_restored": "Mayday",
            "translation": "Cuu nan",
        }
        processor = self._processor(self._response(payload, -0.2))
        result = processor.process(b"RIFF", "vi", "session-1", 7, "req-1")

        self.assertEqual(result.response.translation, "Cuu nan")
        self.assertEqual(result.response.audio_file, "session-1_0007.wav")
        self.assertAlmostEqual(result.response.confidence, math.exp(-0.2))
        self.assertEqual(result.metrics["input_tokens"], 1000)
        # 1000/1e6*1.0 + 500/1e6*2.0
        self.assertAlmostEqual(result.metrics["estimated_cost_usd"], 0.002)

    def test_a_missing_logprob_yields_zero_confidence_rather_than_an_error(self) -> None:
        processor = self._processor(self._response({"translation": "x"}, None))
        result = processor.process(b"RIFF", "vi", "session-1", 1, "req-1")
        self.assertEqual(result.response.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
