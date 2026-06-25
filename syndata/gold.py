"""
Gold-standard bundle assembler.

Turns a *judged* pool of synthetic items into the two files the rating workflow
needs (see ``docs/gold_standard_protocol.md``):

  - ``rater_bundle.json``        — blind; what the rating app serves. No scores,
                                   no model names, no stratum.
  - ``assignment_manifest.json`` — private; the answer key + rater assignments.
                                   Judge scores, teacher model, stratum, overlap.

Splitting the two is what keeps the bundle blind: nothing that could anchor a
rater ever reaches the app. Selection is stratified — most items are a random
"normal" sample; the rest are "borderline", chosen nearest the judge's per-
language overall-score median, to force coverage of the decision boundary where
agreement matters most.

This module is pure and offline: it consumes scores produced by a prior
``judge-score`` pass, so the expensive API work is re-runnable and the assembler
itself is deterministic given its random seed.
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from .data_structures import QualityScore, SeedItem, SyntheticItem


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_items(paths: list[Path]) -> list[SyntheticItem]:
    """Load and de-duplicate :class:`SyntheticItem`s from JSONL files (last wins)."""
    by_id: dict[str, SyntheticItem] = {}
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    item = SyntheticItem.model_validate_json(line)
                    by_id[item.id] = item
    return list(by_id.values())


def load_scores(path: Path) -> dict[str, QualityScore]:
    """Load ensemble :class:`QualityScore`s (one per line) keyed by ``item_id``."""
    scores: dict[str, QualityScore] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                qs = QualityScore.model_validate_json(line)
                scores[qs.item_id] = qs
    return scores


# ---------------------------------------------------------------------------
# Stratified selection
# ---------------------------------------------------------------------------

def select_gold_set(
    items: list[SyntheticItem],
    scores: dict[str, QualityScore],
    *,
    per_language: int = 80,
    normal_frac: float = 0.6,
    rng: random.Random | None = None,
) -> dict[str, list[tuple[SyntheticItem, str]]]:
    """Pick a stratified gold set per language.

    Only items with a judge score are eligible (borderline selection needs the
    overall score, and the manifest records judge scores for every item). Within a
    language: ``borderline`` = the items whose overall score is closest to that
    language's median; ``normal`` = a random sample of the rest. Returns
    ``{language: [(item, stratum), ...]}``. If a language has fewer scored items
    than requested, strata scale down proportionally.
    """
    rng = rng or random.Random(0)

    by_lang: dict[str, list[SyntheticItem]] = {}
    for item in items:
        if item.id in scores:
            by_lang.setdefault(item.target_language, []).append(item)

    selected: dict[str, list[tuple[SyntheticItem, str]]] = {}
    for lang, pool in by_lang.items():
        take = min(per_language, len(pool))
        n_normal = round(take * normal_frac)
        n_border = take - n_normal

        median = _median([scores[i.id].overall for i in pool])
        # Borderline = closest to the median (ties broken deterministically by id).
        by_distance = sorted(pool, key=lambda i: (abs(scores[i.id].overall - median), i.id))
        border = by_distance[:n_border]
        border_ids = {i.id for i in border}

        rest = [i for i in pool if i.id not in border_ids]
        rng.shuffle(rest)
        normal = rest[:n_normal]

        chosen = [(i, "borderline") for i in border] + [(i, "normal") for i in normal]
        rng.shuffle(chosen)
        selected[lang] = chosen
    return selected


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


# ---------------------------------------------------------------------------
# Bundle (blind) + manifest (private)
# ---------------------------------------------------------------------------

def build_bundle(
    selected: dict[str, list[tuple[SyntheticItem, str]]],
    seeds_by_id: dict[str, SeedItem],
    *,
    bundle_id: str,
    instructions_version: str = "v1",
) -> dict:
    """Assemble the blind rater bundle. Carries the English seed (for the
    source-needing axes) and the generated text — but no scores, model, or stratum.
    """
    items_out = []
    for lang in sorted(selected):
        for item, _stratum in selected[lang]:
            seed = seeds_by_id.get(item.seed_id)
            items_out.append({
                "task_id": item.id,
                "language": item.target_language,
                "task_family": item.task_family.value,
                "source_prompt": seed.prompt if seed else None,
                "source_expected": seed.expected if seed else None,
                "generated_prompt": item.prompt,
                "generated_expected": item.expected,
                "show_source": True,
            })
    return {
        "bundle_id": bundle_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instructions_version": instructions_version,
        "rating_schema": {
            "axes": [
                {"key": "fluency", "label": "Naturalness", "scale": [1, 4], "needs_source": False},
                {"key": "faithfulness", "label": "Meaning match", "scale": [1, 4], "needs_source": True},
                {"key": "bias", "label": "Cultural fit", "scale": [1, 4], "needs_source": True},
            ],
            "optional": ["unsure", "comment"],
        },
        "items": items_out,
    }


def _ensemble_judges(judge_model: str) -> list[str]:
    """Recover the judge list from an aggregate label like ``ensemble[mean]:A,B``."""
    if ":" in judge_model:
        return [j for j in judge_model.split(":", 1)[1].split(",") if j]
    return [judge_model]


def build_manifest(
    selected: dict[str, list[tuple[SyntheticItem, str]]],
    scores: dict[str, QualityScore],
    *,
    bundle_id: str,
    raters_per_language: int = 2,
    overlap_frac: float = 0.2,
    rng: random.Random | None = None,
) -> dict:
    """Assemble the private manifest: rater assignments + provenance/answer key.

    Rater IDs are slot placeholders (``hi_r1`` …) since native speakers are still
    being recruited; edit them in once raters exist. ~``overlap_frac`` of each
    language's items are double-rated (needs ≥2 raters) to give a human–human
    agreement ceiling.
    """
    rng = rng or random.Random(0)
    assignments = []
    provenance: dict[str, dict] = {}

    for lang in sorted(selected):
        entries = list(selected[lang])
        raters = [f"{lang}_r{k + 1}" for k in range(max(1, raters_per_language))]
        n_overlap = math.ceil(overlap_frac * len(entries)) if len(raters) >= 2 else 0
        order = list(range(len(entries)))
        rng.shuffle(order)
        overlap_idx = set(order[:n_overlap])

        for idx, (item, stratum) in enumerate(entries):
            primary = raters[idx % len(raters)]
            assigned = [primary]
            if idx in overlap_idx:
                # Add a distinct second rater for the double-rated subset.
                second = raters[(idx + 1) % len(raters)]
                if second != primary:
                    assigned.append(second)
            assignments.append({
                "task_id": item.id,
                "raters": assigned,
                "overlap": len(assigned) > 1,
                "stratum": stratum,
            })
            qs = scores[item.id]
            provenance[item.id] = {
                "teacher_model": item.generation.teacher_model,
                "judge_scores": {a.value: round(v, 4) for a, v in qs.scores.items()},
                "judge_overall": round(qs.overall, 4),
                "judge_model_ensemble": _ensemble_judges(qs.judge_model),
            }

    return {
        "bundle_id": bundle_id,
        "assignments": assignments,
        "provenance": provenance,
    }


def write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
