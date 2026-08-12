"""Tests for catalog snapshot export (offline)."""

from ollama_advisor.snapshot import (
    diff_identifiers,
    models_to_rows,
    write_catalog_snapshot,
    write_csv,
)


SAMPLE_MODELS = [
    {
        "identifier": "llama3.1",
        "description": "Meta Llama 3.1",
        "capabilities": ["tools"],
        "pulls": "100M",
        "purposes": ["general"],
        "variants": [
            {"tag": "llama3.1:8b", "param_size": "8b", "required_gb": 5.8},
        ],
    },
    {
        "identifier": "qwen2.5-coder",
        "description": "Code model",
        "capabilities": ["tools"],
        "pulls": "20M",
        "purposes": ["coding", "general"],
        "variants": [
            {"tag": "qwen2.5-coder:7b", "param_size": "7b", "required_gb": 5.2},
        ],
    },
]


def test_models_to_rows_flattens_variants():
    rows = models_to_rows(SAMPLE_MODELS)
    assert len(rows) == 2
    assert rows[0]["tag"] == "llama3.1:8b"
    assert "tools" in rows[0]["capabilities"]


def test_diff_identifiers():
    prev = {"llama3.1", "old-model"}
    curr = {"llama3.1", "qwen2.5-coder"}
    diff = diff_identifiers(prev, curr)
    assert diff["added"] == ["qwen2.5-coder"]
    assert diff["removed"] == ["old-model"]


def test_write_catalog_snapshot_mocked(tmp_path, monkeypatch):
    def fake_get_catalog(force_refresh=False):
        return {
            "models": SAMPLE_MODELS,
            "updated": True,
            "from_cache": False,
            "source": "live",
        }

    monkeypatch.setattr("ollama_advisor.snapshot.get_catalog", fake_get_catalog)

    result = write_catalog_snapshot(
        output_dir=tmp_path,
        force_refresh=True,
        date="2026-08-12",
    )

    assert result["model_count"] == 2
    assert result["variant_count"] == 2
    assert (tmp_path / "models.csv").exists()
    assert (tmp_path / "models.json").exists()
    assert (tmp_path / "history" / "2026-08-12.csv").exists()
    assert (tmp_path / "latest_diff.json").exists()

    # Second run with one model removed → removed in diff
    smaller = [SAMPLE_MODELS[0]]

    def fake_get_catalog2(force_refresh=False):
        return {
            "models": smaller,
            "updated": True,
            "from_cache": False,
            "source": "live",
        }

    monkeypatch.setattr("ollama_advisor.snapshot.get_catalog", fake_get_catalog2)
    result2 = write_catalog_snapshot(
        output_dir=tmp_path,
        force_refresh=True,
        date="2026-08-13",
    )
    assert result2["diff"]["removed"] == ["qwen2.5-coder"]
    assert result2["diff"]["added"] == []


def test_write_csv_roundtrip(tmp_path):
    path = tmp_path / "t.csv"
    rows = models_to_rows(SAMPLE_MODELS)
    write_csv(rows, path)
    text = path.read_text(encoding="utf-8")
    assert "identifier,tag,param_size" in text
    assert "llama3.1:8b" in text
