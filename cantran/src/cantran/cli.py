"""CLI interface using Click."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.panel import Panel

from cantran import __version__
from cantran.config import load_config, get
from cantran.utils import console, setup_logging


@click.group()
@click.version_option(version=__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug output.")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Custom config TOML file.")
@click.option("--cache-dir", type=click.Path(), default=None,
              help="Model cache directory (default: ~/.cache/huggingface).")
@click.pass_context
def main(ctx, verbose, config_path, cache_dir):
    """cantran — Offline video translation to Cantonese."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = load_config(Path(config_path) if config_path else None)
    setup_logging(verbose)

    # Set model cache directory: CLI flag > config > default
    from cantran.models import set_cache_dir
    cache = cache_dir or get(ctx.obj["config"], "models", "cache_dir")
    if cache:
        set_cache_dir(cache)


# === capture ===

@main.command()
@click.option("--duration", "-d", type=float, default=None, help="Recording duration in seconds (Ctrl+C to stop if not set).")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output WAV file path.")
@click.option("--translate", "do_translate", is_flag=True, help="Run full translation pipeline after capture.")
@click.option("--source-lang", type=click.Choice(["auto", "ja", "zh", "en"]), default="auto", help="Source language.")
@click.option("--play", is_flag=True, help="Play translated audio when done.")
@click.pass_context
def capture(ctx, duration, output, do_translate, source_lang, play):
    """Record audio from BlackHole (browser/system audio)."""
    from cantran.stages.capture import capture_audio
    from cantran.types import PipelineContext

    config = ctx.obj["config"]

    console.print(Panel(
        "[bold]Audio Capture[/bold]\n"
        "Make sure:\n"
        "1. System output is set to the BlackHole aggregate device\n"
        "2. Your video is playing in Safari (or any app)\n"
        "3. Other audio sources are muted",
        title="cantran capture",
        border_style="blue",
    ))

    if output is None:
        output = "cantran_work/01_capture/raw_capture.wav"

    output_path = Path(output)

    capture_audio(
        output_path,
        duration=duration,
        sample_rate=get(config, "capture", "sample_rate", default=44100),
        channels=get(config, "capture", "channels", default=2),
        device_name=get(config, "capture", "device_name", default="BlackHole 2ch"),
    )

    if do_translate:
        work_dir = Path(get(config, "output", "work_dir", default="cantran_work"))
        pipeline_ctx = PipelineContext(
            work_dir=work_dir,
            raw_audio=output_path,
            source_lang=source_lang,
            verbose=ctx.obj["verbose"],
        )

        from cantran.pipeline import run_pipeline
        run_pipeline(pipeline_ctx, config, play=play)

        if pipeline_ctx.final_audio:
            console.print(f"\n[green]✓[/green] Translation complete: {pipeline_ctx.final_audio}")
    else:
        console.print(f"\n[green]✓[/green] Audio saved: {output_path}")


# === translate ===

@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
@click.option("--source-lang", type=click.Choice(["auto", "ja", "zh", "en"]), default="auto", help="Source language.")
@click.option("--subtitle-only", is_flag=True, help="Only generate subtitles (SRT), no audio.")
@click.option("--subtitle-format", type=click.Choice(["srt", "vtt"]), default="srt", help="Subtitle format.")
@click.option("--play", is_flag=True, help="Play translated audio when done.")
@click.option("--keep-intermediates", is_flag=True, help="Keep intermediate files.")
@click.option("--skip-to", type=click.Choice(["preprocess", "transcribe", "translate", "tts", "postprocess"]),
              default=None, help="Skip to a specific stage (uses cached results).")
@click.pass_context
def translate(ctx, input_path, output, source_lang, subtitle_only, subtitle_format,
              play, keep_intermediates, skip_to):
    """Translate an audio or video file to Cantonese."""
    from cantran.types import PipelineContext
    from cantran.pipeline import run_pipeline, generate_subtitles

    config = ctx.obj["config"]
    input_path = Path(input_path)
    work_dir = Path(get(config, "output", "work_dir", default="cantran_work"))

    pipeline_ctx = PipelineContext(
        work_dir=work_dir,
        source_path=input_path,
        source_lang=source_lang,
        keep_intermediates=keep_intermediates,
        verbose=ctx.obj["verbose"],
        output_path=Path(output) if output else None,
    )

    run_pipeline(pipeline_ctx, config, skip_to=skip_to, subtitle_only=subtitle_only, play=play)

    if subtitle_only:
        sub_output = Path(output) if output else work_dir / f"subtitles.{subtitle_format}"
        generate_subtitles(pipeline_ctx, sub_output, format=subtitle_format)
        console.print(f"\n[green]✓[/green] Subtitles saved: {sub_output}")
    elif pipeline_ctx.final_audio:
        console.print(f"\n[green]✓[/green] Translation complete: {pipeline_ctx.final_audio}")
        if pipeline_ctx.output_path:
            console.print(f"  Output: {pipeline_ctx.output_path}")


# === transcribe ===

@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="Output JSON file path.")
@click.option("--source-lang", type=click.Choice(["auto", "ja", "zh", "en"]), default="auto", help="Source language.")
@click.pass_context
def transcribe(ctx, input_path, output, source_lang):
    """Transcribe an audio file (no translation)."""
    from cantran.stages.preprocess import preprocess_audio
    from cantran.stages.transcribe import transcribe as do_transcribe

    config = ctx.obj["config"]
    input_path = Path(input_path)
    work_dir = Path(get(config, "output", "work_dir", default="cantran_work"))
    work_dir.mkdir(parents=True, exist_ok=True)

    # Preprocess
    processed = work_dir / "audio_16k.wav"
    preprocess_audio(input_path, processed)

    # Transcribe
    result = do_transcribe(
        processed,
        model_name=get(config, "transcribe", "model",
                      default="mlx-community/whisper-large-v3-turbo"),
        language=source_lang if source_lang != "auto" else None,
    )

    # Save
    out = Path(output) if output else work_dir / "transcript.json"
    result.save(out)
    console.print(f"\n[green]✓[/green] Transcript saved: {out}")
    console.print(f"  Language: {result.language}")
    console.print(f"  Segments: {len(result.segments)}")
    console.print(f"  Duration: {result.audio_duration:.1f}s")


# === doctor ===

@main.command()
@click.pass_context
def doctor(ctx):
    """Check system setup: BlackHole, audio devices, models, ffmpeg."""
    import shutil
    from cantran.stages.capture import find_blackhole_device, list_audio_devices
    from cantran.models import REQUIRED_MODELS, check_model_cached

    console.print(Panel("[bold]cantran Doctor[/bold]", border_style="blue"))
    all_ok = True

    # Check ffmpeg
    console.print("\n[bold]ffmpeg:[/bold]")
    if shutil.which("ffmpeg"):
        console.print("  [green]✓[/green] ffmpeg found")
    else:
        console.print("  [red]✗[/red] ffmpeg not found — install with: brew install ffmpeg")
        all_ok = False

    # Check BlackHole
    console.print("\n[bold]BlackHole:[/bold]")
    bh = find_blackhole_device()
    if bh is not None:
        console.print(f"  [green]✓[/green] BlackHole device found (index {bh})")
    else:
        console.print("  [red]✗[/red] BlackHole not found — install with: brew install blackhole-2ch")
        console.print("    Then create an aggregate device in Audio MIDI Setup")
        all_ok = False

    # List audio input devices
    console.print("\n[bold]Audio input devices:[/bold]")
    for dev in list_audio_devices():
        marker = " ←" if "blackhole" in dev["name"].lower() else ""
        console.print(f"  [{dev['index']}] {dev['name']} ({dev['inputs']}ch){marker}")

    # Check models
    console.print("\n[bold]Models:[/bold]")
    for model in REQUIRED_MODELS:
        cached = check_model_cached(model.repo_id)
        if cached:
            console.print(f"  [green]✓[/green] {model.name} ({model.size_hint})")
        else:
            console.print(f"  [yellow]○[/yellow] {model.name} — not downloaded ({model.size_hint})")
            console.print(f"      Run: cantran models download --all")

    # Summary
    console.print()
    if all_ok:
        console.print("[bold green]All checks passed![/bold green]")
    else:
        console.print("[bold yellow]Some checks failed. See above for fixes.[/bold yellow]")


# === models ===

@main.group()
def models():
    """Manage translation models."""
    pass


@models.command("list")
def models_list():
    """List required models and their download status."""
    from cantran.models import list_models
    list_models()


@models.command("download")
@click.option("--all", "download_all", is_flag=True, help="Download all required models.")
@click.option("--model", "model_name", type=str, default=None, help="Download a specific model by name.")
def models_download(download_all, model_name):
    """Download models for offline use."""
    from cantran.models import download_all_models, download_model, REQUIRED_MODELS

    if download_all:
        console.print("[bold]Downloading all models...[/bold]")
        download_all_models()
    elif model_name:
        # Find by name
        match = next((m for m in REQUIRED_MODELS if m.name == model_name), None)
        if match:
            download_model(match.repo_id)
            console.print(f"[green]✓[/green] {match.name} downloaded")
        else:
            console.print(f"[red]Unknown model: {model_name}[/red]")
            console.print(f"Available: {', '.join(m.name for m in REQUIRED_MODELS)}")
    else:
        console.print("Specify --all or --model <name>")


main.add_command(models)
