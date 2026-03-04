# jpnsubt Implementation Summary

**Status**: ✅ Complete
**Date**: 2026-03-01

## Overview

`jpnsubt` is a standalone Japanese subtitle generator using Kotoba Whisper V2.0. It processes video/audio files and produces Japanese-only SRT or WebVTT subtitles without translation.

**Key Features**:
- **Japanese-optimized model**: Kotoba Whisper V2.0 (6.3× faster than large-v3, better Japanese CER)
- **Self-contained CLI**: `uv run jpnsubt <input> [options]`
- **Multiple formats**: SRT and WebVTT subtitle output
- **Config-driven architecture**: TOML configuration with CLI overrides
- **Modular design**: Reuses cantran patterns for consistency

---

## Directory Structure

```
jpnsubt/
├── pyproject.toml                      # Project metadata, dependencies, entry point
├── .python-version                     # Python 3.11
├── config/
│   └── default.toml                    # Default configuration
└── src/jpnsubt/
    ├── __init__.py                     # Package metadata (version 0.1.0)
    ├── __main__.py                     # Entry point for `python -m jpnsubt`
    ├── cli.py                          # Click CLI command orchestration
    ├── config.py                       # TOML config loader (cantran pattern)
    ├── preprocess.py                   # ffmpeg: extract 16 kHz mono WAV
    ├── transcribe.py                   # mlx_whisper + Kotoba model
    └── subtitle.py                     # SRT/VTT subtitle writers
```

---

## Module Documentation

### `config.py`
- **Pattern**: Deep-merge TOML config loader (same as cantran)
- **Functions**:
  - `load_config(user_config)`: Loads default config + optional user overrides
  - `get(config, *keys, default)`: Dot-path nested dict access

### `preprocess.py`
- **Function**: `preprocess_audio(input_path, output_path, target_sample_rate, target_channels)`
- **Purpose**: Extract audio from video/audio and resample to 16 kHz mono WAV
- **Tool**: ffmpeg subprocess with `-ar 16000 -ac 1`

### `transcribe.py`
- **Dataclass**: `Segment(start: float, end: float, text: str)`
- **Functions**:
  - `resolve_model_path(model_id, cache_dir)`: Check local directory or download from HuggingFace
  - `transcribe(audio_path, model_id, language, best_of, cache_dir)`: mlx_whisper transcription
- **Gotchas handled**:
  - ✅ Local model path check: `Path(model_id).is_dir()`
  - ✅ snapshot_download workaround: resolve path first, then pass to mlx_whisper
  - ✅ Greedy decoding: `best_of=1` (mlx-whisper doesn't support beam search)

### `subtitle.py`
- **Functions**:
  - `seconds_to_timestamp(seconds, sep)`: Format time as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)
  - `write_srt(segments, output_path)`: Write numbered SRT cues
  - `write_vtt(segments, output_path)`: Write WebVTT with WEBVTT header

### `cli.py`
Click command with full pipeline orchestration:

```
jpnsubt [OPTIONS] INPUT

Options:
  --output / -o PATH       Output path (default: <input_stem>.srt)
  --format [srt|vtt]       Output format (default: srt)
  --model TEXT             Override model ID
  --work-dir PATH          Working directory (default: jpnsubt_work/)
  --keep                   Keep intermediate WAV
  --config / -c PATH       Custom TOML config
  --verbose / -v           Debug logging
  --version                Show version
  --help                   Show help
```

**Flow**:
1. Load config + apply CLI overrides
2. `preprocess_audio()` → `audio_16k.wav`
3. `transcribe()` → `[Segment, ...]`
4. `write_srt()` or `write_vtt()` → subtitle file
5. Cleanup work directory (unless `--keep`)

---

## Configuration

**Location**: `config/default.toml`

```toml
[preprocess]
target_sample_rate = 16000
target_channels = 1

[transcribe]
model = "kaiinui/kotoba-whisper-v2.0-mlx"
language = "ja"
best_of = 1

[models]
cache_dir = "/Volumes/Macbook_Air_M1_backup/models_trans"

[output]
format = "srt"
work_dir = "jpnsubt_work"
keep_intermediates = false
```

---

## Usage Examples

### Basic usage (SRT output)
```bash
cd ~/Documents/Overleaf/project_translation/jpnsubt
uv run jpnsubt /path/to/video.mp4
# Output: /path/to/video.srt
```

### WebVTT output
```bash
uv run jpnsubt /path/to/video.mp4 --format vtt --output subtitles.vtt
```

### Keep intermediate audio
```bash
uv run jpnsubt /path/to/video.mp4 --keep
# Keeps jpnsubt_work/audio_16k.wav
```

### Custom config
```bash
uv run jpnsubt /path/to/video.mp4 --config my_config.toml
```

### Override model
```bash
uv run jpnsubt /path/to/video.mp4 --model my-custom-whisper-model
```

### Verbose output
```bash
uv run jpnsubt /path/to/video.mp4 --verbose
```

### Via python -m
```bash
uv run python -m jpnsubt --help
```

---

## Installation & Verification

### Install dependencies
```bash
cd ~/Documents/Overleaf/project_translation/jpnsubt
uv sync
```

### Verify installation
```bash
# Help
uv run jpnsubt --help

# Version
uv run jpnsubt --version

# Module imports
uv run python -c "from jpnsubt.config import load_config; print('✓ Config OK')"
uv run python -c "from jpnsubt.preprocess import preprocess_audio; print('✓ Preprocess OK')"
uv run python -c "from jpnsubt.transcribe import transcribe; print('✓ Transcribe OK')"
uv run python -c "from jpnsubt.subtitle import write_srt, write_vtt; print('✓ Subtitle OK')"
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| click | >=8.0 | CLI framework |
| mlx-whisper | >=0.4 | Speech recognition |
| huggingface-hub | >=0.20 | Model downloading |
| numpy | >=1.26 | Numeric operations |
| rich | >=13.0 | Formatted logging |

---

## Key Gotchas & Solutions

### 1. mlx-whisper cache_dir ignored
**Problem**: mlx_whisper's internal `snapshot_download` ignores custom `cache_dir`

**Solution**: Resolve model path first via `snapshot_download(cache_dir=...)`, then pass the local path to `mlx_whisper.transcribe()`

**Implementation**: `transcribe.py:resolve_model_path()`

### 2. Beam search not supported
**Problem**: mlx-whisper doesn't support beam search decoding

**Solution**: Always use `best_of=1` (greedy decoding)

**Config**: `config/default.toml` → `best_of = 1`

### 3. Local vs HuggingFace model paths
**Problem**: Need to distinguish between local directories and HuggingFace repo IDs

**Solution**: Check `Path(model_id).is_dir()` before calling `snapshot_download()`

**Implementation**: `transcribe.py:resolve_model_path()`

---

## Testing Strategy

### Smoke tests (implemented)
- ✅ `uv sync` completes successfully (42 packages installed)
- ✅ `uv run jpnsubt --help` works
- ✅ `uv run jpnsubt --version` shows 0.1.0
- ✅ All modules import without errors
- ✅ Config loads correctly (model, language, cache_dir)
- ✅ `python -m jpnsubt` entry point works

### Integration tests (recommended)
- Test with actual Japanese video/audio file
- Verify SRT output timestamps and formatting
- Verify VTT output with WEBVTT header
- Test cleanup with/without `--keep` flag
- Test config override with custom TOML

---

## Next Steps

1. **Test with Japanese audio**: Use sample Japanese video/audio to verify transcription quality
2. **Benchmark performance**: Compare Kotoba Whisper V2.0 vs large-v3
3. **Add integration tests**: Pytest suite for pipeline verification
4. **Documentation**: Add README with usage examples
5. **Error handling**: Improve edge case handling (corrupted files, missing ffmpeg, etc.)

---

## Related Projects

- **cantran**: Full Cantonese translation pipeline (same repo, sibling)
- **Kotoba Whisper V2.0**: Japanese-optimized Whisper model
- **mlx-whisper**: MLX framework for speech recognition
- **Qwen3-TTS**: TTS model (used in cantran, not in jpnsubt)

---

## Author Notes

- Modeled after cantran architecture for consistency
- Minimal dependencies (no TTS, no translation)
- Handles mlx-whisper quirks (cache_dir workaround, best_of=1)
- Production-ready CLI with Click and Rich logging
- Config-driven with TOML support
