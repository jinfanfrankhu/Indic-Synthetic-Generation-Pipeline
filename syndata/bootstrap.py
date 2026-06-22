"""
Seed bootstrapping (self-instruct).

The curated seed pool is tiny (a dozen-odd English tasks). To give the generator
real diversity to draw from, ``bootstrap_seeds`` few-shots the teacher with a
handful of existing seeds of one task family and asks for a batch of *new*,
distinct English seeds in the same schema.

Because bad English seeds would propagate into every target-language item built
from them, generated candidates pass a set of cheap, mechanical pre-filters here
(schema validity, near-duplicate dedup, English-only, required fields per task,
length bounds) before being written out. The surviving file is then meant for a
human skim — the final quality gate — before generation runs against it.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field

from .client import ChatClient
from .data_structures import SeedItem, TaskFamily
from .parsing import extract_json_object

# Unicode ranges for the four target scripts. A bootstrapped *English* seed
# containing any of these means the teacher drifted into a target language — a
# pre-filter reject, not something to translate later.
_TARGET_SCRIPT = re.compile(
    "["
    "ऀ-ॿ"   # Devanagari (Hindi)
    "؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿"  # Arabic/Nastaliq (Urdu)
    "஀-௿"   # Tamil
    "ഀ-ൿ"   # Malayalam
    "]"
)

# First "[...]" block across newlines, after fences/reasoning are stripped.
_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)

_MIN_PROMPT_LEN = 10
_MAX_PROMPT_LEN = 2000


@dataclass
class BootstrapResult:
    """Outcome of one task family's bootstrap run."""
    task: TaskFamily
    seeds: list[SeedItem]
    requested: int
    drops: dict[str, int] = field(default_factory=dict)

    def _bump(self, reason: str) -> None:
        self.drops[reason] = self.drops.get(reason, 0) + 1


def _strip_wrapping(raw: str) -> str:
    """Drop a <think> chain of thought and any markdown code fence."""
    text = raw.strip()
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    return text


def parse_seed_array(raw: str) -> list[dict]:
    """Best-effort extraction of a JSON array of seed dicts from ``raw``.

    Tolerates fenced / reasoning-wrapped output and a model that returned a
    single object instead of an array (wrapped into a one-element list).
    Returns ``[]`` when nothing usable is found.
    """
    text = _strip_wrapping(raw)
    candidate = text if text.startswith("[") else None
    if candidate is None:
        match = _JSON_ARRAY.search(text)
        candidate = match.group(0) if match else None
    if candidate:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            obj = None
        if isinstance(obj, list):
            return [r for r in obj if isinstance(r, dict)]
    # Fall back to a single object (e.g. MockClient, or a model that ignored the
    # "array" instruction).
    single = extract_json_object(raw)
    return [single] if single else []


def _normalize(prompt: str) -> str:
    """Key for near-duplicate detection: lowercased, whitespace-collapsed."""
    return " ".join(prompt.lower().split())


def _build_messages(
    task: TaskFamily, examples: list[SeedItem], per_call: int
) -> tuple[str, str]:
    """(system, user) asking for ``per_call`` new English seeds for ``task``."""
    schema_hint = {
        TaskFamily.QA: 'each needs a factual question in "prompt" and its short answer in "expected".',
        TaskFamily.REASONING: 'each needs a multi-step problem in "prompt" and the final answer (with brief reasoning) in "expected".',
        TaskFamily.CLASSIFICATION: 'each needs the text to classify in "prompt", a "labels" array of >=2 candidate labels, and the correct one in "expected".',
        TaskFamily.SUMMARIZATION: 'each needs a passage to summarize in "prompt" and a reference summary in "expected".',
        TaskFamily.TRANSLATION: 'each needs a short English sentence to translate in "prompt"; leave "expected" as null.',
        TaskFamily.INSTRUCTION: 'each needs an open-ended instruction in "prompt"; leave "expected" as null.',
    }.get(task, 'fill "prompt" and "expected" as appropriate.')

    system = (
        "You generate seed tasks for an instruction-tuning dataset. Produce NEW, "
        "diverse English tasks — vary the topic, domain, and difficulty; do not "
        "repeat or lightly reword the examples. Write everything in ENGLISH only.\n"
        f"For the '{task.value}' task family, {schema_hint}\n"
        "Output ONLY a JSON array of objects, no markdown fences, no commentary. "
        'Each object: {"prompt": str, "expected": str|null, "labels": [str]|null, '
        '"metadata": {"domain": str, "difficulty": str}}.'
    )

    shown = [
        {
            "prompt": s.prompt,
            "expected": s.expected,
            "labels": s.labels,
            "metadata": s.metadata,
        }
        for s in examples[:3]
    ]
    user = (
        f"Examples of existing '{task.value}' seeds:\n"
        f"{json.dumps(shown, ensure_ascii=False, indent=2)}\n\n"
        f"Now produce {per_call} new, distinct '{task.value}' seeds as a JSON array."
    )
    return system, user


def _accept(record: dict, task: TaskFamily, result: BootstrapResult) -> SeedItem | None:
    """Run the pre-filters on one raw record; return a SeedItem or None (+log drop)."""
    prompt = str(record.get("prompt", "")).strip()
    if not prompt or len(prompt) < _MIN_PROMPT_LEN or len(prompt) > _MAX_PROMPT_LEN:
        result._bump("length")
        return None
    if _TARGET_SCRIPT.search(prompt):
        result._bump("not_english")
        return None

    expected_raw = record.get("expected")
    expected = str(expected_raw).strip() if expected_raw not in (None, "") else None
    labels = record.get("labels") if isinstance(record.get("labels"), list) else None

    # Required fields per task family.
    if task in (TaskFamily.QA, TaskFamily.REASONING) and not expected:
        result._bump("missing_expected")
        return None
    if task == TaskFamily.CLASSIFICATION:
        if not labels or len(labels) < 2:
            result._bump("bad_labels")
            return None
        if not expected:
            result._bump("missing_expected")
            return None

    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    try:
        return SeedItem.model_validate(
            {
                "id": "pending",  # real id assigned by the caller after dedup
                "task_family": task.value,
                "prompt": prompt,
                "expected": expected,
                "labels": labels,
                "metadata": metadata,
            }
        )
    except Exception:  # noqa: BLE001 — schema reject is just another drop
        result._bump("invalid_schema")
        return None


def bootstrap_seeds(
    task: TaskFamily,
    n: int,
    client: ChatClient,
    model: str,
    examples: list[SeedItem],
    *,
    per_call: int = 8,
    temperature: float = 1.0,
    max_tokens: int = 1024,
    max_attempts: int | None = None,
    verbose: bool = True,
) -> BootstrapResult:
    """Generate ``n`` new, de-duplicated English seeds for ``task``.

    Loops teacher calls (``per_call`` seeds each) until ``n`` survive the
    pre-filters or the attempt budget runs out. Dedup is against both the
    ``examples`` and seeds already accepted in this run.
    """
    result = BootstrapResult(task=task, seeds=[], requested=n)
    system, user = _build_messages(task, examples, per_call)
    seen = {_normalize(s.prompt) for s in examples}
    # Generous attempt budget: enough calls to reach n even if many are dropped.
    if max_attempts is None:
        max_attempts = max(4, (n // per_call) * 3 + 4)

    attempts = 0
    while len(result.seeds) < n and attempts < max_attempts:
        attempts += 1
        try:
            raw = client.complete(
                model=model, system=system, user=user,
                temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as err:  # noqa: BLE001 — skip a failed call, keep going
            if verbose:
                print(f"  [{task.value}] call {attempts} failed: {err}", file=sys.stderr)
            continue

        records = parse_seed_array(raw)
        if not records:
            result._bump("unparseable_response")
        for record in records:
            if len(result.seeds) >= n:
                break
            seed = _accept(record, task, result)
            if seed is None:
                continue
            key = _normalize(seed.prompt)
            if key in seen:
                result._bump("duplicate")
                continue
            seen.add(key)
            seed.id = f"seed-{task.value}-bs-{len(result.seeds) + 1:04d}"
            seed.metadata = {**seed.metadata, "source": f"bootstrap:{model}"}
            result.seeds.append(seed)

        if verbose:
            print(
                f"  [{task.value}] attempt {attempts}/{max_attempts}: "
                f"{len(result.seeds)}/{n} accepted",
                file=sys.stderr,
            )

    return result
