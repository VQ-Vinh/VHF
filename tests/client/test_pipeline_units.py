from __future__ import annotations

import unittest

try:
    import numpy as np

    from prana_elex.pipeline.audio_utils import resample_audio, trim_trailing_silence
    from prana_elex.pipeline.segment_processor import SegmentJob, SegmentProcessor

    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False


@unittest.skipUnless(PIPELINE_AVAILABLE, "client audio dependencies are not installed")
class AudioUtilsTests(unittest.TestCase):
    def test_resample_preserves_dtype_and_duration(self) -> None:
        audio = np.arange(4800, dtype=np.int16)
        result = resample_audio(audio, 48000, 16000)
        self.assertEqual(result.dtype, audio.dtype)
        self.assertEqual(len(result), 1600)

    def test_trim_removes_only_trailing_silent_frames(self) -> None:
        sample_rate = 16000
        speech = np.full(1600, 1000, dtype=np.int16)
        silence = np.zeros(1024, dtype=np.int16)
        result = trim_trailing_silence(np.concatenate((speech, silence)), sample_rate)
        self.assertGreaterEqual(len(result), len(speech))
        self.assertLess(len(result), len(speech) + len(silence))
        self.assertTrue(np.all(result[: len(speech)] == speech))


@unittest.skipUnless(PIPELINE_AVAILABLE, "client audio dependencies are not installed")
class PipelineStructureTests(unittest.TestCase):
    def test_segment_types_are_owned_by_segment_processor(self) -> None:
        self.assertEqual(SegmentJob.__module__, "prana_elex.pipeline.segment_processor")
        self.assertTrue(callable(getattr(SegmentProcessor, "process")))
        self.assertTrue(callable(getattr(SegmentProcessor, "retry_last_failed")))


if __name__ == "__main__":
    unittest.main()
