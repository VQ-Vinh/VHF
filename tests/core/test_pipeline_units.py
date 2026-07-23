from __future__ import annotations

import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy as np

    from prana_core.pipeline.audio_utils import (
        resample_audio,
        split_audio_buffer,
        trim_trailing_silence,
    )
    from prana_core.pipeline.orchestrator import PipelineOrchestrator
    from prana_core.pipeline.segment_processor import SegmentJob, SegmentProcessor
    from prana_core.vad.base import VADState

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

    def test_split_audio_buffer_is_exact_and_non_overlapping(self) -> None:
        max_samples = 150

        short = np.arange(140, dtype=np.int16)
        chunks, remainder = split_audio_buffer([short], max_samples)
        self.assertEqual(chunks, [])
        np.testing.assert_array_equal(np.concatenate(remainder), short)

        exact = np.arange(150, dtype=np.int16)
        chunks, remainder = split_audio_buffer([exact], max_samples)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(remainder, [])
        np.testing.assert_array_equal(chunks[0], exact)

        continuous = np.arange(310, dtype=np.int16)
        chunks, remainder = split_audio_buffer([continuous], max_samples)
        self.assertEqual([len(chunk) for chunk in chunks], [150, 150])
        self.assertEqual([len(part) for part in remainder], [10])
        np.testing.assert_array_equal(np.concatenate([*chunks, *remainder]), continuous)

    def test_orchestrator_queues_15_second_chunks_with_sequential_ids(self) -> None:
        class FakeSession:
            session_id = "session-test"

            def __init__(self) -> None:
                self.sequence = 0

            def next_sequence(self) -> int:
                self.sequence += 1
                return self.sequence

        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._config = SimpleNamespace(
            vad=SimpleNamespace(max_segment_duration_ms=15000)
        )
        orchestrator._session = FakeSession()
        orchestrator._job_queue = queue.Queue()
        orchestrator._vad_buffer = [np.arange(310, dtype=np.int16)]
        orchestrator._vad_sample_count = 310
        orchestrator._samples_since_speech = 0
        orchestrator._speech_frame_count = 16

        orchestrator._flush_max_duration_segments(10, VADState.SPEECH, 2)

        first = orchestrator._job_queue.get_nowait()
        second = orchestrator._job_queue.get_nowait()
        self.assertEqual((first.sequence, second.sequence), (1, 2))
        self.assertEqual((len(first.audio_data), len(second.audio_data)), (150, 150))
        self.assertEqual(orchestrator._vad_sample_count, 10)
        np.testing.assert_array_equal(
            np.concatenate(
                [first.audio_data, second.audio_data, *orchestrator._vad_buffer]
            ),
            np.arange(310, dtype=np.int16),
        )

@unittest.skipUnless(PIPELINE_AVAILABLE, "client audio dependencies are not installed")
class PipelineStructureTests(unittest.TestCase):
    def test_segment_types_are_owned_by_segment_processor(self) -> None:
        self.assertEqual(SegmentJob.__module__, "prana_core.pipeline.segment_processor")
        self.assertTrue(callable(getattr(SegmentProcessor, "process")))
        self.assertTrue(callable(getattr(SegmentProcessor, "retry_last_failed")))

    def test_restart_clears_worker_stop_event_before_start(self) -> None:
        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._stop_event = threading.Event()
        calls = []

        def stop():
            calls.append("stop")
            orchestrator._stop_event.set()

        def start():
            calls.append("start")
            self.assertFalse(orchestrator._stop_event.is_set())

        orchestrator._do_stop = stop
        orchestrator._do_start = start
        orchestrator._do_restart()
        self.assertEqual(calls, ["stop", "start"])

    def test_stop_replaces_queue_before_a_later_restart(self) -> None:
        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._stop_event = threading.Event()
        orchestrator._state_lock = threading.RLock()
        orchestrator._cleanup_timer = None
        orchestrator._recorder = None
        orchestrator._executor = None
        orchestrator._worker_futures = []
        orchestrator._job_queue = queue.Queue(maxsize=32)
        stale_queue = orchestrator._job_queue
        stale_queue.put(object())
        orchestrator._backend = SimpleNamespace(close=lambda: None)
        orchestrator._session = SimpleNamespace(session_id="old-session", sequence=3)

        orchestrator._do_stop()

        self.assertIsNot(orchestrator._job_queue, stale_queue)
        self.assertTrue(orchestrator._job_queue.empty())


if __name__ == "__main__":
    unittest.main()
