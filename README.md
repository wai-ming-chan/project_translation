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
- Converting Japanese anime/drama to Cantonese subtitles + audio
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
├── media/                      # Video files
│   └── G_GUNDAM/               # Organized by series
│
├── subtitles/                  # Generated/existing subtitle files
│   ├── G_GUNDAM/
│   ├── Chiikawa/
│   └── ...
│
├── dictionaries/               # Translation glossaries (CSV)
│   ├── G_GUNDAM/
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
uv run jpnsubt input.mp4 --model kaiinui/kotoba-whisper-v2.0-mlx --format vtt
```

---

## 📚 Key Notes

- **Models**: Downloaded from HuggingFace Hub (cached in `/Volumes/Macbook_Air_M1_backup/models_trans/`)
- **FFmpeg**: Required for audio preprocessing (both tools)
- **Working files**: Intermediate files stored in `*_work/` dirs (auto-cleanup or use `--keep` flag)
- **Fast on Apple Silicon**: Both tools use MLX (optimized for M1/M2/M3 Macs)

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
