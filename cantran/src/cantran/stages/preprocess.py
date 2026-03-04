"""Audio preprocessing: resample and normalize via ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cantran.utils import logger


def preprocess_audio(
    input_path: Path,
    output_path: Path,
    target_sample_rate: int = 16000,
    target_channels: int = 1,
) -> Path:
    """
    Resample and convert audio to 16kHz mono WAV for Whisper.

    Uses ffmpeg subprocess for reliable format handling.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input audio not found: {input_path}")

    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i", str(input_path),
        "-ar", str(target_sample_rate),
        "-ac", str(target_channels),
        "-c:a", "pcm_s16le",
        "-f", "wav",
        str(output_path),
    ]

    logger.info(f"Preprocessing audio: {input_path.name} → {output_path.name}")
    logger.debug(f"ffmpeg command: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    if not output_path.exists():
        raise RuntimeError(f"ffmpeg did not produce output: {output_path}")

    logger.info(f"Preprocessed audio saved to {output_path}")
    return output_path


def extract_audio_from_video(video_path: Path, output_path: Path) -> Path:
    """Extract audio track from a video file."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",  # no video
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-f", "wav",
        str(output_path),
    ]

    logger.info(f"Extracting audio from video: {video_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

    return output_path
