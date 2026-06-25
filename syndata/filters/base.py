"""
Filter composition.

:class:`FilterChain` runs a list of filters over one item and collects every
:class:`QualityFilterResult`. It never discards: it returns all verdicts plus an
AND-composed ``would_pass`` flag so the caller can *see* what each filter thinks
before deciding whether to drop. This is the "score, don't drop" mode the Week 4
plan calls for — we collect score distributions first, then place thresholds
against the gold set.

The concrete filters subclass ``QualityFilter`` from
:mod:`syndata.data_structures`. Filters that need the source seed (the LLM judge,
back-translation) take a seed lookup at construction time; the structural and
language-ID filters need only the item itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..data_structures import QualityFilter, QualityFilterResult, SyntheticItem


@dataclass
class FilterVerdict:
    """All per-filter results for one item, plus the AND-composed verdict."""

    item_id: str
    results: list[QualityFilterResult] = field(default_factory=list)

    @property
    def would_pass(self) -> bool:
        """True iff every filter passed. In score-only mode this is advisory."""
        return all(r.passed for r in self.results)

    def failed_filters(self) -> list[str]:
        return [r.filter_name for r in self.results if not r.passed]


class FilterChain:
    """Runs an ordered list of filters over items (score-only; nothing dropped).

    Order matters for cost when API-backed filters are included: put the free
    deterministic gates (structural, language-ID) first and the API-backed ones
    (judge, back-translation) last so they only run on what survives — but in
    score-only mode every filter still runs on every item unless ``short_circuit``
    is set.
    """

    def __init__(self, filters: list[QualityFilter], *, short_circuit: bool = False) -> None:
        self.filters = filters
        self.short_circuit = short_circuit

    def evaluate(self, item: SyntheticItem) -> FilterVerdict:
        verdict = FilterVerdict(item_id=item.id)
        for f in self.filters:
            result = f.evaluate(item)
            verdict.results.append(result)
            if self.short_circuit and not result.passed:
                break
        return verdict
