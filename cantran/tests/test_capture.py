"""Tests for audio capture stage."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from cantran.stages.capture import list_audio_devices, find_blackhole_device


def test_list_audio_devices():
    """list_audio_devices should return a list of dicts with expected keys."""
    devices = list_audio_devices()
    assert isinstance(devices, list)
    for dev in devices:
        assert "index" in dev
        assert "name" in dev
        assert "inputs" in dev


def test_find_blackhole_device_missing():
    """find_blackhole_device returns None when device name doesn't match."""
    result = find_blackhole_device("NonExistentDevice12345")
    assert result is None
