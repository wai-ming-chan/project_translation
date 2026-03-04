"""Data types used across the pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Segment:
    """A single timestamped segment of speech."""

    start: float  # seconds
    end: float  # seconds
    text: str
    language: str = ""
    translated_text: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class TranscribeResult:
    """Result of the transcription stage."""

    segments: list[Segment]
    language: str  # detected or specified language code
    audio_duration: float = 0.0

    def save(self, path: Path) -> None:
        data = {
            "language": self.language,
            "audio_duration": self.audio_duration,
            "segments": [asdict(s) for s in self.segments],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> TranscribeResult:
        data = json.loads(path.read_text())
        segments = [Segment(**s) for s in data["segments"]]
        return cls(
            segments=segments,
            language=data["language"],
            audio_duration=data.get("audio_duration", 0.0),
        )


@dataclass
class PipelineContext:
    """Shared state passed through the pipeline."""

    work_dir: Path
    source_path: Optional[Path] = None  # original input file
    source_lang: str = "auto"
    keep_intermediates: bool = False
    verbose: bool = False

    # Paths populated by stages
    raw_audio: Optional[Path] = None
    processed_audio: Optional[Path] = None
    transcript: Optional[TranscribeResult] = None
    translated_segments: list[Segment] = field(default_factory=list)
    tts_segments: list[Path] = field(default_factory=list)
    final_audio: Optional[Path] = None
    output_path: Optional[Path] = None

    def stage_dir(self, name: str) -> Path:
        """Create and return a numbered stage directory."""
        d = self.work_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d
