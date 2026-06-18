"""
Generator.

Given a :class:`SeedItem` and a :class:`GenerationConfig`, build the teacher
prompt (via :mod:`syndata.templates`), call a :class:`ChatClient`, parse the
response, and stamp full provenance into a :class:`SyntheticItem`.

Parsing is defensive: the templates ask for strict JSON, but ``parse_response``
salvages fenced or preamble-wrapped output and, failing that, falls back to
treating the whole response as the prompt. The raw response is always preserved
on ``SyntheticItem.raw_response`` for audit, so nothing is ever lost.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .client import ChatClient
from .data_structures import GenerationConfig, SeedItem, SyntheticItem
from .templates import get_template, language_name

# Matches the first {...} block, across newlines — used to salvage JSON that the
# model wrapped in fences or surrounded with commentary.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_response(raw: str) -> tuple[str, str | None]:
    """Extract ``(prompt, expected)`` from a teacher response.

    Returns ``expected=None`` when the model emitted no answer (empty string or
    missing key). On unrecoverable output, returns the stripped raw text as the
    prompt so the item is still usable and auditable.
    """
    text = raw.strip()
    # Reasoning models (e.g. sarvam-m) prepend a <think>...</think> chain of
    # thought — which itself contains braces — before the answer JSON. Keep only
    # what follows the final closing tag (handles an orphaned </think> too).
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    # Strip markdown code fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        # Drop a leading "json" language tag left by the fence.
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()

    candidate = text
    if not candidate.startswith("{"):
        match = _JSON_BLOCK.search(text)
        if match:
            candidate = match.group(0)

    try:
        obj = json.loads(candidate)
        prompt = str(obj.get("prompt", "")).strip()
        expected_raw = obj.get("expected", "")
        expected = str(expected_raw).strip() if expected_raw not in (None, "") else None
        if prompt:
            return prompt, expected
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    # Unrecoverable — keep the raw text as the prompt rather than dropping it.
    return raw.strip(), None


def make_synthetic_id(seed: SeedItem, target_language: str) -> str:
    """Stable-ish id, e.g. ``syn-hi-qa-002`` from ``seed-qa-002``."""
    suffix = seed.id.replace("seed-", "", 1)
    return f"syn-{target_language}-{suffix}"


def generate(
    seed: SeedItem,
    config: GenerationConfig,
    client: ChatClient,
) -> SyntheticItem:
    """Generate one :class:`SyntheticItem` from a seed using the teacher client."""
    lang = language_name(config.target_language)
    builder = get_template(config.prompt_template_name)
    system, user = builder(seed, lang)

    raw = client.complete(
        model=config.teacher_model,
        system=system,
        user=user,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    prompt, expected = parse_response(raw)

    return SyntheticItem(
        id=make_synthetic_id(seed, config.target_language),
        seed_id=seed.id,
        task_family=seed.task_family,
        target_language=config.target_language,
        prompt=prompt,
        expected=expected,
        metadata={**seed.metadata, "template": config.prompt_template_name},
        generation=config,
        generated_at=datetime.now(timezone.utc),
        raw_response=raw,
    )
