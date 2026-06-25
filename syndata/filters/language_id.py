"""
Language-ID gate (deterministic; no API).

REQUIREMENTS R1.3 calls for dropping items where the model is <75% confident the
output is in the target language (IndicLID in the spec). For Buttery's four
targets the scripts are **disjoint** — Devanagari (hi), Perso-Arabic (ur), Tamil
(ta), Malayalam (ml) occupy non-overlapping Unicode blocks — so the fraction of
script-bearing characters that fall in the target block is a robust, dependency-
free confidence proxy. It catches the failure modes that actually occur here:
output left in English (Latin script) and code-switching (mixed scripts).

Confidence = (target-script chars) / (all letter chars), ignoring whitespace,
digits, and punctuation (which are script-neutral). The 0.75 threshold is the one
number the spec fixes up front.

Limitation: a script gate cannot distinguish languages that *share* a script
(e.g. Urdu vs. Persian, both Perso-Arabic). That's not a failure mode the teacher
produces for our targets, but for a finer gate (or more target languages) swap in
IndicLID/fastText behind the same ``QualityFilter`` interface.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime, timezone

from ..data_structures import QualityFilter, QualityFilterResult, SyntheticItem

CONFIDENCE_THRESHOLD = 0.75

# ISO code -> list of (inclusive) Unicode codepoint ranges for the target script.
_SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "hi": [(0x0900, 0x097F)],                       # Devanagari
    "ta": [(0x0B80, 0x0BFF)],                        # Tamil
    "ml": [(0x0D00, 0x0D7F)],                        # Malayalam
    "ur": [                                          # Perso-Arabic (Urdu)
        (0x0600, 0x06FF),                            # Arabic
        (0x0750, 0x077F),                            # Arabic Supplement
        (0x08A0, 0x08FF),                            # Arabic Extended-A
        (0xFB50, 0xFDFF),                            # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),                            # Arabic Presentation Forms-B
    ],
}


def _in_ranges(cp: int, ranges: list[tuple[int, int]]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def target_script_confidence(text: str, iso_code: str) -> float:
    """Fraction of letter characters that are in the target script (0.0–1.0).

    Denominator is letters only — whitespace, digits, and punctuation are
    script-neutral and would otherwise dilute the signal. Returns 0.0 if the text
    has no letters, or if the language is unknown (fail closed).
    """
    ranges = _SCRIPT_RANGES.get(iso_code)
    if not ranges:
        return 0.0
    letters = [c for c in text if unicodedata.category(c).startswith("L")]
    if not letters:
        return 0.0
    in_script = sum(1 for c in letters if _in_ranges(ord(c), ranges))
    return in_script / len(letters)


class LanguageIDFilter(QualityFilter):
    name = "language_id"

    def __init__(self, threshold: float = CONFIDENCE_THRESHOLD) -> None:
        self.threshold = threshold

    def evaluate(self, item: SyntheticItem) -> QualityFilterResult:
        # Judge the generated text the model produced: prompt plus any answer.
        text = item.prompt or ""
        if item.expected:
            text = f"{text}\n{item.expected}"
        confidence = target_script_confidence(text, item.target_language)
        passed = confidence >= self.threshold
        reason = (
            None if passed
            else f"only {confidence:.0%} of letters in {item.target_language} script "
                 f"(<{self.threshold:.0%})"
        )
        return QualityFilterResult(
            item_id=item.id,
            filter_name=self.name,
            passed=passed,
            score=confidence,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )
