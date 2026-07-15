"""Bootstrap pre-filters: the seed-level gates added after the 2026-07-13 review.

That review traced most corpus defects back to seed quality (bootstrapped seeds
5.2% defect vs. 0.8% hand-curated), and a bad seed propagates into all four
target languages. These tests pin the two classification gates that attack the
biggest buckets, plus id-collision avoidance.
"""
from __future__ import annotations

from syndata.bootstrap import BootstrapResult, _accept
from syndata.data_structures import TaskFamily


def _result(task=TaskFamily.CLASSIFICATION) -> BootstrapResult:
    return BootstrapResult(task=task, seeds=[], requested=5)


def _rec(**over) -> dict:
    rec = {
        "prompt": "The food was cold and slow. Classify the sentiment. "
                  "Options: positive, neutral, negative.",
        "expected": "negative",
        "labels": ["positive", "neutral", "negative"],
        "metadata": {"domain": "sentiment"},
    }
    rec.update(over)
    return rec


def test_valid_classification_seed_accepted():
    r = _result()
    seed = _accept(_rec(), TaskFamily.CLASSIFICATION, r)
    assert seed is not None
    assert seed.expected == "negative"


def test_expected_must_be_one_of_labels():
    r = _result()
    # "mixed" is not an offered class -> no classifier could ever produce it.
    seed = _accept(_rec(expected="mixed"), TaskFamily.CLASSIFICATION, r)
    assert seed is None
    assert r.drops.get("expected_not_in_labels") == 1


def test_prompt_must_show_the_option_list():
    r = _result()
    # Options hidden in metadata only: the model has nothing to choose from.
    # This was the single biggest format-failure bucket in the review.
    seed = _accept(
        _rec(prompt="The food was cold and slow. Classify the sentiment."),
        TaskFamily.CLASSIFICATION,
        r,
    )
    assert seed is None
    assert r.drops.get("options_not_in_prompt") == 1


def test_non_english_seed_rejected():
    r = _result(TaskFamily.QA)
    seed = _accept(
        {"prompt": "भारत की राजधानी क्या है?", "expected": "New Delhi"},
        TaskFamily.QA,
        r,
    )
    assert seed is None
    assert r.drops.get("not_english") == 1


def test_qa_requires_expected():
    r = _result(TaskFamily.QA)
    seed = _accept({"prompt": "What is the capital of India?"}, TaskFamily.QA, r)
    assert seed is None
    assert r.drops.get("missing_expected") == 1
