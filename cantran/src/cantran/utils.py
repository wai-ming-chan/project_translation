"""Utilities: logging, temp dirs, progress display."""

from __future__ import annotations

import gc
import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the cantran logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    return logging.getLogger("cantran")


logger = logging.getLogger("cantran")


@contextmanager
def work_directory(base: Path | None = None) -> Generator[Path, None, None]:
    """Create a temporary work directory, or use a specified one."""
    if base:
        base.mkdir(parents=True, exist_ok=True)
        yield base
    else:
        with tempfile.TemporaryDirectory(prefix="cantran_") as tmpdir:
            yield Path(tmpdir)


def unload_model(model: object) -> None:
    """Delete a model and force garbage collection to free RAM."""
    del model
    gc.collect()


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SRT."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_vtt_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm for VTT."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
