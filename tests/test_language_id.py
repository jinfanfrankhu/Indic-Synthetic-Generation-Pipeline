"""Language-ID gate: target-script proportion, no API."""
from __future__ import annotations

import pytest

from syndata.filters.language_id import (
    CONFIDENCE_THRESHOLD,
    LanguageIDFilter,
    target_script_confidence,
)


def test_pure_target_script_is_full_confidence():
    assert target_script_confidence("नई दिल्ली", "hi") == 1.0
    assert target_script_confidence("கோவை", "ta") == 1.0
    assert target_script_confidence("തിരുവനന്തപുരം", "ml") == 1.0
    assert target_script_confidence("اسلام آباد", "ur") == 1.0


def test_english_text_is_zero_confidence_for_hindi():
    assert target_script_confidence("Hello world", "hi") == 0.0


def test_digits_and_punctuation_are_ignored():
    # Only letters count toward the denominator; "123 ..." has no letters -> 0.0.
    assert target_script_confidence("12345 !!! ???", "hi") == 0.0
    # Devanagari with surrounding digits/punct still reads as fully target-script.
    assert target_script_confidence("दिल्ली 2024!", "hi") == 1.0


def test_unknown_language_fails_closed():
    assert target_script_confidence("anything", "fr") == 0.0


def test_mixed_script_between_zero_and_one():
    conf = target_script_confidence("Delhi दिल्ली", "hi")  # 5 Latin, 6 Devanagari letters
    assert 0.0 < conf < 1.0


def test_filter_passes_clean_target_item(make_item):
    assert LanguageIDFilter().evaluate(make_item()).passed


def test_filter_rejects_english_output(make_item):
    item = make_item(prompt="What is the capital of India?", expected="New Delhi")
    result = LanguageIDFilter().evaluate(item)
    assert not result.passed
    assert "script" in result.reason


def test_threshold_is_configurable(make_item):
    # An item ~60% target script passes a lenient gate but fails the spec's 0.75.
    item = make_item(prompt="Translate: Good morning", expected="सुप्रभात नमस्ते आपका स्वागत है")
    strict = LanguageIDFilter(threshold=0.75).evaluate(item)
    lenient = LanguageIDFilter(threshold=0.3).evaluate(item)
    assert not strict.passed
    assert lenient.passed


def test_translation_family_is_exempt_by_default(make_item):
    # A *correct* translation item carries the English source by design, so the
    # script gate exempts it (passes) rather than rejecting it. The real script
    # confidence is still recorded in score/reason for the audit trail.
    item = make_item(
        task_family="translation",
        prompt="निम्नलिखित का हिंदी में अनुवाद करें: 'Good morning. How are you today?'",
        expected="सुप्रभात। आज आप कैसे हैं?",
    )
    result = LanguageIDFilter().evaluate(item)
    assert result.passed
    assert "exempt" in result.reason
    assert result.score < CONFIDENCE_THRESHOLD  # the real proportion, unmasked


def test_exemption_is_configurable(make_item):
    # Opting translation back in (empty exempt set) restores strict gating.
    item = make_item(
        task_family="translation",
        prompt="निम्नलिखित का हिंदी में अनुवाद करें: 'Good morning. How are you today?'",
        expected="सुप्रभात।",
    )
    assert not LanguageIDFilter(exempt_tasks=frozenset()).evaluate(item).passed


def test_default_threshold_matches_spec():
    assert CONFIDENCE_THRESHOLD == 0.75
