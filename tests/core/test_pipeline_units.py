from __future__ import annotations

import io
import queue
import sys
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
    from prana_core.pipeline.orchestrator import (
        CAPTURE_QUEUE_FRAMES,
        PipelineOrchestrator,
        PipelineState,
        effective_worker_count,
    )
    from prana_core.backend.client import BackendApiError
    from prana_core.pipeline.models import ProcessingResult
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
            vad=SimpleNamespace(max_segment_duration_ms=15000),
            translation=SimpleNamespace(target_language="vi"),
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
        self.assertEqual((first.target_language, second.target_language), ("vi", "vi"))
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
    def test_audio_callback_queues_a_copy_without_running_vad(self) -> None:
        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._state = PipelineState.RUNNING
        orchestrator._state_lock = threading.RLock()
        orchestrator._capture_queue = queue.Queue(maxsize=CAPTURE_QUEUE_FRAMES)
        orchestrator._capture_dropped_frames = 0
        processed = []
        orchestrator._process_vad_frame = processed.append
        audio = np.arange(32, dtype=np.int16)

        orchestrator._audio_callback(audio)
        audio[:] = -1

        self.assertEqual(processed, [])
        np.testing.assert_array_equal(
            orchestrator._capture_queue.get_nowait(), np.arange(32, dtype=np.int16)
        )

    def test_capture_worker_processes_pcm_frames_in_order(self) -> None:
        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._stop_event = threading.Event()
        orchestrator._capture_queue = queue.Queue(maxsize=CAPTURE_QUEUE_FRAMES)
        orchestrator._capture_dropped_frames = 0
        observed = []

        def process(audio) -> None:
            observed.append(int(audio[0]))
            if len(observed) == 3:
                orchestrator._stop_event.set()

        orchestrator._process_vad_frame = process
        for value in (1, 2, 3):
            orchestrator._capture_queue.put(np.array([value], dtype=np.int16))

        orchestrator._capture_loop()

        self.assertEqual(observed, [1, 2, 3])
        self.assertEqual(orchestrator._capture_queue.unfinished_tasks, 0)

    def test_full_capture_queue_is_reported_without_blocking(self) -> None:
        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._state = PipelineState.RUNNING
        orchestrator._state_lock = threading.RLock()
        orchestrator._capture_queue = queue.Queue(maxsize=1)
        orchestrator._capture_dropped_frames = 0
        orchestrator._capture_queue.put(np.zeros(1, dtype=np.int16))

        orchestrator._audio_callback(np.ones(1, dtype=np.int16))

        self.assertEqual(orchestrator._capture_dropped_frames, 1)

    def test_segment_types_are_owned_by_segment_processor(self) -> None:
        self.assertEqual(SegmentJob.__module__, "prana_core.pipeline.segment_processor")
        self.assertTrue(callable(getattr(SegmentProcessor, "process")))
        self.assertTrue(callable(getattr(SegmentProcessor, "retry_last_failed")))

    def test_processing_result_serializes_target_language(self) -> None:
        result = ProcessingResult(
            session_id="session",
            sequence=1,
            audio_file="segment.wav",
            target_language="vi",
        )

        self.assertEqual(result.model_dump()["target_language"], "vi")
        self.assertEqual(
            ProcessingResult.model_validate(
                {
                    "session_id": "legacy",
                    "sequence": 1,
                    "audio_file": "legacy.wav",
                }
            ).target_language,
            "",
        )

    def test_queued_segments_snapshot_target_language(self) -> None:
        class FakeSession:
            session_id = "session-test"
            sequence = 0

            def next_sequence(self) -> int:
                self.sequence += 1
                return self.sequence

        orchestrator = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orchestrator._config = SimpleNamespace(
            translation=SimpleNamespace(target_language="vi")
        )
        orchestrator._session = FakeSession()
        orchestrator._job_queue = queue.Queue()

        orchestrator._enqueue_audio_data(np.ones(200, dtype=np.int16), 16000)
        orchestrator._config.translation.target_language = "en"
        orchestrator._enqueue_audio_data(np.ones(200, dtype=np.int16), 16000)

        first = orchestrator._job_queue.get_nowait()
        second = orchestrator._job_queue.get_nowait()
        self.assertEqual(first.target_language, "vi")
        self.assertEqual(second.target_language, "en")

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

    def test_worker_count_honors_plan_concurrency(self) -> None:
        self.assertEqual(
            effective_worker_count(
                4,
                {"entitlements": {"max_concurrency": 2}},
            ),
            2,
        )
        self.assertEqual(effective_worker_count(4, {}), 2)

    def test_transient_backend_failure_retries_with_backoff(self) -> None:
        class Backend:
            calls = 0

            def process_audio(self, *_args, **_kwargs):
                self.calls += 1
                if self.calls < 3:
                    raise BackendApiError(
                        "SERVICE_BUSY",
                        "busy",
                        status=503,
                        detail={"retry_after": 3},
                    )
                return ProcessingResult(
                    session_id="session",
                    sequence=1,
                    audio_file="segment.wav",
                )

        processor = SegmentProcessor.__new__(SegmentProcessor)
        processor._backend = Backend()
        processor._config = SimpleNamespace(
            translation=SimpleNamespace(target_language="vi")
        )
        processor.backend_error = "old error"
        processor.last_backend_ok = False
        processor._status_lock = threading.Lock()
        processor._retrying = {}

        with patch(
            "prana_core.pipeline.segment_processor.time.sleep"
        ) as sleep:
            result = processor._process_with_retry(
                SimpleNamespace(name="20260803_100000_0001.wav"),
                "session",
                1,
                "vi",
                audio_bytes=b"wav",
            )

        self.assertEqual(result.sequence, 1)
        self.assertEqual(processor._backend.calls, 3)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [3.0, 4.0],
        )
        self.assertFalse(processor.retry_status["retrying"])
        self.assertIsNone(processor.backend_error)
        self.assertEqual(result.target_language, "vi")

    def test_manual_retry_keeps_failed_segment_target(self) -> None:
        processor = SegmentProcessor.__new__(SegmentProcessor)
        audio_path = SimpleNamespace(name="20260803_100000_0007.wav")
        processor._failed_audio = {("session", 7): (audio_path, "vi")}
        saved = []
        processor._storage = SimpleNamespace(save_result=saved.append)
        processor._publish_result = lambda _result: None
        observed = []

        def process(_path, _session, _sequence, target_language):
            observed.append(target_language)
            return ProcessingResult(
                session_id="session",
                sequence=7,
                audio_file="segment.wav",
                target_language=target_language,
            )

        processor._process_with_retry = process
        processor._retry_failed(audio_path, "session", 7, "vi")

        self.assertEqual(observed, ["vi"])
        self.assertEqual(processor._failed_audio, {})
        self.assertEqual(saved[0].audio_file, audio_path.name)

    def test_saved_file_result_uses_local_timestamped_audio_name(self) -> None:
        class Backend:
            def process_audio(self, *_args, **_kwargs):
                return ProcessingResult(
                    session_id="session",
                    sequence=3,
                    audio_file="session_0003.wav",
                )

        saved = []
        processor = SegmentProcessor.__new__(SegmentProcessor)
        processor._backend = Backend()
        processor._storage = SimpleNamespace(save_result=saved.append)
        processor._config = SimpleNamespace(
            translation=SimpleNamespace(target_language="vi")
        )
        processor.print_result = lambda _result: None
        audio_path = SimpleNamespace(name="20260803_101500_0003.wav")

        result = processor._process_saved_file(audio_path, "session", 3)

        self.assertEqual(result.audio_file, audio_path.name)
        self.assertEqual(saved[0].audio_file, audio_path.name)

    def test_non_transient_backend_failure_is_not_retried(self) -> None:
        class Backend:
            calls = 0

            def process_audio(self, *_args, **_kwargs):
                self.calls += 1
                raise BackendApiError(
                    "SUBSCRIPTION_INACTIVE",
                    "inactive",
                    status=403,
                )

        processor = SegmentProcessor.__new__(SegmentProcessor)
        processor._backend = Backend()
        processor._config = SimpleNamespace(
            translation=SimpleNamespace(target_language="vi")
        )
        processor.backend_error = None
        processor.last_backend_ok = None
        processor._status_lock = threading.Lock()
        processor._retrying = {}

        with patch(
            "prana_core.pipeline.segment_processor.time.sleep"
        ) as sleep:
            with self.assertRaises(BackendApiError):
                processor._process_with_retry(
                    SimpleNamespace(),
                    "session",
                    1,
                    "vi",
                )

        sleep.assert_not_called()
        self.assertEqual(processor._backend.calls, 1)

    def test_print_result_never_fails_on_vietnamese_console_text(self) -> None:
        result = ProcessingResult(
            session_id="session",
            sequence=1,
            audio_file="segment.wav",
            transcript_restored="Xin chào",
            translation="Máy chủ đang bận",
        )
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")

        with patch.object(sys, "stdout", console):
            SegmentProcessor.print_result(result)

        console.flush()
        output = raw.getvalue().decode("cp1252")
        console.detach()
        self.assertIn("TRN:", output)


if __name__ == "__main__":
    unittest.main()
