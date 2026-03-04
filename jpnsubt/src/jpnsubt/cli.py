"""CLI interface using Click."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from jpnsubt import __version__
from jpnsubt.config import load_config, get
from jpnsubt.preprocess import preprocess_audio
from jpnsubt.subtitle import write_srt, write_vtt
from jpnsubt.transcribe import transcribe


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(name)s: %(message)s",
    )


@click.command()
@click.version_option(version=__version__)
@click.argument("input", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output subtitle file path (default: <input_stem>.srt).",
)
@click.option(
    "--format",
    type=click.Choice(["srt", "vtt"]),
    default="srt",
    help="Subtitle format (default: srt).",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Override Kotoba Whisper model ID (default: from config).",
)
@click.option(
    "--work-dir",
    type=click.Path(),
    default="jpnsubt_work",
    help="Working directory for intermediates (default: jpnsubt_work).",
)
@click.option(
    "--keep",
    is_flag=True,
    help="Keep intermediate WAV after run.",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Custom TOML config file.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose/debug output.",
)
def main(input, output, format, model, work_dir, keep, config, verbose):
    """
    Generate Japanese subtitles using Kotoba Whisper V2.0.

    INPUT: Path to video or audio file
    """
    setup_logging(verbose)
    logger = logging.getLogger("jpnsubt")

    try:
        # Load and merge config
        cfg = load_config(Path(config) if config else None)

        # Apply CLI overrides
        if model:
            if "transcribe" not in cfg:
                cfg["transcribe"] = {}
            cfg["transcribe"]["model"] = model

        # Resolve paths
        input_path = Path(input).resolve()
        work_dir_path = Path(work_dir)

        # Default output path: <input_stem>.<format>
        if not output:
            output = input_path.parent / f"{input_path.stem}.{format}"
        output_path = Path(output).resolve()

        logger.info(f"Input: {input_path}")
        logger.info(f"Output: {output_path}")

        # Stage 1: Preprocess audio
        audio_16k_path = work_dir_path / "audio_16k.wav"
        preprocess_audio(
            input_path,
            audio_16k_path,
            target_sample_rate=get(cfg, "preprocess", "target_sample_rate", default=16000),
            target_channels=get(cfg, "preprocess", "target_channels", default=1),
        )

        # Stage 2: Transcribe
        model_id = get(cfg, "transcribe", "model", default="kotoba-tech/kotoba-whisper-v2.0")
        cache_dir = get(cfg, "models", "cache_dir")
        segments = transcribe(
            audio_16k_path,
            model_id=model_id,
            language=get(cfg, "transcribe", "language", default="ja"),
            cache_dir=Path(cache_dir) if cache_dir else None,
        )

        # Stage 3: Write subtitle file
        if format == "vtt":
            write_vtt(segments, output_path)
        else:
            write_srt(segments, output_path)

        logger.info(f"✓ Subtitles written to {output_path}")

        # Cleanup (optional)
        if not keep and work_dir_path.exists():
            logger.info(f"Cleaning up {work_dir_path}")
            shutil.rmtree(work_dir_path)

    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
