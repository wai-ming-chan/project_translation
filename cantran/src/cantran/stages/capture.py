"""Audio capture from BlackHole virtual audio device."""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf
from rich.live import Live
from rich.text import Text

from cantran.utils import console, logger


def list_audio_devices() -> list[dict]:
    """Return all available audio devices."""
    devices = sd.query_devices()
    return [
        {"index": i, "name": d["name"], "inputs": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


def find_blackhole_device(device_name: str = "BlackHole 2ch") -> Optional[int]:
    """Find the BlackHole device index, or None if not found."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if device_name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    return None


def capture_audio(
    output_path: Path,
    duration: Optional[float] = None,
    sample_rate: int = 44100,
    channels: int = 2,
    device_name: str = "BlackHole 2ch",
) -> Path:
    """
    Record audio from BlackHole until duration elapsed or Ctrl+C.

    The user should be playing video in Safari (or any app) before calling this.
    System audio output must be set to the BlackHole aggregate device.
    """
    device_idx = find_blackhole_device(device_name)
    if device_idx is None:
        raise RuntimeError(
            f"Could not find audio device '{device_name}'. "
            "Make sure BlackHole is installed and an aggregate device is configured. "
            "Run 'cantran doctor' for setup help."
        )

    logger.info(f"Recording from device: {sd.query_devices(device_idx)['name']}")
    if duration:
        logger.info(f"Recording for {duration:.0f} seconds...")
    else:
        logger.info("Recording until Ctrl+C...")

    frames: list[np.ndarray] = []
    stopped = False

    def _stop_handler(signum, frame):
        nonlocal stopped
        stopped = True

    old_handler = signal.signal(signal.SIGINT, _stop_handler)

    try:
        block_size = int(sample_rate * 0.1)  # 100ms blocks
        elapsed = 0.0

        with Live(console=console, refresh_per_second=10) as live:
            with sd.InputStream(
                device=device_idx,
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
                blocksize=block_size,
            ) as stream:
                while not stopped:
                    if duration and elapsed >= duration:
                        break

                    data, overflowed = stream.read(block_size)
                    if overflowed:
                        logger.warning("Audio buffer overflow — some audio may be lost")
                    frames.append(data.copy())
                    elapsed += block_size / sample_rate

                    # Show live status
                    peak = np.abs(data).max()
                    bar_len = int(min(peak * 50, 50))
                    bar = "█" * bar_len + "░" * (50 - bar_len)
                    mins, secs = divmod(int(elapsed), 60)
                    live.update(
                        Text(f"  ● REC  {mins:02d}:{secs:02d}  [{bar}]  peak={peak:.3f}")
                    )

    finally:
        signal.signal(signal.SIGINT, old_handler)

    if not frames:
        raise RuntimeError("No audio was captured.")

    audio_data = np.concatenate(frames, axis=0)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio_data, sample_rate)

    total = len(audio_data) / sample_rate
    logger.info(f"Saved {total:.1f}s of audio to {output_path}")
    return output_path
