"""Tests for TTS utilities (unit tests, no model loading)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from cantran.stages.postprocess import get_audio_duration, adjust_speed


def test_get_audio_duration(sample_audio):
    duration = get_audio_duration(sample_audio)
    assert duration == pytest.approx(2.0, abs=0.05)


def test_adjust_speed_no_change_needed(sample_audio, tmp_path):
    """When speed factor is close to 1.0, file should be copied as-is."""
    output = tmp_path / "adjusted.wav"
    result = adjust_speed(sample_audio, output, target_duration=2.0)
    assert result.exists()
