"""Model download, cache, and verification via huggingface_hub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from huggingface_hub import snapshot_download
from rich.table import Table

from cantran.utils import console, logger

# Module-level cache dir, set via set_cache_dir() from CLI/config
_cache_dir: Optional[str] = None


def set_cache_dir(path: Optional[str]) -> None:
    """Set the HuggingFace cache directory for all model operations."""
    global _cache_dir
    if path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        _cache_dir = str(p)
        logger.info(f"Model cache directory: {_cache_dir}")
    else:
        _cache_dir = None


def get_cache_dir() -> Optional[str]:
    """Return the configured cache directory, or None for default."""
    return _cache_dir


@dataclass
class ModelInfo:
    """Information about a required model."""

    name: str
    repo_id: str
    description: str
    stage: str
    size_hint: str  # approximate size


REQUIRED_MODELS = [
    ModelInfo(
        name="whisper-large-v3-turbo",
        repo_id="mlx-community/whisper-large-v3-turbo",
        description="Speech-to-text (MLX Whisper)",
        stage="transcribe",
        size_hint="~1.5 GB",
    ),
    ModelInfo(
        name="nllb-200-distilled-600M",
        repo_id="facebook/nllb-200-distilled-600M",
        description="Translation non-EN → EN (NLLB-200)",
        stage="translate",
        size_hint="~2.5 GB",
    ),
    ModelInfo(
        name="qwen3-8b",
        repo_id="mlx-community/Qwen3-8B-4bit",
        description="Translation EN → Cantonese (Qwen3 MLX 4-bit)",
        stage="translate",
        size_hint="~5 GB",
    ),
    ModelInfo(
        name="qwen3-tts-0.6b",
        repo_id="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        description="Text-to-speech (Qwen3-TTS MLX 4-bit)",
        stage="tts",
        size_hint="~400 MB",
    ),
]


def download_model(repo_id: str, force: bool = False) -> Path:
    """Download a model from HuggingFace Hub. Returns local cache path."""
    logger.info(f"Downloading model: {repo_id}")
    path = snapshot_download(
        repo_id=repo_id,
        local_files_only=False,
        cache_dir=_cache_dir,
    )
    logger.info(f"Model cached at: {path}")
    return Path(path)


def download_all_models(force: bool = False) -> None:
    """Download all required models for offline use."""
    if _cache_dir:
        console.print(f"  Cache dir: {_cache_dir}\n")
    for model in REQUIRED_MODELS:
        try:
            download_model(model.repo_id, force=force)
            console.print(f"  [green]✓[/green] {model.name} ({model.size_hint})")
        except Exception as e:
            console.print(f"  [red]✗[/red] {model.name}: {e}")


def check_model_cached(repo_id: str) -> bool:
    """Check if a model is already downloaded in the HF cache."""
    try:
        snapshot_download(repo_id=repo_id, local_files_only=True, cache_dir=_cache_dir)
        return True
    except Exception:
        return False


def list_models() -> None:
    """Print a table of required models and their download status."""
    table = Table(title="cantran Models")
    table.add_column("Model", style="cyan")
    table.add_column("Stage", style="green")
    table.add_column("Size", style="yellow")
    table.add_column("Cached", style="bold")

    for model in REQUIRED_MODELS:
        cached = check_model_cached(model.repo_id)
        status = "[green]✓ yes[/green]" if cached else "[red]✗ no[/red]"
        table.add_row(model.name, model.stage, model.size_hint, status)

    if _cache_dir:
        console.print(f"Cache dir: {_cache_dir}\n")
    console.print(table)
