from __future__ import annotations

import numpy as np

from prana_core.pipeline.segment_processor import apply_software_gain


def test_default_gain_does_not_normalize_quiet_audio() -> None:
    audio = np.array([-100, 100, -250, 250], dtype=np.int16)

    processed, rms, peak, clipping = apply_software_gain(audio, 0.0, 500.0)

    np.testing.assert_array_equal(processed, audio)
    assert peak == 250.0
    assert 0 < rms < 500
    assert clipping == 0.0


def test_gain_is_not_applied_below_speech_threshold() -> None:
    audio = np.full(160, 200, dtype=np.int16)

    processed, *_ = apply_software_gain(audio, 6.0, 500.0)

    np.testing.assert_array_equal(processed, audio)


def test_gain_is_limited_and_reports_clipping() -> None:
    audio = np.array([20_000, -20_000, 1_000, -1_000], dtype=np.int16)

    processed, _rms, _peak, clipping = apply_software_gain(
        audio, 6.0, 500.0
    )

    assert processed.max() == 32767
    assert processed.min() == -32768
    assert clipping == 0.5
