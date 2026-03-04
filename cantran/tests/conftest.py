"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def sample_audio(tmp_path):
    """Create a short sine-wave WAV file for testing."""
    import soundfile as sf

    duration = 2.0  # seconds
    sample_rate = 16000
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    path = tmp_path / "test_audio.wav"
    sf.write(str(path), audio, sample_rate)
    return path


@pytest.fixture
def sample_transcript(tmp_path):
    """Create a sample transcript JSON for testing."""
    data = {
        "language": "en",
        "audio_duration": 10.0,
        "segments": [
            {
                "start": 0.0,
                "end": 3.5,
                "text": "Hello, this is a test.",
                "language": "en",
                "translated_text": "",
            },
            {
                "start": 3.5,
                "end": 7.0,
                "text": "The weather is nice today.",
                "language": "en",
                "translated_text": "",
            },
            {
                "start": 7.0,
                "end": 10.0,
                "text": "Goodbye everyone.",
                "language": "en",
                "translated_text": "",
            },
        ],
    }
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(data, indent=2))
    return path
