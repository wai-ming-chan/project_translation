"""Speech-to-text transcription using mlx-whisper."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from cantran.types import Segment, TranscribeResult
from cantran.utils import logger, unload_model


# Language code mapping: Whisper codes → NLLB codes
WHISPER_TO_NLLB = {
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",
    "en": "eng_Latn",
    "ko": "kor_Hang",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
}


def transcribe(
    audio_path: Path,
    model_name: str = "mlx-community/whisper-large-v3-turbo",
    language: Optional[str] = None,
) -> TranscribeResult:
    """
    Transcribe audio to timestamped segments using mlx-whisper.

    Args:
        audio_path: Path to 16kHz mono WAV.
        model_name: HuggingFace model ID for mlx-whisper.
        language: Language code (ja/zh/en) or None for auto-detect.

    Returns:
        TranscribeResult with segments and detected language.
    """
    import mlx_whisper
    from huggingface_hub import snapshot_download
    from cantran.models import get_cache_dir

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(f"Transcribing with model: {model_name}")
    if language and language != "auto":
        logger.info(f"Source language: {language}")
    else:
        logger.info("Auto-detecting source language...")

    # Resolve model to local path using our cache_dir so mlx_whisper
    # doesn't re-download to the default ~/.cache/huggingface
    model_path = snapshot_download(
        repo_id=model_name, cache_dir=get_cache_dir()
    )

    decode_options = {}
    if language and language != "auto":
        decode_options["language"] = language

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=model_path,
        **decode_options,
    )

    detected_lang = result.get("language", language or "unknown")
    logger.info(f"Detected language: {detected_lang}")

    segments = []
    for seg in result.get("segments", []):
        segments.append(
            Segment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
                language=detected_lang,
            )
        )

    audio_duration = segments[-1].end if segments else 0.0
    logger.info(f"Transcribed {len(segments)} segments ({audio_duration:.1f}s)")

    return TranscribeResult(
        segments=segments,
        language=detected_lang,
        audio_duration=audio_duration,
    )
