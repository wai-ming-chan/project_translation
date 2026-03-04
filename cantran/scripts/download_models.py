#!/usr/bin/env python3
"""Download all required models for offline use.

Usage:
    python scripts/download_models.py
    python scripts/download_models.py --list
"""

import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cantran.models import download_all_models, list_models


def main():
    if "--list" in sys.argv:
        list_models()
    else:
        print("Downloading all required models for cantran...")
        print("This may take a while on first run.\n")
        download_all_models()
        print("\nDone! Models are cached in ~/.cache/huggingface/")


if __name__ == "__main__":
    main()
