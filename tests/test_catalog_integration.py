"""Integration-style tests with network mocked."""

import json
from unittest.mock import patch

from ollama_advisor.catalog import get_catalog


SAMPLE_HTML = """
<html><body>
<a href="/library/llama3.1">llama3.1 Llama 3.1 general model tools 8b 70b 10M Pulls</a>
<a href="/library/qwen2.5-coder">qwen2.5-coder Coding model tools 7b 5M Pulls</a>
</body></html>
"""


def test_get_catalog_live_mocked(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr("ollama_advisor.catalog.CACHE_PATH", cache_file)

    with patch("ollama_advisor.catalog._fetch_library_html", return_value=SAMPLE_HTML):
        result = get_catalog(force_refresh=True)

    assert result["source"] == "live"
    assert len(result["models"]) >= 2
    ids = {m["identifier"] for m in result["models"]}
    assert "llama3.1" in ids
    assert "qwen2.5-coder" in ids


def test_get_catalog_uses_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache.json"
    payload = {
        "fetched_at": __import__("time").time(),
        "identifiers_hash": "abc",
        "models": [{"identifier": "cached-model", "description": "x", "variants": []}],
    }
    cache_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("ollama_advisor.catalog.CACHE_PATH", cache_file)

    result = get_catalog(force_refresh=False)
    assert result["from_cache"] is True
    assert result["models"][0]["identifier"] == "cached-model"
