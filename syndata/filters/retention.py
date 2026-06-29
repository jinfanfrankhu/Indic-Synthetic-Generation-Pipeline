"""
Retention reporting for the filter chain.

The Week 4 exit criterion is "per-language retention rates logged": after running
the filter chain over a batch we need to see, per language and per task family,
what fraction of items each filter passed and what fraction survived the chain.

This module is pure aggregation over :class:`~syndata.filters.base.FilterVerdict`s
— no I/O, no API — so it is unit-testable on its own. The CLI (`syndata filter`)
feeds it the items it scored and writes the rendered Markdown to ``docs/``.

Two numbers matter and are reported separately:

  - **per-filter pass rate** — of items a filter judged, the fraction it passed.
    The LLM judge is score-only (always passes), so its "pass rate" is 1.0 by
    construction; it is shown for completeness but never drives retention.
  - **chain retention** — the fraction that passed *every* enforcing filter
    (``would_pass``). This is the headline retention number.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..data_structures import SyntheticItem
from .base import FilterVerdict


@dataclass
class PassStat:
    """Passed-out-of-total for one filter (or the chain) over a group of items."""

    total: int = 0
    passed: int = 0

    @property
    def rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def add(self, passed: bool) -> None:
        self.total += 1
        self.passed += 1 if passed else 0


@dataclass
class GroupRetention:
    """Retention for one group of items (a language, or a language×task cell)."""

    n_items: int = 0
    # filter_name -> PassStat across the items in this group
    per_filter: dict[str, PassStat] = field(default_factory=lambda: defaultdict(PassStat))
    chain: PassStat = field(default_factory=PassStat)

    def add(self, verdict: FilterVerdict) -> None:
        self.n_items += 1
        for r in verdict.results:
            self.per_filter[r.filter_name].add(r.passed)
        self.chain.add(verdict.would_pass)


@dataclass
class RetentionReport:
    """Full retention summary: overall, per language, and per language×task."""

    filter_names: list[str]
    overall: GroupRetention
    by_language: dict[str, GroupRetention]
    by_language_task: dict[tuple[str, str], GroupRetention]
    generated_at: datetime


def summarize(pairs: list[tuple[SyntheticItem, FilterVerdict]]) -> RetentionReport:
    """Aggregate (item, verdict) pairs into a :class:`RetentionReport`.

    Filter column order is taken from the first verdict that has results, so the
    report columns match chain order (cheap deterministic gates first).
    """
    overall = GroupRetention()
    by_language: dict[str, GroupRetention] = defaultdict(GroupRetention)
    by_language_task: dict[tuple[str, str], GroupRetention] = defaultdict(GroupRetention)

    filter_names: list[str] = []
    for item, verdict in pairs:
        if not filter_names and verdict.results:
            filter_names = [r.filter_name for r in verdict.results]
        overall.add(verdict)
        by_language[item.target_language].add(verdict)
        by_language_task[(item.target_language, item.task_family.value)].add(verdict)

    return RetentionReport(
        filter_names=filter_names,
        overall=overall,
        by_language=dict(by_language),
        by_language_task=dict(by_language_task),
        generated_at=datetime.now(timezone.utc),
    )


def _row(label: str, group: GroupRetention, filter_names: list[str]) -> str:
    cells = [label, str(group.n_items)]
    for name in filter_names:
        stat = group.per_filter.get(name)
        cells.append(f"{stat.rate:.0%} ({stat.passed}/{stat.total})" if stat else "—")
    cells.append(f"**{group.chain.rate:.0%}** ({group.chain.passed}/{group.chain.total})")
    return "| " + " | ".join(cells) + " |"


def render_markdown(report: RetentionReport, *, title: str = "Filter Retention Report") -> str:
    """Render a :class:`RetentionReport` as a Markdown document."""
    names = report.filter_names
    header = ["Group", "N", *names, "Chain"]
    sep = ["---"] * len(header)

    lines: list[str] = [
        f"# {title}",
        "",
        f"_Generated {report.generated_at:%Y-%m-%d %H:%M UTC}_",
        "",
        "Per-filter cells are pass rates (passed/total) for that filter alone. "
        "**Chain** is the fraction passing every enforcing filter — the headline "
        "retention. The LLM judge is score-only (non-rejecting), so its column is "
        "1.0 by construction and does not affect Chain.",
        "",
        "## Overall",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
        _row("all", report.overall, names),
        "",
        "## By language",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for lang in sorted(report.by_language):
        lines.append(_row(lang, report.by_language[lang], names))
    lines += ["", "## By language × task", "",
              "| " + " | ".join(header) + " |",
              "| " + " | ".join(sep) + " |"]
    for lang, task in sorted(report.by_language_task):
        lines.append(_row(f"{lang} / {task}", report.by_language_task[(lang, task)], names))
    lines.append("")
    return "\n".join(lines)
