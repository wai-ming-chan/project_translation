"""Transcription using Kotoba Whisper V2.0 (PyTorch via whisper)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import snapshot_download

logger = logging.getLogger("jpnsubt")


@dataclass
class Segment:
    """A transcribed segment with timing."""

    start: float
    end: float
    text: str


def resolve_model_path(model_id: str, cache_dir: Path | None = None) -> str:
    """
    Resolve model path: check if it's a local directory, otherwise download.
    """
    model_path = Path(model_id)

    # If model_id is already a local directory, use it directly
    if model_path.is_dir():
        logger.info(f"Using local model: {model_id}")
        return str(model_path)

    # Otherwise, download from HuggingFace Hub
    logger.info(f"Downloading model: {model_id}")
    cache_dir = Path(cache_dir) if cache_dir else None
    local_path = snapshot_download(
        repo_id=model_id,
        cache_dir=str(cache_dir) if cache_dir else None,
    )
    logger.info(f"Model downloaded to: {local_path}")
    return local_path


def transcribe(
    audio_path: Path,
    model_id: str,
    language: str = "ja",
    cache_dir: Path | None = None,
) -> list[Segment]:
    """
    Transcribe audio using Kotoba Whisper V2.0 via OpenAI Whisper.

    Args:
        audio_path: Path to audio file (any format supported by ffmpeg)
        model_id: HuggingFace model ID (e.g., "kotoba-tech/kotoba-whisper-v2.0")
        language: Language code (e.g., "ja" for Japanese)
        cache_dir: Optional model cache directory

    Returns:
        List of Segment objects with start time, end time, and transcribed text
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(f"Transcribing: {audio_path.name}")

    # Resolve model path
    model_path = resolve_model_path(model_id, cache_dir)

    try:
        import whisper

        logger.info("Loading model...")
        # Load the model from local path directly
        model = whisper.load_model(model_path, device="cpu", in_memory=False)

        logger.info("Transcribing audio...")
        result = model.transcribe(
            str(audio_path),
            language=language,
            verbose=False,
        )

        # Convert result to Segment objects
        segments = []
        for chunk in result["segments"]:
            text = chunk["text"].strip()
            # Skip empty segments
            if text:
                segment = Segment(
                    start=chunk["start"],
                    end=chunk["end"],
                    text=text,
                )
                segments.append(segment)

        logger.info(f"Transcribed {len(segments)} segments")
        return segments

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
