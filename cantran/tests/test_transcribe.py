"""Tests for transcription types and utilities."""

from __future__ import annotations

import json
from pathlib import Path

from cantran.types import Segment, TranscribeResult
from cantran.stages.transcribe import WHISPER_TO_NLLB


def test_segment_duration():
    seg = Segment(start=1.0, end=3.5, text="hello")
    assert seg.duration == pytest.approx(2.5)


def test_transcribe_result_save_load(tmp_path):
    segments = [
        Segment(start=0.0, end=2.0, text="Test one", language="en"),
        Segment(start=2.0, end=4.0, text="Test two", language="en"),
    ]
    result = TranscribeResult(segments=segments, language="en", audio_duration=4.0)

    path = tmp_path / "transcript.json"
    result.save(path)

    loaded = TranscribeResult.load(path)
    assert loaded.language == "en"
    assert loaded.audio_duration == 4.0
    assert len(loaded.segments) == 2
    assert loaded.segments[0].text == "Test one"
    assert loaded.segments[1].start == 2.0


def test_whisper_to_nllb_mapping():
    assert WHISPER_TO_NLLB["ja"] == "jpn_Jpan"
    assert WHISPER_TO_NLLB["zh"] == "zho_Hans"
    assert WHISPER_TO_NLLB["en"] == "eng_Latn"


import pytest
