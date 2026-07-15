"""Classification prompts must carry their option list into the generated item.

A classification item whose prompt hides its labels in metadata is unanswerable —
the model has nothing to choose from. That was the biggest format-failure bucket
in the 2026-07-13 review (docs/error_taxonomy.md), where the teacher inlined the
options only ~95% of the time because nothing required it.
"""
from __future__ import annotations

import json

import pytest

from syndata.data_structures import SeedItem, TaskFamily
from syndata.templates import adapt_and_localize, direct_translate


def _seed(**over) -> SeedItem:
    data = {
        "id": "seed-classification-001",
        "task_family": "classification",
        "prompt": "The service was slow and the food cold. Classify the sentiment.",
        "expected": "negative",
        "labels": ["positive", "neutral", "negative"],
        "metadata": {},
    }
    data.update(over)
    return SeedItem.model_validate(data)


@pytest.mark.parametrize("template", [adapt_and_localize, direct_translate])
def test_labels_are_passed_to_the_teacher(template):
    _system, user = template(_seed(), "Hindi")
    for label in ("positive", "neutral", "negative"):
        assert label in user


@pytest.mark.parametrize("template", [adapt_and_localize, direct_translate])
def test_prompt_must_carry_the_options_inline(template):
    _system, user = template(_seed(), "Hindi")
    # The instruction must demand the options end up inside the produced "prompt",
    # not merely be known to the teacher.
    assert "MUST end with the localized options" in user


@pytest.mark.parametrize("template", [adapt_and_localize, direct_translate])
def test_expected_must_be_one_of_the_localized_labels(template):
    _system, user = template(_seed(), "Tamil")
    assert "MUST be exactly one of those localized labels" in user


@pytest.mark.parametrize("template", [adapt_and_localize, direct_translate])
def test_non_classification_seeds_get_no_label_rule(template):
    qa = SeedItem.model_validate({
        "id": "seed-qa-001", "task_family": "qa",
        "prompt": "What year did the first man walk on the moon?",
        "expected": "1969", "labels": None, "metadata": {},
    })
    _system, user = template(qa, "Hindi")
    assert "Label set" not in user


def test_seating_puzzle_seed_answer_is_correct():
    """seed-reasoning-bs-0008 shipped a wrong answer that propagated to all 4
    languages. Charlie is immediately right of Bob, so (Bob, Charlie) is a block;
    only Bob, Charlie, Alice keeps Alice away from Bob."""
    pool = json.load(open("data/seeds/seed_pool_20260713.json", encoding="utf-8"))
    seed = next(s for s in pool["seeds"] if s["id"] == "seed-reasoning-bs-0008")
    assert "Bob, Charlie, Alice" in seed["expected"]
    assert "The order is Alice, Bob, Charlie" not in seed["expected"]
