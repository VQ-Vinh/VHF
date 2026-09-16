from __future__ import annotations

import threading
import unittest

from prana_core.console.polling import MAX_BACKOFF, MIN_BACKOFF, ResilientPoller


class _Recorder:
    def __init__(self):
        self.results: list[tuple[object, str | None, int]] = []
        self.event = threading.Event()

    def __call__(self, value, error, failures):
        self.results.append((value, type(error).__name__ if error else None, failures))
        self.event.set()


class ResilientPollerTests(unittest.TestCase):
    def test_delivers_values_and_can_be_stopped(self):
        sink = _Recorder()
        poller = ResilientPoller(lambda: "value", sink, interval=0.01)
        poller.start()
        self.assertTrue(sink.event.wait(2), "poller produced no result")
        poller.stop()
        self.assertFalse(poller.running)
        self.assertEqual(sink.results[0], ("value", None, 0))

    def test_failure_keeps_serving_the_last_good_value(self):
        """An operator watching a Station must not see the screen blank on a blip."""
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            if calls["n"] == 1:
                return "good"
            raise RuntimeError("boom")

        sink = _Recorder()
        poller = ResilientPoller(fetch, sink, interval=0.01)
        poller.start()
        deadline = threading.Event()
        deadline.wait(0.5)
        poller.stop()

        failures = [row for row in sink.results if row[1] == "RuntimeError"]
        self.assertTrue(failures, sink.results)
        # Value handed to the sink on failure is still the last good one.
        self.assertEqual(failures[0][0], "good")
        self.assertEqual(poller.last_value, "good")

    def test_backoff_grows_then_caps(self):
        poller = ResilientPoller(lambda: None, lambda *_: None, interval=2.0)
        self.assertEqual(poller._delay(), 2.0)
        poller._failures = 1
        self.assertEqual(poller._delay(), MIN_BACKOFF)
        poller._failures = 2
        self.assertEqual(poller._delay(), 2.0)
        poller._failures = 9
        self.assertEqual(poller._delay(), MAX_BACKOFF)

    def test_paused_poller_does_not_fetch(self):
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return calls["n"]

        poller = ResilientPoller(fetch, lambda *_: None, interval=0.01)
        poller.pause()
        poller.start()
        threading.Event().wait(0.2)
        poller.stop()
        self.assertEqual(calls["n"], 0)

    def test_a_failing_sink_does_not_kill_the_loop(self):
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return calls["n"]

        def sink(*_args):
            raise ValueError("sink exploded")

        poller = ResilientPoller(fetch, sink, interval=0.01)
        poller.start()
        threading.Event().wait(0.2)
        poller.stop()
        self.assertGreater(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
