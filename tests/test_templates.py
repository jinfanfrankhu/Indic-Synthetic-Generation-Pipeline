"""Prompt templates: pure functions over a SeedItem, no API."""
from __future__ import annotations

from syndata.data_structures import SeedItem, TaskFamily
from syndata.templates import (
    _extract_source,
    default_template_for,
    get_template,
    translation_task,
)


def _translation_seed(prompt: str = "Translate to the target language: 'Good morning. How are you today?'"):
    return SeedItem(id="seed-translation-001", task_family=TaskFamily.TRANSLATION,
                    prompt=prompt, metadata={})


def test_translation_is_default_for_translation_family():
    # The whole point of the fix: translation no longer routes to direct_translate.
    assert default_template_for(TaskFamily.TRANSLATION) == "translation_task"
    assert get_template("translation_task") is translation_task


def test_extract_source_pulls_quoted_sentence():
    assert _extract_source("Translate to the target language: 'Where is the market?'") \
        == "Where is the market?"
    # Internal apostrophe (o'clock): greedy match keeps the whole sentence.
    src = _extract_source("Translate to the target language: 'Reserve a table at seven o'clock.'")
    assert src == "Reserve a table at seven o'clock."


def test_extract_source_fallback_without_quotes():
    assert _extract_source("Translate to the target language: Good morning.") == "Good morning."


def test_translation_task_preserves_english_source_and_demands_answer():
    system, user = translation_task(_translation_seed(), "Hindi")
    # The English source must survive verbatim into the exercise (so it's a real
    # translation, not a no-op), and the contract must require a non-empty answer.
    assert "Good morning. How are you today?" in user
    assert "Hindi" in system
    assert "must not be empty" in system
    assert 'must not equal "prompt"' in system
