"""Model purpose classification."""

from __future__ import annotations

import re

PURPOSES = frozenset({"general", "reasoning", "coding", "vision", "embedding", "audio"})

REASONING_KEYWORDS = re.compile(
    r"reasoning|r1|qwq|o1|o3",
    re.IGNORECASE,
)
CODING_KEYWORDS = re.compile(
    r"\b(?:code|coder|coding|sql|devstral|starcoder|codellama|codegemma|"
    r"codestral|codeqwen|codegeex|opencoder)\b",
    re.IGNORECASE,
)


def classify_purposes(
    identifier: str,
    description: str,
    capabilities: set[str] | list[str] | None = None,
) -> set[str]:
    """
    Classify a model into one or more purpose categories.

    Categories: general, reasoning, coding, vision, embedding, audio.
    """
    caps = {c.lower() for c in (capabilities or [])}
    text = f"{identifier} {description}".lower()
    purposes: set[str] = set()

    if "embedding" in caps or "embed" in identifier.lower():
        purposes.add("embedding")
    if "vision" in caps:
        purposes.add("vision")
    if "audio" in caps:
        purposes.add("audio")
    if "thinking" in caps or REASONING_KEYWORDS.search(text):
        purposes.add("reasoning")
    if CODING_KEYWORDS.search(text):
        purposes.add("coding")

    if "embedding" not in purposes:
        purposes.add("general")

    return purposes
