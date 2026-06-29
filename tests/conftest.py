"""Shared fixtures for the syndata test suite.

The deterministic filters and the retention aggregator are pure functions over
:class:`SyntheticItem`s, so most tests just need a cheap way to mint items with
specific fields. ``make_item`` is that factory; live API paths are never touched.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from syndata.data_structures import GenerationConfig, SyntheticItem, TaskFamily


@pytest.fixture
def make_item():
    """Factory for a fully-valid :class:`SyntheticItem` with overridable fields."""

    def _make(
        *,
        id: str = "item-1",
        seed_id: str = "seed-1",
        task_family: TaskFamily | str = TaskFamily.QA,
        target_language: str = "hi",
        prompt: str = "प्रश्न: भारत की राजधानी क्या है?",
        expected: str | None = "नई दिल्ली।",
        teacher_model: str = "mock",
    ) -> SyntheticItem:
        if isinstance(task_family, str):
            task_family = TaskFamily(task_family)
        return SyntheticItem(
            id=id,
            seed_id=seed_id,
            task_family=task_family,
            target_language=target_language,
            prompt=prompt,
            expected=expected,
            generation=GenerationConfig(
                seed_id=seed_id,
                target_language=target_language,
                teacher_model=teacher_model,
                prompt_template_name="direct_translate",
            ),
            generated_at=datetime.now(timezone.utc),
            raw_response="{}",
        )

    return _make
