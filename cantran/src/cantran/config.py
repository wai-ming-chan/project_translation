"""Configuration loading with layered defaults."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "default.toml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, recursing into nested dicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(user_config: Path | None = None) -> dict[str, Any]:
    """Load default config, optionally overridden by a user config file."""
    config: dict[str, Any] = {}

    if _DEFAULT_CONFIG.exists():
        config = tomllib.loads(_DEFAULT_CONFIG.read_text())

    if user_config and user_config.exists():
        user = tomllib.loads(user_config.read_text())
        config = _deep_merge(config, user)

    return config


def get(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Dot-path access into nested config: get(cfg, 'transcribe', 'model')."""
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
