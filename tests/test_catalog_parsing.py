"""Tests for catalog card text parsing."""

from ollama_advisor.catalog import _estimate_memory_gb, _parse_card_text


def test_parse_llama31_card():
    text = (
        "llama3.1 Llama 3.1 is a new state-of-the-art model from Meta available "
        "in 8B, 70B and 405B parameter sizes. tools 8b 70b 405b "
        "118.4M Pulls 93 Tags Updated 1 year ago"
    )
    parsed = _parse_card_text(text)

    assert parsed["identifier"] == "llama3.1"
    assert "Llama 3.1 is a new state-of-the-art model" in parsed["description"]
    assert parsed["capabilities"] == ["tools"]
    assert parsed["param_sizes"] == ["8b", "70b", "405b"]
    assert parsed["pulls"] == "118.4M"
    assert len(parsed["variants"]) == 3
    assert parsed["variants"][0]["tag"] == "llama3.1:8b"
    assert parsed["variants"][0]["required_gb"] == _estimate_memory_gb("8b")


def test_parse_mixtral_card():
    text = (
        "mixtral A set of Mixture of Experts (MoE) model family from Mistral AI. "
        "tools 8x7b 8x22b 2.8M Pulls 70 Tags Updated 1 year ago"
    )
    parsed = _parse_card_text(text)

    assert parsed["identifier"] == "mixtral"
    assert "Mixture of Experts" in parsed["description"]
    assert parsed["capabilities"] == ["tools"]
    assert parsed["param_sizes"] == ["8x7b", "8x22b"]
    assert parsed["pulls"] == "2.8M"
    assert parsed["variants"][1]["required_gb"] == _estimate_memory_gb("8x22b")


def test_estimate_memory_moe():
    assert _estimate_memory_gb("8x7b") == round(56 * 0.6 + 1.0, 2)
    assert _estimate_memory_gb("7b") == round(7 * 0.6 + 1.0, 2)
