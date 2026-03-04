"""Mux translated audio into video file using ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cantran.utils import logger


def mux_audio_to_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    keep_original_audio: bool = True,
) -> Path:
    """
    Replace or add an audio track to a video file.

    Args:
        video_path: Original video file.
        audio_path: Translated Cantonese audio WAV.
        output_path: Output video path.
        keep_original_audio: If True, keep original as secondary track.

    Returns:
        Path to the output video.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    if keep_original_audio:
        # Add Cantonese as first audio track, keep original as second
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",       # video from input 0
            "-map", "1:a:0",       # Cantonese audio from input 1
            "-map", "0:a:0?",      # original audio from input 0 (optional)
            "-c:v", "copy",        # don't re-encode video
            "-c:a", "aac",
            "-metadata:s:a:0", "language=yue",
            "-metadata:s:a:0", "title=Cantonese (Translated)",
            "-shortest",
            str(output_path),
        ]
    else:
        # Replace audio entirely
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-metadata:s:a:0", "language=yue",
            "-shortest",
            str(output_path),
        ]

    logger.info(f"Muxing audio into video: {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg muxing failed:\n{result.stderr}")

    logger.info(f"Output video: {output_path}")
    return output_path
