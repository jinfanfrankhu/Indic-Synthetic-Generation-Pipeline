"""
Quality filters.

Each filter takes a :class:`~syndata.data_structures.SyntheticItem` and returns a
:class:`~syndata.data_structures.QualityFilterResult` — a pass/fail verdict plus a
filter-specific score and a human-readable reason. Filters compose via
:class:`FilterChain`, which runs every enabled filter and reports each verdict
**without dropping anything** (score-only mode). Whether an item is kept is the
caller's decision: thresholds are tuned against the gold set (see
``docs/gold_standard_protocol.md``), not hardcoded here.

Filters that ship:
  - :class:`StructuralFilter`  — deterministic format checks (no API).
  - :class:`LanguageIDFilter`  — target-script proportion gate (no API).
  - LLM-judge and back-translation filters wrap the existing engines and land
    alongside these.
"""
from __future__ import annotations

from .base import FilterChain, FilterVerdict
from .language_id import LanguageIDFilter
from .llm_judge import EnsembleJudgement, LLMJudgeFilter, aggregate_scores
from .structural import StructuralFilter

__all__ = [
    "FilterChain",
    "FilterVerdict",
    "StructuralFilter",
    "LanguageIDFilter",
    "LLMJudgeFilter",
    "EnsembleJudgement",
    "aggregate_scores",
]
