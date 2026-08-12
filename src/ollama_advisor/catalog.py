"""Ollama library catalog crawling, parsing, and caching."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

from bs4 import BeautifulSoup

from .purpose import classify_purposes

LIBRARY_URL = "https://ollama.com/library"
CACHE_PATH = Path.home() / ".ollama_advisor_cache.json"
CACHE_TTL_SECONDS = 6 * 60 * 60
USER_AGENT = "ollama-advisor/0.1.3 (+https://github.com/dschloe/ollama-advisor)"

# ollama.com/library serves meta-robots: index, follow — crawling is permitted.
# See https://ollama.com/robots.txt (Disallow only applies to /search paths).

CAPABILITY_LABELS = frozenset(
    {"tools", "vision", "thinking", "embedding", "audio", "cloud"}
)
PARAM_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?x\d+(?:\.\d+)?b|\d+(?:\.\d+)?b)\b", re.I)
PULLS_PATTERN = re.compile(r"([\d.]+[KMB]?)\s+Pulls", re.I)


def _estimate_memory_gb(param_label: str) -> float:
    """Estimate required memory from parameter size label (4-bit quantized approx)."""
    label = param_label.lower().strip()
    moe = re.match(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)b", label)
    if moe:
        billions = float(moe.group(1)) * float(moe.group(2))
    else:
        m = re.match(r"(\d+(?:\.\d+)?)b", label)
        if not m:
            return 999.0
        billions = float(m.group(1))
    return round(billions * 0.6 + 1.0, 2)


def _parse_pulls_count(text: str) -> str:
    match = PULLS_PATTERN.search(text)
    return match.group(1) if match else ""


def _parse_card_text(text: str) -> dict[str, Any]:
    """
    Parse a single model card's visible text into structured fields.

    Example input:
    "llama3.1 Llama 3.1 is a new state-of-the-art model ... tools 8b 70b 405b 118.4M Pulls"
    """
    cleaned = " ".join(text.split())
    if not cleaned:
        return {
            "identifier": "",
            "description": "",
            "capabilities": [],
            "param_sizes": [],
            "pulls": "",
            "variants": [],
        }

    parts = cleaned.split(None, 1)
    identifier = parts[0] if parts else ""
    remainder = parts[1] if len(parts) > 1 else ""

    pulls = _parse_pulls_count(remainder)
    before_pulls = PULLS_PATTERN.split(remainder, maxsplit=1)[0].strip()

    tokens = before_pulls.split()

    # Trailing layout: ... [capabilities] [param_sizes]
    # Parse from the right so "8B, 70B" inside the description is not treated as tags.
    param_sizes: list[str] = []
    idx = len(tokens) - 1
    while idx >= 0 and PARAM_PATTERN.fullmatch(tokens[idx].lower()):
        param_sizes.insert(0, tokens[idx].lower())
        idx -= 1

    capabilities: list[str] = []
    while idx >= 0 and tokens[idx].lower() in CAPABILITY_LABELS:
        capabilities.insert(0, tokens[idx].lower())
        idx -= 1

    description = " ".join(tokens[: idx + 1]).strip()
    variants = [
        {
            "tag": f"{identifier}:{size}",
            "param_size": size,
            "required_gb": _estimate_memory_gb(size),
        }
        for size in param_sizes
    ]

    return {
        "identifier": identifier,
        "description": description,
        "capabilities": capabilities,
        "param_sizes": param_sizes,
        "pulls": pulls,
        "variants": variants,
    }


def _enrich_model(raw: dict[str, Any]) -> dict[str, Any]:
    purposes = classify_purposes(
        raw.get("identifier", ""),
        raw.get("description", ""),
        raw.get("capabilities", []),
    )
    enriched = dict(raw)
    enriched["purposes"] = sorted(purposes)
    return enriched


def _fallback_catalog() -> list[dict[str, Any]]:
    """Minimal built-in catalog when live crawl fails."""
    seeds = [
        {
            "identifier": "llama3.2",
            "description": "Meta Llama 3.2 general-purpose models",
            "capabilities": ["tools"],
            "param_sizes": ["1b", "3b"],
            "pulls": "0",
        },
        {
            "identifier": "qwen2.5-coder",
            "description": "Qwen2.5 Coder for code generation",
            "capabilities": ["tools"],
            "param_sizes": ["1.5b", "7b"],
            "pulls": "0",
        },
        {
            "identifier": "deepseek-r1",
            "description": "DeepSeek reasoning model with thinking capability",
            "capabilities": ["thinking"],
            "param_sizes": ["7b", "14b"],
            "pulls": "0",
        },
        {
            "identifier": "llava",
            "description": "Vision-language model",
            "capabilities": ["vision"],
            "param_sizes": ["7b", "13b"],
            "pulls": "0",
        },
        {
            "identifier": "nomic-embed-text",
            "description": "Text embedding model",
            "capabilities": ["embedding"],
            "param_sizes": ["latest"],
            "pulls": "0",
        },
        {
            "identifier": "whisper",
            "description": "Speech recognition model",
            "capabilities": ["audio"],
            "param_sizes": ["base", "small"],
            "pulls": "0",
        },
        {
            "identifier": "mistral",
            "description": "Mistral general-purpose models",
            "capabilities": ["tools"],
            "param_sizes": ["7b"],
            "pulls": "0",
        },
        {
            "identifier": "gemma2",
            "description": "Google Gemma 2 general models",
            "capabilities": [],
            "param_sizes": ["2b", "9b"],
            "pulls": "0",
        },
    ]
    models = []
    for seed in seeds:
        parsed = _parse_card_text(
            f"{seed['identifier']} {seed['description']} "
            f"{' '.join(seed['capabilities'])} "
            f"{' '.join(seed['param_sizes'])} {seed['pulls']} Pulls"
        )
        for size in seed["param_sizes"]:
            if size in {"latest", "base", "small"}:
                parsed.setdefault("variants", []).append(
                    {
                        "tag": f"{seed['identifier']}:{size}",
                        "param_size": size,
                        "required_gb": 2.0 if size != "small" else 1.5,
                    }
                )
        models.append(_enrich_model(parsed))
    return models


def _identifiers_hash(models: list[dict[str, Any]]) -> str:
    ids = sorted({m.get("identifier", "") for m in models})
    payload = json.dumps(ids, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _fetch_library_html() -> str:
    req = urllib_request.Request(
        LIBRARY_URL,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib_request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_library_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        match = re.fullmatch(r"/library/([^/:]+)", href)
        if not match:
            continue
        identifier = match.group(1)
        if identifier in seen:
            continue
        seen.add(identifier)
        text = anchor.get_text(" ", strip=True)
        if not text:
            parent = anchor.find_parent(["li", "article", "div"])
            text = parent.get_text(" ", strip=True) if parent else identifier
        parsed = _parse_card_text(text if text else identifier)
        if not parsed["identifier"]:
            parsed["identifier"] = identifier
        if not parsed["variants"]:
            parsed["variants"] = [
                {
                    "tag": identifier,
                    "param_size": "default",
                    "required_gb": 4.0,
                }
            ]
        models.append(_enrich_model(parsed))

    return models


def _load_cache() -> dict[str, Any] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(models: list[dict[str, Any]]) -> None:
    payload = {
        "fetched_at": time.time(),
        "identifiers_hash": _identifiers_hash(models),
        "models": models,
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_catalog(force_refresh: bool = False) -> dict[str, Any]:
    """
    Return the model catalog, using cache when fresh.

    Returns
    -------
    dict
        keys: models (list), updated (bool), from_cache (bool), source (str)
    """
    cached = _load_cache()
    now = time.time()
    updated = False

    if (
        not force_refresh
        and cached
        and cached.get("models")
        and (now - cached.get("fetched_at", 0)) < CACHE_TTL_SECONDS
    ):
        return {
            "models": cached["models"],
            "updated": False,
            "from_cache": True,
            "source": "cache",
        }

    try:
        html = _fetch_library_html()
        live_models = _parse_library_html(html)
        if not live_models:
            raise ValueError("No models parsed from library page")
        live_hash = _identifiers_hash(live_models)
        old_hash = cached.get("identifiers_hash") if cached else None
        updated = live_hash != old_hash
        _save_cache(live_models)
        return {
            "models": live_models,
            "updated": updated,
            "from_cache": False,
            "source": "live",
        }
    except Exception:
        if cached and cached.get("models"):
            return {
                "models": cached["models"],
                "updated": False,
                "from_cache": True,
                "source": "cache_stale",
            }
        fallback = _fallback_catalog()
        return {
            "models": fallback,
            "updated": False,
            "from_cache": False,
            "source": "fallback",
        }


def expand_runnable_rows(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten model catalog into one row per runnable variant tag."""
    rows: list[dict[str, Any]] = []
    for model in models:
        purposes = sorted(
            classify_purposes(
                model.get("identifier", ""),
                model.get("description", ""),
                model.get("capabilities", []),
            )
        )
        variants = model.get("variants") or [
            {
                "tag": model.get("identifier", ""),
                "param_size": "default",
                "required_gb": 4.0,
            }
        ]
        for variant in variants:
            rows.append(
                {
                    "identifier": model.get("identifier", ""),
                    "tag": variant.get("tag", ""),
                    "description": model.get("description", ""),
                    "param_size": variant.get("param_size", ""),
                    "required_gb": variant.get("required_gb", 999.0),
                    "capabilities": model.get("capabilities", []),
                    "purposes": purposes,
                    "pulls": model.get("pulls", ""),
                }
            )
    return rows
