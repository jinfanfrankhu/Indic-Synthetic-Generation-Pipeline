"""
Robust JSON extraction from LLM responses.

Shared by the generator and the judge: models wrap JSON in markdown fences,
prepend commentary, or (reasoning models) emit a <think>...</think> chain of
thought whose braces defeat naive extraction. This recovers the intended object
or returns ``None`` so the caller can fall back.
"""
from __future__ import annotations

import json
import re

# First "{...}" block across newlines — applied only after reasoning/fences are
# stripped, so its greediness no longer matches across stray braces.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(raw: str) -> dict | None:
    """Best-effort parse of the JSON object in ``raw``; ``None`` if unrecoverable."""
    if not raw:
        return None
    text = raw.strip()

    # Reasoning models prepend <think>...</think> (with braces inside it) before
    # the answer; keep only what follows the final closing tag.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()

    # Strip a markdown code fence and any leading "json" language tag.
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()

    candidate = text if text.startswith("{") else None
    if candidate is None:
        match = _JSON_BLOCK.search(text)
        candidate = match.group(0) if match else None
    if not candidate:
        return None

    try:
        obj = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None
