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
    # Per-family requirements. These are deliberately explicit: the 2026-07-13
    # full-corpus review traced most defects back to seed quality (bootstrapped
    # seeds 5.2% defect vs. 0.8% for hand-curated), and a bad seed propagates into
    # all four target languages. See docs/error_taxonomy.md.
    schema_hint = {
        TaskFamily.QA: (
            'each needs a factual question in "prompt" and its short, unambiguous '
            'answer in "expected". VERIFY every answer is correct before writing it. '
            'Prefer stable facts (science, geography, well-established history) over '
            'anything time-varying or disputed. Keep answers short (a word, name, '
            'number, or year) - not sentences.'
        ),
        TaskFamily.REASONING: (
            'each needs a multi-step problem in "prompt" (ending with an instruction '
            'to show the reasoning step by step) and the correct final answer in '
            '"expected". SOLVE each problem yourself and double-check the answer - a '
            'wrong "expected" corrupts every language it is translated into.'
        ),
        TaskFamily.CLASSIFICATION: (
            'each needs the text to classify in "prompt", a "labels" array of >=2 '
            'candidate labels, and the correct one in "expected". TWO HARD RULES: '
            '(1) "expected" MUST be exactly one of the strings in "labels"; '
            '(2) the "prompt" MUST list the candidate labels inline so the model can '
            'see its choices (e.g. "... Classify the sentiment. Options: positive, '
            'neutral, negative."). A prompt without a visible option list is invalid. '
            'Avoid sarcasm/irony - it makes the label ambiguous after translation.'
        ),
        TaskFamily.SUMMARIZATION: (
            'each needs a self-contained factual passage of 3-5 sentences to summarize '
            'in "prompt" and a faithful ONE-sentence reference summary in "expected" '
            'that introduces no new facts.'
        ),
        TaskFamily.TRANSLATION: (
            'each needs a short, natural English sentence to translate in "prompt"; '
            'leave "expected" as null. Vary register and everyday domain (greeting, '
            'travel, health, market, work, directions).'
        ),
        TaskFamily.INSTRUCTION: (
            'each needs a self-contained, open-ended instruction in "prompt"; leave '
            '"expected" as null. Vary the type (explain, write, list, how-to).'
        ),
    }.get(task, 'fill "prompt" and "expected" as appropriate.')

    system = (
        "You generate seed tasks for an instruction-tuning dataset. Produce NEW, "
        "diverse English tasks — vary the topic, domain, and difficulty; do not "
        "repeat or lightly reword the examples. Write everything in ENGLISH only.\n"
        f"For the '{task.value}' task family, {schema_hint}\n"
        "TRANSLATABILITY (these seeds are translated into Hindi, Urdu, Tamil, and "
        "Malayalam): avoid idioms, puns, wordplay, and English-culture trivia that "
        "will not survive translation. Prefer universal content, and include some "
        "India/South-Asia-relevant material where it fits naturally.\n"
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
        # The answer must actually be one of the offered classes. Without this a
        # seed can carry an "expected" no classifier could ever produce.
        if expected not in {str(x) for x in labels}:
            result._bump("expected_not_in_labels")
            return None
        # The prompt must show the model its choices. Bootstrapped classification
        # seeds that hid the options in metadata were the single biggest
        # format-failure bucket in the 2026-07-13 review: the model had nothing to
        # choose from. Require at least two labels to appear in the prompt text.
        low = prompt.lower()
        if sum(1 for x in labels if str(x).lower() in low) < 2:
            result._bump("options_not_in_prompt")
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
    taken_ids: set[str] | None = None,
) -> BootstrapResult:
    """Generate ``n`` new, de-duplicated English seeds for ``task``.

    Loops teacher calls (``per_call`` seeds each) until ``n`` survive the
    pre-filters or the attempt budget runs out. Dedup is against both the
    ``examples`` and seeds already accepted in this run.

    ``taken_ids`` are seed ids already in use (e.g. from a previous bootstrap
    run). Ids are allocated past them, so re-running never reuses an id — a
    collision would otherwise propagate into generated item ids, which embed the
    seed id.
    """
    result = BootstrapResult(task=task, seeds=[], requested=n)
    system, user = _build_messages(task, examples, per_call)
    seen = {_normalize(s.prompt) for s in examples}
    taken = set(taken_ids or ()) | {s.id for s in examples}
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
            counter = len(result.seeds) + 1
            while f"seed-{task.value}-bs-{counter:04d}" in taken:
                counter += 1
            seed.id = f"seed-{task.value}-bs-{counter:04d}"
            taken.add(seed.id)
            seed.metadata = {**seed.metadata, "source": f"bootstrap:{model}"}
            result.seeds.append(seed)

        if verbose:
            print(
                f"  [{task.value}] attempt {attempts}/{max_attempts}: "
                f"{len(result.seeds)}/{n} accepted",
                file=sys.stderr,
            )

    return result
