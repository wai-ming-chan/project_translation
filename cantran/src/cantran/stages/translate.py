"""Translation: NLLB for non-EN→EN, Qwen3 for EN→Cantonese."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from cantran.types import Segment, TranscribeResult
from cantran.stages.transcribe import WHISPER_TO_NLLB
from cantran.utils import logger, unload_model


def _get_nllb_source_lang(whisper_lang: str, override: Optional[str] = None) -> str:
    """Convert a Whisper language code to NLLB language code."""
    if override and override != "auto":
        return override
    code = WHISPER_TO_NLLB.get(whisper_lang)
    if not code:
        raise ValueError(
            f"Unsupported source language '{whisper_lang}'. "
            f"Supported: {list(WHISPER_TO_NLLB.keys())}"
        )
    return code


def _nllb_to_english(
    texts: list[str],
    source_lang: str,
    nllb_model_path: str,
    cache_dir: Optional[str],
) -> list[str]:
    """Translate texts to English using NLLB-200."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    logger.info(f"Loading NLLB model for {source_lang} → English...")
    tokenizer = AutoTokenizer.from_pretrained(nllb_model_path, cache_dir=cache_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_path, cache_dir=cache_dir)

    tokenizer.src_lang = source_lang
    target_token_id = tokenizer.convert_tokens_to_ids("eng_Latn")

    results = []
    for text in texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        output = model.generate(
            **inputs,
            forced_bos_token_id=target_token_id,
            max_new_tokens=128,
            num_beams=4,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
        )
        translated = tokenizer.decode(output[0], skip_special_tokens=True)
        results.append(translated)

    unload_model(model)
    unload_model(tokenizer)

    return results


def _qwen_to_cantonese(
    texts: list[str],
    qwen_model_path: str,
    cache_dir: Optional[str],
) -> list[str]:
    """Translate English texts to Cantonese using Qwen3 via mlx-lm."""
    from mlx_lm import load, generate

    # Resolve model to local path (skip download if already a local directory)
    if Path(qwen_model_path).is_dir():
        model_path = qwen_model_path
    else:
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(repo_id=qwen_model_path, cache_dir=cache_dir)

    logger.info(f"Loading Qwen for EN → Cantonese...")
    model, tokenizer = load(model_path)

    # Check if model supports chat template (instruct models) or needs
    # completion-style prompts (base models)
    has_chat = hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template

    system_prompt = (
        "你係一個專業嘅英文翻譯廣東話嘅翻譯員。"
        "將以下英文翻譯成道地嘅香港廣東話口語。"
        "要求：\n"
        "1. 用廣東話口語，唔好用書面語或者普通話\n"
        "2. 用繁體字，用香港慣用詞彙（例如：係、唔、嘅、咗、嚟、啲、冇、喺）\n"
        "3. 只輸出翻譯結果，唔好加任何解釋\n"
        "4. 保持原文嘅語氣同情感"
    )

    results = []
    for text in texts:
        if has_chat:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text + "\n/no_think"},
            ]
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
        else:
            # Completion-style prompt for base models
            prompt = (
                f"Translate the following English text into colloquial Hong Kong Cantonese "
                f"(廣東話). Use traditional characters and Cantonese vocabulary "
                f"(係、唔、嘅、咗、嚟、啲、冇、喺). Output only the translation.\n\n"
                f"English: {text}\n"
                f"廣東話："
            )

        response = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=1024,
            verbose=False,
        )
        # Strip Qwen3 <think>...</think> reasoning block if present
        response = re.sub(r"<think>.*?</think>\s*", "", response, flags=re.DOTALL)
        # Handle unclosed <think> block (ran out of tokens during thinking)
        response = re.sub(r"<think>.*", "", response, flags=re.DOTALL)
        # Clean up: take first line only (base models may ramble)
        response = response.strip().split("\n")[0].strip()
        results.append(response)
        logger.info(f"  EN: {text}")
        logger.info(f"  粵: {response}")

    unload_model(model)
    unload_model(tokenizer)

    return results


def _apply_opencc(texts: list[str], config: str = "s2hk") -> list[str]:
    """Convert Simplified Chinese to Traditional Chinese (HK) using OpenCC."""
    from opencc import OpenCC
    converter = OpenCC(config)
    return [converter.convert(t) for t in texts]


def translate_segments(
    transcript: TranscribeResult,
    model_path: str = "facebook/nllb-200-distilled-600M",
    source_lang: Optional[str] = None,
    target_lang: str = "yue_Hant",
    opencc_config: str = "s2hk",
    two_hop_for_ja: bool = True,
    qwen_model: str = "mlx-community/Qwen3-8B-4bit",
) -> list[Segment]:
    """
    Translate transcribed segments to Cantonese.

    Pipeline:
    - If source is English: EN → Cantonese (Qwen2.5)
    - If source is JA/ZH/other: source → EN (NLLB) → Cantonese (Qwen2.5)

    Args:
        transcript: TranscribeResult from the transcription stage.
        model_path: HuggingFace model ID for NLLB (used for non-EN→EN).
        source_lang: Override source language (NLLB code).
        target_lang: Target language code (unused, always Cantonese).
        opencc_config: OpenCC config for character normalization.
        two_hop_for_ja: If True and source is JA, go JA→EN→Cantonese.
        qwen_model: HuggingFace model ID for Qwen2.5 (EN→Cantonese).

    Returns:
        List of Segments with translated_text populated.
    """
    from cantran.models import get_cache_dir

    nllb_source = _get_nllb_source_lang(transcript.language, source_lang)
    cache_dir = get_cache_dir()
    texts = [s.text for s in transcript.segments]

    # Step 1: Get English text
    if nllb_source == "eng_Latn":
        logger.info("Source is English, skipping NLLB step")
        en_texts = texts
    else:
        logger.info(f"Step 1: {nllb_source} → English (NLLB)")
        en_texts = _nllb_to_english(texts, nllb_source, model_path, cache_dir)
        logger.info(f"  Intermediate EN: {en_texts}")

    # Step 2: English → Cantonese (Qwen2.5)
    logger.info("Step 2: English → Cantonese (Qwen2.5)")
    translated = _qwen_to_cantonese(en_texts, qwen_model, cache_dir)

    # Step 3: Normalize characters with OpenCC (ensure Traditional HK)
    logger.info(f"Applying OpenCC ({opencc_config}) character normalization...")
    translated = _apply_opencc(translated, opencc_config)

    # Populate segments
    result_segments = []
    for seg, trans_text in zip(transcript.segments, translated):
        new_seg = Segment(
            start=seg.start,
            end=seg.end,
            text=seg.text,
            language=seg.language,
            translated_text=trans_text,
        )
        result_segments.append(new_seg)

    logger.info(f"Translated {len(result_segments)} segments to Cantonese")
    return result_segments
