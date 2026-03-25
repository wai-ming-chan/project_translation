# Project Translation

Translation and subtitle generation tools for video content. Contains two main CLI tools for Japanese and Cantonese workflows.

---

## 📋 Projects Overview

### 1. **cantran** — Offline Video Translation to Cantonese

A full-featured pipeline for translating and dubbing video content into Cantonese.

**What it does:**
- Captures audio from system (BlackHole) or takes input video/audio
- Transcribes speech to text (Japanese, Chinese, English → text)
- Translates text to English (if needed), then to Cantonese
- Generates Cantonese audio using TTS
- Aligns timing and outputs subtitles

**Full pipeline:**
```
Input Audio/Video → Extract Audio → Transcribe → Translate → TTS → Output
```

**Quick usage:**
```bash
cd cantran
uv run cantran capture --translate --source-lang ja  # Capture system audio and translate
uv run cantran process input.mp4 --source-lang ja     # Process existing file
```

**Output:**
- SRT subtitle file with translated text
- Optional: dubbed Cantonese audio/video

**Best for:**
- Converting Japanese video content to Cantonese subtitles + audio
- When you need both translation AND text subtitles

---

### 2. **jpnsubt** — Japanese Subtitle Generator

Lightweight tool for generating Japanese-only subtitles from video/audio.

**What it does:**
- Takes a video or audio file
- Extracts and normalizes audio to 16 kHz mono
- Transcribes using Kotoba Whisper V2.0 (Japanese-optimized model)
- Outputs SRT or WebVTT subtitle file

**Simple pipeline:**
```
Input Audio/Video → Preprocess → Transcribe → Output Subtitles
```

**Quick usage:**
```bash
cd jpnsubt
uv run jpnsubt input.mp4                    # Creates input.srt
uv run jpnsubt input.mp4 --format vtt       # Creates input.vtt
uv run jpnsubt input.mp4 -o output.srt      # Custom output path
```

**Output:**
- SRT or WebVTT subtitle file with Japanese text

**Best for:**
- Quick Japanese subtitle generation (no translation needed)
- When you only want text transcription
- Faster than cantran (no translation/TTS steps)

---

## 🚀 Quick Comparison

| Feature | cantran | jpnsubt |
|---------|---------|---------|
| **Transcription** | ✓ | ✓ |
| **Translation** | ✓ | ✗ (Japanese only) |
| **TTS/Audio** | ✓ | ✗ |
| **Output** | SRT + Audio | SRT/VTT only |
| **Speed** | Slower (full pipeline) | Faster (transcription only) |
| **Languages** | JPN/ZH/EN → CAN | Japanese only |
| **Use case** | Full dubbing workflow | Quick subtitles |

---

## 📁 Directory Structure

```
project_translation/
├── cantran/                    # Full translation + TTS pipeline
│   ├── src/cantran/            # Source code
│   ├── config/default.toml     # Configuration
│   ├── .venv/                  # Virtual environment
│   └── cantran_work/           # Working files (gitignored)
│
├── jpnsubt/                    # Japanese transcription only
│   ├── src/jpnsubt/            # Source code
│   ├── config/default.toml     # Configuration
│   ├── .venv/                  # Virtual environment
│   └── jpnsubt_work/           # Working files (gitignored)
│
├── media/                      # Video files (NOT tracked in git)
│   └── [project_name]/         # Organized by series/project
│
├── subtitles/                  # Generated/existing subtitle files (NOT tracked in git)
│   ├── [project_name]/
│   └── ...
│
├── dictionaries/               # Translation glossaries (NOT tracked in git)
│   ├── [project_name]/
│   │   ├── force_translate.csv
│   │   └── dont_translate.csv
│   └── ...
│
└── references/                 # Wiki pages, reference materials
```

---

## 🛠️ Setup

Both tools use Python 3.11 and `uv` package manager.

**First time setup:**
```bash
cd cantran
uv sync          # Installs dependencies

cd ../jpnsubt
uv sync          # Installs dependencies
```

**Running after setup:**
```bash
cd cantran
uv run cantran --help

cd ../jpnsubt
uv run jpnsubt --help
```

---

## 📝 Common Workflows

### Scenario 1: I have a Japanese video, want Japanese subtitles ONLY
→ Use **jpnsubt** (faster)
```bash
cd jpnsubt
uv run jpnsubt /path/to/video.mp4
```

### Scenario 2: I have a Japanese video, want Cantonese subtitles + audio
→ Use **cantran** (full pipeline)
```bash
cd cantran
uv run cantran process /path/to/video.mp4 --source-lang ja
```

### Scenario 3: I want to capture system audio and translate it live
→ Use **cantran capture**
```bash
cd cantran
uv run cantran capture --translate --source-lang ja
```

---

## 🔧 Configuration

Both tools use TOML config files in `config/default.toml`:

- **cantran**: Manages model selection, TTS voice, translation language, output format
- **jpnsubt**: Manages model selection, output format, work directory

Override config via CLI:
```bash
uv run jpnsubt input.mp4 --model kotoba-tech/kotoba-whisper-v2.0 --format vtt
```

---

## 📊 Model Status & Accuracy Issues

### Current Models & Performance

**jpnsubt (Japanese Transcription):**
- **Model**: Kotoba Whisper V2.0 (PyTorch)
- **Status**: ⚠️ **Accuracy needs improvement** — **Skips sentences frequently**
  - Misses dialogue segments, especially in fast-paced or noisy audio
  - Not production-ready without manual review and correction
  - Works better with clear, slower speech (not realistic for most video content)
- 🔄 **Future work**: May need to evaluate alternative Japanese speech-to-text models or fine-tuning

**cantran (Translation Pipeline):**
- **Transcription**: MLX Whisper (multilingual) — Similar issues as jpnsubt
- **Translation (Non-English → English)**: NLLB-200-distilled-600M (HF Transformers) — Moderate accuracy
- **Translation (English → Cantonese)**: Qwen3-8B-4bit — **Accuracy needs significant improvement**
  - Often produces unnatural Cantonese phrasing
  - Glossaries help with technical/proper nouns but don't solve fluency issues
  - Requires extensive post-editing for quality output
- 🔄 **Future work**: Plan to replace with better-performing Cantonese translation model

### Known Limitations
- ⚠️ Both tools require **manual review and correction** before production use
- 📝 **Recommendation**: Use only as first-pass draft generation; always human-review all output

---

## 🔒 Security Notes

### LiteLLM Vulnerability
This project **does NOT use LiteLLM** abstraction layer. We use direct model libraries instead:
- Direct HuggingFace Transformers API for translation
- Direct MLX Whisper / OpenAI Whisper for transcription

**Why this matters**: LiteLLM had a reported backdoor vulnerability ([Popular LiteLLM PyPI package backdoored to steal credentials, auth tokens](https://www.csoonline.com/article/651858/popular-litellm-pypi-package-backdoored-to-steal-credentials-auth-tokens/)) that could expose API keys. By avoiding this abstraction layer, we eliminate this attack vector entirely.

---

## 📚 Key Notes

- **Models**: Downloaded from HuggingFace Hub (configurable in `config/default.toml`)
- **FFmpeg**: Required for audio preprocessing (both tools)
- **Working files**: Intermediate files stored in `*_work/` dirs (auto-cleanup or use `--keep` flag)
- **Python 3.11**: Required with `uv` package manager for dependency management
- **No LiteLLM**: Direct model imports eliminate abstraction layer vulnerabilities
- **Alpha stage**: Both tools are in early development — accuracy improvements planned

---

## ⚡ Common Commands

```bash
# jpnsubt
uv run jpnsubt video.mp4                    # SRT subtitle
uv run jpnsubt video.mp4 --format vtt       # WebVTT subtitle
uv run jpnsubt video.mp4 --keep             # Keep intermediate audio
uv run jpnsubt video.mp4 -v                 # Verbose output

# cantran
uv run cantran capture --duration 30        # Record 30 seconds
uv run cantran capture --translate          # Full pipeline
uv run cantran process video.mp4            # Process file
uv run cantran --help                       # Show all commands
```

---

**Last updated:** 2026-03-02
