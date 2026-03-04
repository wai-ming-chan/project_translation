"""Text-to-speech using Qwen3-TTS via mlx-audio."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from cantran.types import Segment
from cantran.utils import logger, unload_model


def synthesize_segments(
    segments: list[Segment],
    output_dir: Path,
    model_name: str = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
    voice: str = "Cantonese_woman",
) -> list[Path]:
    """
    Generate Cantonese speech audio for each translated segment.

    Args:
        segments: Segments with translated_text populated.
        output_dir: Directory to write individual WAV files.
        model_name: HuggingFace model ID for TTS.
        voice: Voice/speaker identifier.

    Returns:
        List of paths to generated WAV files, one per segment.
    """
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model
    from cantran.models import get_cache_dir
    from huggingface_hub import snapshot_download

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating TTS with model: {model_name}")
    logger.info(f"Voice: {voice}, Segments: {len(segments)}")

    # Resolve model to local path using our cache dir
    model_path = snapshot_download(
        repo_id=model_name, cache_dir=get_cache_dir()
    )

    # Load model once, reuse for all segments
    logger.info("Loading TTS model...")
    model = load_model(model_path)

    output_paths = []
    for i, seg in enumerate(segments):
        if not seg.translated_text.strip():
            logger.debug(f"Segment {i}: empty text, skipping")
            output_paths.append(None)
            continue

        out_prefix = str(output_dir / f"seg_{i:04d}")
        out_path = output_dir / f"seg_{i:04d}.wav"

        logger.info(f"Segment {i}: {seg.translated_text[:60]}...")

        generate_audio(
            text=seg.translated_text,
            model=model,
            voice=voice,
            lang_code="yue",
            file_prefix=out_prefix,
            audio_format="wav",
            verbose=False,
        )

        # generate_audio writes to {prefix}_000.wav for single segments
        generated = output_dir / f"seg_{i:04d}_000.wav"
        if generated.exists():
            generated.rename(out_path)
            output_paths.append(out_path)
            logger.debug(f"  -> saved {out_path.name}")
        elif out_path.exists():
            output_paths.append(out_path)
        else:
            logger.warning(f"  Segment {i}: no audio generated")
            output_paths.append(None)

    valid = sum(1 for p in output_paths if p is not None)
    logger.info(f"Generated {valid}/{len(segments)} TTS audio files")

    unload_model(model)

    return output_paths
