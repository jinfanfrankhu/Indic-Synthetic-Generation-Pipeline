"""
Structural validity filter (deterministic; no API).

Task-agnostic and task-specific format checks that don't need a model:

  - the generated prompt is present and not trivially short;
  - QA / classification items carry a non-empty ``expected`` answer;
  - no leftover scaffolding (raw JSON, markdown fences) from a parse fallback —
    a sign ``generator.parse_response`` couldn't recover the model's output;
  - no truncation artifact (long text cut off mid-sentence);
  - not degenerately repetitive — the UPDESH rule: drop if >75% of tokens repeat.

These are the cheap gates that run first in the chain. Format quality is checked
here, deterministically, rather than being handed to the LLM judge (which scores
only the subjective axes — fluency, faithfulness, bias).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..data_structures import (
    QualityFilter,
    QualityFilterResult,
    SyntheticItem,
    TaskFamily,
)

# Tasks whose items must carry an answer.
_ANSWER_REQUIRED = {TaskFamily.QA, TaskFamily.CLASSIFICATION}

MIN_PROMPT_CHARS = 5            # below this the "prompt" is not a usable task
MAX_PROMPT_CHARS = 8000         # runaway / repetition guard
MIN_TOKENS_FOR_REPETITION = 8   # too few tokens to judge repetition meaningfully
MAX_REPEAT_FRACTION = 0.75      # UPDESH: drop if >75% of tokens repeat
# Terminal punctuation across our four scripts' conventions: Latin, Devanagari
# danda (।॥), and Urdu/Arabic full stop ۔ (U+06D4) + question mark ؟ (U+061F).
_TERMINAL_PUNCT = ".?!।॥۔؟…\"')]}"


def _repeat_fraction(text: str) -> tuple[float, int]:
    """Fraction of whitespace tokens that are repeats; returns (fraction, n_tokens)."""
    tokens = text.split()
    n = len(tokens)
    if n == 0:
        return 0.0, 0
    return 1.0 - (len(set(tokens)) / n), n


class StructuralFilter(QualityFilter):
    name = "structural"

    def evaluate(self, item: SyntheticItem) -> QualityFilterResult:
        violations: list[str] = []
        prompt = (item.prompt or "").strip()

        # Presence / length.
        if not prompt:
            violations.append("empty prompt")
        elif len(prompt) < MIN_PROMPT_CHARS:
            violations.append(f"prompt under {MIN_PROMPT_CHARS} chars")
        elif len(prompt) > MAX_PROMPT_CHARS:
            violations.append(f"prompt over {MAX_PROMPT_CHARS} chars")

        # Answer required for answer-bearing tasks.
        if item.task_family in _ANSWER_REQUIRED:
            if not (item.expected or "").strip():
                violations.append(f"{item.task_family.value} item missing 'expected' answer")

        # Parse-fallback / scaffolding leakage: parse_response dumped raw text when
        # it couldn't recover JSON, so the prompt still looks like JSON or a fence.
        if prompt.startswith("{") or '"prompt"' in prompt:
            violations.append("prompt contains raw JSON scaffolding")
        if "```" in prompt:
            violations.append("prompt contains markdown code fence")

        # Truncation: long output that ends without terminal punctuation is likely
        # cut off at max_tokens. (Short prompts may legitimately omit punctuation.)
        if len(prompt) > 40 and prompt[-1] not in _TERMINAL_PUNCT:
            violations.append("possible truncation (no terminal punctuation)")

        # Degenerate repetition.
        frac, n_tokens = _repeat_fraction(prompt)
        if n_tokens >= MIN_TOKENS_FOR_REPETITION and frac > MAX_REPEAT_FRACTION:
            violations.append(f"{frac:.0%} of tokens repeat (>{MAX_REPEAT_FRACTION:.0%})")

        passed = not violations
        # Graded score: clean = 1.0, each violation pushes toward 0.
        score = max(0.0, 1.0 - 0.5 * len(violations))
        return QualityFilterResult(
            item_id=item.id,
            filter_name=self.name,
            passed=passed,
            score=score,
            reason=None if passed else "; ".join(violations),
            timestamp=datetime.now(timezone.utc),
        )
