"""
LLM-as-judge scoring + a judge-panel validation harness.

The judge scores only the *subjective* axes — fluency, faithfulness, bias —
where multiple decorrelated models genuinely help (per the UPDESH / LLM-as-judge
findings). Structural/format axes (label-in-set, length, valid JSON) are handled
by code in the planned ``StructuralFilter``, not here.

Each judge is asked to reason briefly *before* scoring (explanation-generating
prompts measurably improve cross-lingual judge consistency) and to return a
strict JSON object. ``run_judge_panel`` runs several judges over several items
concurrently so their scores can be compared side by side — the judge analogue
of the teacher bake-off.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from .client import ChatClient
from .data_structures import QualityAxis, QualityScore, SeedItem, SyntheticItem
from .parsing import extract_json_object
from .templates import language_name

# Subjective axes the LLM ensemble judges. Keyed by the JSON field we ask for.
JUDGE_AXES: tuple[QualityAxis, ...] = (
    QualityAxis.FLUENCY,
    QualityAxis.FAITHFULNESS,
    QualityAxis.BIAS,
)

_AXIS_GUIDANCE = {
    QualityAxis.FLUENCY: "natural, grammatical {lang} a native speaker would write (1.0 = native quality, 0.0 = broken or not {lang} at all)",
    QualityAxis.FAITHFULNESS: "preserves the English seed's meaning, intent, and difficulty (1.0 = fully faithful, 0.0 = unrelated or distorted)",
    QualityAxis.BIAS: "free of unwanted English-centric cultural assumptions; appropriately localized (1.0 = neutral/localized, 0.0 = jarringly foreign)",
}


def build_judge_prompt(item: SyntheticItem, seed: SeedItem, lang: str) -> tuple[str, str]:
    """(system, user) asking a judge to reason then score the subjective axes."""
    system = (
        f"You are a strict, calibrated native-{lang} evaluator of machine-"
        f"generated instruction-tuning data. You judge how well a generated "
        f"{lang} task renders an English seed task. Be critical: most machine "
        "output has flaws, so do NOT default to high scores. Reserve 0.9+ for "
        "output a native speaker would consider flawless; use 0.5 for "
        "understandable-but-flawed; use 0.0 for broken output. "
        f"HARD RULE: if the generated text is not actually written in {lang} "
        "(e.g. it is left in English), fluency MUST be 0.0 regardless of "
        "meaning. Reason briefly, then score. Output only the requested JSON — "
        "no markdown, no extra commentary."
    )
    axis_lines = "\n".join(
        f"- {axis.value}: {desc.format(lang=lang)}"
        for axis, desc in _AXIS_GUIDANCE.items()
    )
    json_fields = ", ".join(f'"{axis.value}": <0.0-1.0>' for axis in JUDGE_AXES)
    parts = [
        f"English seed task:\n{seed.prompt}",
    ]
    if seed.expected:
        parts.append(f"\nReference answer (English): {seed.expected}")
    parts.append(f"\nGenerated {lang} task:\n{item.prompt}")
    if item.expected:
        parts.append(f"\nGenerated answer: {item.expected}")
    parts.append(
        f"\nScore each axis from 0.0 to 1.0:\n{axis_lines}\n\n"
        f'Return JSON only: {{"reasoning": "<one or two sentences>", {json_fields}}}'
    )
    return system, "\n".join(parts)


def _clamp(x: object) -> float:
    try:
        return max(0.0, min(1.0, float(x)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def score_item(
    item: SyntheticItem,
    seed: SeedItem,
    judge_model: str,
    client: ChatClient,
    max_tokens: int = 1024,
) -> QualityScore:
    """Score one item with one judge. Raises ``ValueError`` on unparseable output."""
    lang = language_name(item.target_language)
    system, user = build_judge_prompt(item, seed, lang)
    raw = client.complete(
        model=judge_model,
        system=system,
        user=user,
        temperature=0.0,  # deterministic judging
        max_tokens=max_tokens,
    )
    obj = extract_json_object(raw)
    if obj is None:
        raise ValueError(f"judge returned no parseable JSON: {raw[:120]!r}")

    scores = {axis: _clamp(obj.get(axis.value)) for axis in JUDGE_AXES}
    overall = sum(scores.values()) / len(scores)
    return QualityScore(
        item_id=item.id,
        scores=scores,
        judge_model=judge_model,
        judge_rationale=(str(obj.get("reasoning")) if obj.get("reasoning") else None),
        overall=overall,
        timestamp=datetime.now(timezone.utc),
    )


@dataclass
class JudgeTarget:
    """One thing to be judged: a (possibly synthetic) item plus its source seed."""
    id: str
    label: str               # e.g. "real" or "CONTROL: English text"
    seed: SeedItem
    item: SyntheticItem


@dataclass
class JudgeCell:
    score: QualityScore | None
    error: str | None


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, file=sys.stderr, flush=True)


def run_judge_panel(
    targets: list[JudgeTarget],
    judges: list[str],
    *,
    max_tokens: int = 512,
    request_timeout: float | None = None,
    max_workers: int = 6,
    calls_per_minute: float | None = None,
    verbose: bool = True,
) -> dict[str, dict[str, JudgeCell]]:
    """Score every target with every judge concurrently. Returns {target_id: {judge: cell}}."""
    from .client import build_client

    client_kwargs: dict[str, object] = {}
    if request_timeout is not None:
        client_kwargs["timeout"] = request_timeout
    if calls_per_minute is not None:
        # Pace each judge's calls (needed for low-RPM providers like Gemini).
        client_kwargs["calls_per_minute"] = calls_per_minute
    clients: dict[str, ChatClient] = {}
    build_errors: dict[str, str] = {}
    for judge in judges:
        try:
            clients[judge] = build_client(judge, **client_kwargs)
            _log(f"[judge] ready: {judge}", verbose)
        except Exception as err:  # noqa: BLE001
            build_errors[judge] = f"client init failed: {err}"
            _log(f"[judge] FAILED: {judge} -> {err}", verbose)

    results: dict[str, dict[str, JudgeCell]] = {t.id: {} for t in targets}
    work: list[tuple[JudgeTarget, str]] = []
    for t in targets:
        for judge in judges:
            if judge in build_errors:
                results[t.id][judge] = JudgeCell(None, build_errors[judge])
            else:
                work.append((t, judge))
    if not work:
        return results

    total, done = len(work), 0
    workers = max(1, min(max_workers, total))
    _log(f"dispatching {total} judge calls across {workers} workers...", verbose)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(score_item, t.item, t.seed, judge, clients[judge], max_tokens): (t.id, judge)
            for (t, judge) in work
        }
        for fut in as_completed(futures):
            tid, judge = futures[fut]
            done += 1
            try:
                score = fut.result()
                results[tid][judge] = JudgeCell(score, None)
                _log(f"[{done}/{total}] ✓ {judge} on {tid} — overall {score.overall:.2f}", verbose)
            except Exception as err:  # noqa: BLE001
                results[tid][judge] = JudgeCell(None, str(err))
                _log(f"[{done}/{total}] ✗ {judge} on {tid} — {err}", verbose)
    return results


def render_markdown(targets: list[JudgeTarget], judges: list[str],
                    results: dict[str, dict[str, JudgeCell]]) -> str:
    """Side-by-side judge scores per item, with an inter-judge spread per axis."""
    lines = [
        "# Judge-panel validation",
        "",
        f"Judges: {', '.join(f'`{j}`' for j in judges)}",
        "",
        "Spread = max−min across judges (lower = more agreement). The CONTROL rows "
        "feed judges raw English as if it were the generation; fluency there should "
        "be **low** — a judge that scores it high is not discriminating.",
        "",
    ]
    for t in targets:
        lines.append(f"## {t.id} — _{t.label}_")
        lines.append("")
        lines.append(f"**Seed:** {t.seed.prompt}")
        lines.append(f"**Judged text:** {t.item.prompt}")
        lines.append("")
        # Header row.
        lines.append("| Judge | " + " | ".join(a.value for a in JUDGE_AXES) + " | overall |")
        lines.append("|" + "---|" * (len(JUDGE_AXES) + 2))
        per_axis: dict[QualityAxis, list[float]] = {a: [] for a in JUDGE_AXES}
        for judge in judges:
            cell = results[t.id][judge]
            if cell.error:
                lines.append(f"| `{judge}` | ⚠️ {cell.error} |" + " |" * len(JUDGE_AXES))
                continue
            s = cell.score
            for a in JUDGE_AXES:
                per_axis[a].append(s.scores[a])
            row = " | ".join(f"{s.scores[a]:.2f}" for a in JUDGE_AXES)
            lines.append(f"| `{judge}` | {row} | **{s.overall:.2f}** |")
        # Spread row.
        spread = " | ".join(
            f"{(max(v) - min(v)):.2f}" if len(v) > 1 else "—" for v in per_axis.values()
        )
        lines.append(f"| _spread_ | {spread} | |")
        lines.append("")
        # Rationales.
        for judge in judges:
            cell = results[t.id][judge]
            if cell.score and cell.score.judge_rationale:
                lines.append(f"- `{judge}`: {cell.score.judge_rationale}")
        lines.append("")
    return "\n".join(lines)
