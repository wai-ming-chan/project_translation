"""Pipeline orchestrator: wires stages together, manages state and caching."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from cantran.config import load_config, get
from cantran.types import PipelineContext, TranscribeResult, Segment
from cantran.utils import logger, console


STAGES = [
    "preprocess",
    "transcribe",
    "translate",
    "tts",
    "postprocess",
]


def run_pipeline(
    ctx: PipelineContext,
    config: Optional[dict] = None,
    skip_to: Optional[str] = None,
    subtitle_only: bool = False,
    play: bool = False,
) -> PipelineContext:
    """
    Run the full translation pipeline.

    Args:
        ctx: Pipeline context with source audio/video path set.
        config: Configuration dict (loaded from TOML).
        skip_to: Skip stages before this one (resume from cached results).
        subtitle_only: Only generate subtitles, no TTS.
        play: Play the output audio when done.

    Returns:
        Updated PipelineContext with all paths populated.
    """
    if config is None:
        config = load_config()

    stages_to_run = STAGES.copy()
    if skip_to and skip_to in stages_to_run:
        idx = stages_to_run.index(skip_to)
        stages_to_run = stages_to_run[idx:]
        logger.info(f"Skipping to stage: {skip_to}")

    if subtitle_only:
        # Only need preprocess, transcribe, translate
        stages_to_run = [s for s in stages_to_run if s in ("preprocess", "transcribe", "translate")]

    for stage_name in stages_to_run:
        console.rule(f"[bold blue]Stage: {stage_name}")
        _run_stage(stage_name, ctx, config)

    if play and ctx.final_audio and ctx.final_audio.exists():
        _play_audio(ctx.final_audio, config)

    return ctx


def _run_stage(name: str, ctx: PipelineContext, config: dict) -> None:
    """Run a single pipeline stage."""

    if name == "preprocess":
        from cantran.stages.preprocess import preprocess_audio, extract_audio_from_video

        stage_dir = ctx.stage_dir("02_audio")

        # Determine if input is video or audio
        source = ctx.raw_audio or ctx.source_path
        if source is None:
            raise ValueError("No source audio/video provided")

        suffix = source.suffix.lower()
        if suffix in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
            extracted = stage_dir / "extracted.wav"
            extract_audio_from_video(source, extracted)
            source = extracted

        ctx.processed_audio = preprocess_audio(
            source,
            stage_dir / "audio_16k.wav",
            target_sample_rate=get(config, "preprocess", "target_sample_rate", default=16000),
            target_channels=get(config, "preprocess", "target_channels", default=1),
        )

    elif name == "transcribe":
        from cantran.stages.transcribe import transcribe

        stage_dir = ctx.stage_dir("03_transcribe")

        if ctx.processed_audio is None:
            raise ValueError("No preprocessed audio available. Run preprocess first.")

        ctx.transcript = transcribe(
            ctx.processed_audio,
            model_name=get(config, "transcribe", "model",
                          default="mlx-community/whisper-large-v3-turbo"),
            language=ctx.source_lang if ctx.source_lang != "auto" else None,
        )

        # Save transcript
        ctx.transcript.save(stage_dir / "transcript.json")
        logger.info(f"Transcript saved to {stage_dir / 'transcript.json'}")

    elif name == "translate":
        from cantran.stages.translate import translate_segments

        stage_dir = ctx.stage_dir("04_translate")

        if ctx.transcript is None:
            # Try loading from cache
            cached = ctx.stage_dir("03_transcribe") / "transcript.json"
            if cached.exists():
                ctx.transcript = TranscribeResult.load(cached)
            else:
                raise ValueError("No transcript available. Run transcribe first.")

        ctx.translated_segments = translate_segments(
            ctx.transcript,
            model_path=get(config, "translate", "nllb_model",
                          default="facebook/nllb-200-distilled-600M"),
            source_lang=get(config, "translate", "source_lang"),
            target_lang=get(config, "translate", "target_lang", default="yue_Hant"),
            opencc_config=get(config, "translate", "opencc_config", default="s2hk"),
            qwen_model=get(config, "translate", "qwen_model",
                          default="mlx-community/Qwen3-8B-4bit"),
        )

        # Save translated segments
        data = [asdict(s) for s in ctx.translated_segments]
        (stage_dir / "translated.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )

    elif name == "tts":
        from cantran.stages.tts import synthesize_segments

        stage_dir = ctx.stage_dir("05_tts")

        if not ctx.translated_segments:
            # Try loading from cache
            cached = ctx.stage_dir("04_translate") / "translated.json"
            if cached.exists():
                data = json.loads(cached.read_text())
                ctx.translated_segments = [Segment(**s) for s in data]
            else:
                raise ValueError("No translated segments. Run translate first.")

        ctx.tts_segments = synthesize_segments(
            ctx.translated_segments,
            stage_dir,
            model_name=get(config, "tts", "model",
                          default="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"),
            voice=get(config, "tts", "voice", default="Cantonese_woman"),
        )

    elif name == "postprocess":
        from cantran.stages.postprocess import assemble_audio

        stage_dir = ctx.stage_dir("06_output")

        if not ctx.tts_segments:
            # Try loading from cache
            tts_dir = ctx.stage_dir("05_tts")
            cached_wavs = sorted(tts_dir.glob("seg_*.wav"))
            if cached_wavs:
                ctx.tts_segments = list(cached_wavs)
            else:
                raise ValueError("No TTS audio segments. Run tts first.")

        if not ctx.translated_segments:
            cached = ctx.stage_dir("04_translate") / "translated.json"
            if cached.exists():
                data = json.loads(cached.read_text())
                ctx.translated_segments = [Segment(**s) for s in data]

        ctx.final_audio = assemble_audio(
            ctx.translated_segments,
            ctx.tts_segments,
            stage_dir / "cantonese_audio.wav",
            max_speed_factor=get(config, "tts", "max_speed_factor", default=1.8),
        )

        # Copy to output path if specified
        if ctx.output_path:
            import shutil
            suffix = ctx.output_path.suffix.lower()
            if suffix in (".mp4", ".mkv", ".avi", ".mov") and ctx.source_path:
                from cantran.stages.mux import mux_audio_to_video
                mux_audio_to_video(ctx.source_path, ctx.final_audio, ctx.output_path)
            else:
                shutil.copy2(ctx.final_audio, ctx.output_path)
                logger.info(f"Output saved to {ctx.output_path}")


def generate_subtitles(
    ctx: PipelineContext,
    output_path: Path,
    format: str = "srt",
    bilingual: bool = True,
) -> Path:
    """Generate SRT or VTT subtitle file from translated segments."""
    from cantran.utils import format_timestamp, format_vtt_timestamp

    output_path = Path(output_path)
    segments = ctx.translated_segments
    if not segments:
        raise ValueError("No translated segments available")

    lines = []
    if format == "vtt":
        lines.append("WEBVTT\n")
        fmt = format_vtt_timestamp
    else:
        fmt = format_timestamp

    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{fmt(seg.start)} --> {fmt(seg.end)}")
        if bilingual:
            lines.append(seg.text)
        lines.append(seg.translated_text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Subtitles saved to {output_path}")
    return output_path


def _play_audio(audio_path: Path, config: dict) -> None:
    """Play audio using the configured playback command."""
    cmd = get(config, "playback", "command", default="afplay")
    logger.info(f"Playing audio: {audio_path}")
    subprocess.run([cmd, str(audio_path)])
