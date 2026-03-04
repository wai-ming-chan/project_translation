"""Subtitle file writing (SRT and VTT formats)."""

from __future__ import annotations

import logging
from pathlib import Path

from jpnsubt.transcribe import Segment

logger = logging.getLogger("jpnsubt")


def seconds_to_timestamp(seconds: float, sep: str = ",") -> str:
    """
    Format seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT).

    Args:
        seconds: Time in seconds
        sep: Separator for milliseconds: ',' for SRT, '.' for VTT

    Returns:
        Formatted timestamp string
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def write_srt(segments: list[Segment], output_path: Path) -> None:
    """
    Write segments to SRT subtitle file.

    Args:
        segments: List of Segment objects
        output_path: Path to write SRT file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            start_ts = seconds_to_timestamp(segment.start, sep=",")
            end_ts = seconds_to_timestamp(segment.end, sep=",")
            f.write(f"{i}\n")
            f.write(f"{start_ts} --> {end_ts}\n")
            f.write(f"{segment.text}\n")
            f.write("\n")

    logger.info(f"Wrote {len(segments)} segments to {output_path}")


def write_vtt(segments: list[Segment], output_path: Path) -> None:
    """
    Write segments to WebVTT subtitle file.

    Args:
        segments: List of Segment objects
        output_path: Path to write VTT file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for segment in segments:
            start_ts = seconds_to_timestamp(segment.start, sep=".")
            end_ts = seconds_to_timestamp(segment.end, sep=".")
            f.write(f"{start_ts} --> {end_ts}\n")
            f.write(f"{segment.text}\n")
            f.write("\n")

    logger.info(f"Wrote {len(segments)} segments to {output_path}")
