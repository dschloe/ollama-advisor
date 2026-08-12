"""Tests for purpose classification."""

from ollama_advisor.purpose import classify_purposes


def test_coding_keyword():
    purposes = classify_purposes("qwen2.5-coder", "Code generation model", ["tools"])
    assert "coding" in purposes
    assert "general" in purposes


def test_reasoning_thinking_label():
    purposes = classify_purposes("deepseek-r1", "Reasoning model", ["thinking"])
    assert "reasoning" in purposes


def test_reasoning_keyword_in_name():
    purposes = classify_purposes("qwq-32b", "Preview model", [])
    assert "reasoning" in purposes


def test_vision_label():
    purposes = classify_purposes("llava", "Vision assistant", ["vision"])
    assert "vision" in purposes
    assert "general" in purposes


def test_embedding_excludes_general():
    purposes = classify_purposes("nomic-embed-text", "Embedding model", ["embedding"])
    assert purposes == {"embedding"}


def test_embed_in_identifier():
    purposes = classify_purposes("mxbai-embed-large", "Text embeddings", [])
    assert "embedding" in purposes
    assert "general" not in purposes


def test_audio_label():
    purposes = classify_purposes("whisper", "Speech to text", ["audio"])
    assert "audio" in purposes


def test_coding_does_not_match_encoder_substring():
    purposes = classify_purposes("llava", "vision encoder model", ["vision"])
    assert "coding" not in purposes
    assert "vision" in purposes


def test_multiple_purposes():
    purposes = classify_purposes("llama3.2-vision", "Vision + tools", ["vision", "tools"])
    assert "vision" in purposes
    assert "general" in purposes
