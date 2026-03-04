"""Post-processing: timing alignment, speed adjustment, audio assembly."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from cantran.types import Segment
from cantran.utils import logger


def get_audio_duration(path: Path) -> float:
    """Get duration of an audio file in seconds."""
    info = sf.info(str(path))
    return info.duration


def adjust_speed(
    input_path: Path,
    output_path: Path,
    target_duration: float,
    max_speed_factor: float = 1.8,
) -> Path:
    """
    Adjust audio speed to match target duration using ffmpeg atempo.

    If the TTS output is longer than the original segment, speed it up.
    If shorter, pad with silence.
    """
    actual_duration = get_audio_duration(input_path)

    if actual_duration <= 0:
        return input_path

    speed_factor = actual_duration / target_duration

    if speed_factor > max_speed_factor:
        logger.warning(
            f"Speed factor {speed_factor:.2f}x exceeds max {max_speed_factor}x, capping"
        )
        speed_factor = max_speed_factor
    elif speed_factor < 0.5:
        # Don't slow down too much — just pad
        speed_factor = 1.0

    if abs(speed_factor - 1.0) < 0.05:
        # Close enough, no adjustment needed
        if input_path != output_path:
            import shutil
            shutil.copy2(input_path, output_path)
        return output_path

    # ffmpeg atempo filter (range 0.5–2.0)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-filter:a", f"atempo={speed_factor:.4f}",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Speed adjustment failed: {result.stderr}")
        return input_path

    return output_path


def assemble_audio(
    segments: list[Segment],
    tts_paths: list[Optional[Path]],
    output_path: Path,
    sample_rate: int = 24000,
    max_speed_factor: float = 1.8,
) -> Path:
    """
    Assemble TTS segments into a single audio file with proper timing.

    Each segment is placed at its original timestamp. Gaps are filled with silence.
    TTS audio that runs too long is sped up to fit.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not segments:
        raise ValueError("No segments to assemble")

    total_duration = max(s.end for s in segments)
    total_samples = int(total_duration * sample_rate) + sample_rate  # +1s buffer
    output_audio = np.zeros(total_samples, dtype=np.float32)

    temp_dir = output_path.parent / "_temp_speed"
    temp_dir.mkdir(exist_ok=True)

    for i, (seg, tts_path) in enumerate(zip(segments, tts_paths)):
        if tts_path is None or not tts_path.exists():
            continue

        # Compute available time: segment duration + gap before next segment
        # This allows TTS to spill into natural pauses instead of aggressive speedup
        if i + 1 < len(segments):
            next_start = segments[i + 1].start
            available = next_start - seg.start
        else:
            available = seg.duration

        tts_duration = get_audio_duration(tts_path)
        # Use the gap only if TTS actually needs more time than the segment
        if tts_duration > seg.duration and available > seg.duration:
            target_duration = min(available, tts_duration)
            logger.info(
                f"Segment {i}: TTS={tts_duration:.2f}s, slot={seg.duration:.2f}s, "
                f"using gap → {target_duration:.2f}s budget"
            )
        else:
            target_duration = seg.duration

        # Adjust speed if needed
        adjusted_path = temp_dir / f"adj_{i:04d}.wav"
        adjust_speed(tts_path, adjusted_path, target_duration, max_speed_factor)

        # Read adjusted audio
        audio_data, sr = sf.read(str(adjusted_path))
        if sr != sample_rate:
            # Quick resample via ffmpeg
            resampled = temp_dir / f"res_{i:04d}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(adjusted_path),
                 "-ar", str(sample_rate), "-ac", "1",
                 "-c:a", "pcm_s16le", str(resampled)],
                capture_output=True,
            )
            audio_data, _ = sf.read(str(resampled))

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # Place at the correct position
        start_sample = int(seg.start * sample_rate)
        end_sample = start_sample + len(audio_data)

        if end_sample > len(output_audio):
            # Extend if needed
            extra = np.zeros(end_sample - len(output_audio), dtype=np.float32)
            output_audio = np.concatenate([output_audio, extra])

        output_audio[start_sample:start_sample + len(audio_data)] = audio_data.astype(np.float32)

    # Trim trailing silence
    last_nonzero = np.max(np.nonzero(output_audio)) if np.any(output_audio) else 0
    output_audio = output_audio[:last_nonzero + sample_rate]

    sf.write(str(output_path), output_audio, sample_rate)
    logger.info(f"Assembled audio: {len(output_audio)/sample_rate:.1f}s → {output_path}")

    # Clean up temp
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    return output_path
