"""Tests for translation utilities."""

from __future__ import annotations

import pytest

from cantran.stages.translate import _get_nllb_source_lang, _apply_opencc


def test_get_nllb_source_lang_from_whisper():
    assert _get_nllb_source_lang("ja") == "jpn_Jpan"
    assert _get_nllb_source_lang("en") == "eng_Latn"
    assert _get_nllb_source_lang("zh") == "zho_Hans"


def test_get_nllb_source_lang_override():
    assert _get_nllb_source_lang("ja", override="zho_Hans") == "zho_Hans"


def test_get_nllb_source_lang_unsupported():
    with pytest.raises(ValueError, match="Unsupported"):
        _get_nllb_source_lang("xx")


def test_apply_opencc_s2hk():
    """Test Simplified → Traditional HK conversion."""
    texts = ["计算机", "软件", "网络"]
    converted = _apply_opencc(texts, "s2hk")
    # s2hk converts simplified characters to traditional (HK standard)
    assert converted[0] == "計算機"
    assert converted[1] == "軟件"
    assert converted[2] == "網絡"
    assert len(converted) == 3
