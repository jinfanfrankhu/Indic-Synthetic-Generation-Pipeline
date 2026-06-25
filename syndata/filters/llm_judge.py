"""
LLM-as-judge filter (API-backed; score-only).

A thin adapter over :func:`syndata.judge.score_item`: it scores an item with each
model in a judge ensemble and aggregates the per-judge :class:`QualityScore`s into
one ensemble score (per-axis mean by default; median is more robust to a single
rogue judge). The subjective axes only — fluency, faithfulness, bias.

This filter is deliberately **non-rejecting**: ``evaluate`` always reports
``passed=True`` and carries the ensemble overall in ``score``. We have no
defensible subjective cutoff until it is calibrated against the human gold set
(see ``docs/gold_standard_protocol.md`` — "Two kinds of filter"). The rich
per-axis ensemble score is available via :meth:`LLMJudgeFilter.score_ensemble`,
which is what ``export-gold`` and the distribution logging consume; the scalar
:meth:`evaluate` exists only so the judge composes in a :class:`FilterChain`.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..client import ChatClient
from ..data_structures import (
    QualityAxis,
    QualityFilter,
    QualityFilterResult,
    QualityScore,
    SeedItem,
    SyntheticItem,
)
from ..judge import JUDGE_AXES, score_item


def aggregate_scores(scores: list[QualityScore], method: str = "mean") -> QualityScore:
    """Combine per-judge scores into one ensemble :class:`QualityScore`.

    Per-axis aggregation is the mean (default) or median across judges; overall is
    the mean of the aggregated axes, matching ``score_item``'s convention. Raises
    ``ValueError`` on an empty list.
    """
    if not scores:
        raise ValueError("cannot aggregate zero judge scores")
    combine = statistics.median if method == "median" else statistics.mean

    axes = {
        axis: combine([s.scores[axis] for s in scores if axis in s.scores])
        for axis in JUDGE_AXES
    }
    overall = statistics.mean(axes.values())
    judges = ",".join(sorted({s.judge_model for s in scores}))
    return QualityScore(
        item_id=scores[0].item_id,
        scores=axes,
        judge_model=f"ensemble[{method}]:{judges}",
        judge_rationale=f"{len(scores)} judge(s)",
        overall=overall,
        timestamp=datetime.now(timezone.utc),
    )


@dataclass
class EnsembleJudgement:
    """Ensemble score for one item plus the per-judge detail and any judge errors."""

    ensemble: QualityScore
    per_judge: list[QualityScore] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LLMJudgeFilter(QualityFilter):
    name = "llm_judge"

    def __init__(
        self,
        judges: list[str],
        seed_lookup: dict[str, SeedItem],
        *,
        clients: dict[str, ChatClient] | None = None,
        aggregate: str = "mean",
        max_tokens: int = 1024,
    ) -> None:
        if not judges:
            raise ValueError("LLMJudgeFilter needs at least one judge model")
        self.judges = judges
        self.seed_lookup = seed_lookup
        self.aggregate = aggregate
        self.max_tokens = max_tokens
        # Build one client per judge (lazy import of build_client keeps the package
        # usable without `openai`). Clients are reused so the shared rate limiter
        # paces all judge calls under the account cap.
        if clients is None:
            from ..client import build_client

            clients = {j: build_client(j) for j in judges}
        self.clients = clients

    def score_ensemble(self, item: SyntheticItem) -> EnsembleJudgement:
        """Score ``item`` with every judge and aggregate. Skips judges that error.

        Raises ``ValueError`` if the seed is unknown or every judge fails.
        """
        seed = self.seed_lookup.get(item.seed_id)
        if seed is None:
            raise ValueError(f"no seed {item.seed_id!r} for item {item.id!r}")

        per_judge: list[QualityScore] = []
        errors: list[str] = []
        for judge in self.judges:
            try:
                per_judge.append(
                    score_item(item, seed, judge, self.clients[judge], self.max_tokens)
                )
            except Exception as err:  # noqa: BLE001 — isolate one judge's failure
                errors.append(f"{judge}: {err}")

        if not per_judge:
            raise ValueError(f"all judges failed for {item.id}: {'; '.join(errors)}")
        return EnsembleJudgement(
            ensemble=aggregate_scores(per_judge, self.aggregate),
            per_judge=per_judge,
            errors=errors,
        )

    def evaluate(self, item: SyntheticItem) -> QualityFilterResult:
        """Scalar, non-rejecting verdict for :class:`FilterChain` composition.

        Always ``passed=True`` — the judge never drops in score-only mode. On total
        judge failure we still pass (score 0.0) with a reason, so a flaky API can't
        silently discard items via the chain.
        """
        try:
            judgement = self.score_ensemble(item)
        except ValueError as err:
            return QualityFilterResult(
                item_id=item.id, filter_name=self.name, passed=True, score=0.0,
                reason=f"judge unavailable: {err}",
                timestamp=datetime.now(timezone.utc),
            )
        e = judgement.ensemble
        summary = ", ".join(f"{a.value} {e.scores[a]:.2f}" for a in JUDGE_AXES)
        return QualityFilterResult(
            item_id=item.id, filter_name=self.name, passed=True, score=e.overall,
            reason=f"score-only ({summary}); not enforced",
            timestamp=datetime.now(timezone.utc),
        )
