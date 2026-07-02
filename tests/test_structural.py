"""Structural filter: deterministic format checks, no API."""
from __future__ import annotations

from syndata.data_structures import TaskFamily
from syndata.filters.structural import StructuralFilter


def test_clean_qa_item_passes(make_item):
    result = StructuralFilter().evaluate(make_item())
    assert result.passed
    assert result.score == 1.0
    assert result.reason is None


def test_qa_missing_expected_fails(make_item):
    result = StructuralFilter().evaluate(make_item(expected=None))
    assert not result.passed
    assert "missing 'expected'" in result.reason


def test_classification_missing_expected_fails(make_item):
    item = make_item(task_family=TaskFamily.CLASSIFICATION, expected="   ")
    result = StructuralFilter().evaluate(item)
    assert not result.passed


def test_instruction_without_expected_is_fine(make_item):
    # Only QA/classification/translation require an answer; instruction items may omit it.
    item = make_item(task_family=TaskFamily.INSTRUCTION, expected=None,
                     prompt="एक छोटी कहानी लिखें।")
    assert StructuralFilter().evaluate(item).passed


def test_translation_missing_expected_fails(make_item):
    # A translation with no translation is broken — the Week-5 empty-answer defect.
    item = make_item(
        task_family=TaskFamily.TRANSLATION, expected=None,
        prompt="इस अंग्रेज़ी वाक्य का हिंदी में अनुवाद करें: 'Good morning.'",
    )
    result = StructuralFilter().evaluate(item)
    assert not result.passed
    assert "missing 'expected'" in result.reason


def test_translation_echo_fails(make_item):
    # expected == prompt means no translation happened (the no-op echo defect).
    text = "कृपया स्टेशन पहुँचने पर मुझे कॉल करें।"
    item = make_item(task_family=TaskFamily.TRANSLATION, prompt=text, expected=text)
    result = StructuralFilter().evaluate(item)
    assert not result.passed
    assert "no-op" in result.reason


def test_wellformed_translation_passes(make_item):
    item = make_item(
        task_family=TaskFamily.TRANSLATION,
        prompt="इस अंग्रेज़ी वाक्य का हिंदी में अनुवाद करें: 'Good morning.'",
        expected="सुप्रभात।",
    )
    assert StructuralFilter().evaluate(item).passed


def test_empty_prompt_fails(make_item):
    result = StructuralFilter().evaluate(make_item(prompt="   "))
    assert not result.passed
    assert "empty prompt" in result.reason


def test_json_scaffolding_leak_fails(make_item):
    # parse_response fell back to dumping raw JSON — the prompt still looks like JSON.
    item = make_item(prompt='{"prompt": "भारत की राजधानी?", "expected": "दिल्ली"}')
    result = StructuralFilter().evaluate(item)
    assert not result.passed
    assert "raw JSON" in result.reason


def test_code_fence_leak_fails(make_item):
    item = make_item(prompt="```json\nभारत की राजधानी?\n```")
    assert not StructuralFilter().evaluate(item).passed


def test_truncation_without_terminal_punctuation_fails(make_item):
    long_unterminated = "यह एक बहुत लंबा वाक्य है जो बीच में ही कट गया है और इसका कोई अंत नहीं"
    result = StructuralFilter().evaluate(make_item(prompt=long_unterminated, expected="ठीक है।"))
    assert not result.passed
    assert "truncation" in result.reason


def test_short_prompt_without_punctuation_is_exempt(make_item):
    # Under 40 chars: a label-like prompt may legitimately lack terminal punctuation.
    assert StructuralFilter().evaluate(make_item(prompt="नमस्ते", expected="ok")).passed


def test_degenerate_repetition_fails(make_item):
    spam = " ".join(["राम"] * 20)
    result = StructuralFilter().evaluate(make_item(prompt=spam + "।", expected="राम।"))
    assert not result.passed
    assert "repeat" in result.reason


def test_score_decreases_with_violation_count(make_item):
    # An item with two violations scores lower than one with a single violation.
    one = StructuralFilter().evaluate(make_item(expected=None))
    two = StructuralFilter().evaluate(make_item(prompt="{bad", expected=None))
    assert two.score < one.score < 1.0
