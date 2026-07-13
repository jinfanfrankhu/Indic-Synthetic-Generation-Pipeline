"""Tests for the generation duplicate guard (`generated_seed_keys`).

The sweep commands (`generate-batch`, `generate-drip`) use this to avoid
regenerating a (seed, language, task) that already has an item on disk — the
failure mode that produced temperature near-duplicates in the Week 5 corpus.
"""
from __future__ import annotations

from pathlib import Path

from syndata.seeds import generated_seed_keys


def _write(out_root: Path, lang: str, task: str, items) -> None:
    d = out_root / lang / task
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"drip_mock.jsonl").open("a", encoding="utf-8") as fh:
        for it in items:
            fh.write(it.model_dump_json() + "\n")


def test_missing_tree_returns_empty(tmp_path):
    assert generated_seed_keys(tmp_path / "nope") == set()


def test_collects_triples_across_combos(tmp_path, make_item):
    _write(tmp_path, "hi", "qa", [
        make_item(id="a", seed_id="seed-qa-001", target_language="hi", task_family="qa"),
        make_item(id="b", seed_id="seed-qa-002", target_language="hi", task_family="qa"),
    ])
    _write(tmp_path, "ta", "reasoning", [
        make_item(id="c", seed_id="seed-reasoning-001", target_language="ta",
                  task_family="reasoning"),
    ])
    keys = generated_seed_keys(tmp_path)
    assert keys == {
        ("seed-qa-001", "hi", "qa"),
        ("seed-qa-002", "hi", "qa"),
        ("seed-reasoning-001", "ta", "reasoning"),
    }


def test_same_seed_different_language_is_distinct(tmp_path, make_item):
    _write(tmp_path, "hi", "qa",
           [make_item(id="a", seed_id="seed-qa-001", target_language="hi", task_family="qa")])
    _write(tmp_path, "ur", "qa",
           [make_item(id="b", seed_id="seed-qa-001", target_language="ur", task_family="qa")])
    keys = generated_seed_keys(tmp_path)
    # A guard keyed on the triple must NOT treat these as duplicates: the same
    # English seed rendered into hi vs. ur are two legitimately different items.
    assert ("seed-qa-001", "hi", "qa") in keys
    assert ("seed-qa-001", "ur", "qa") in keys
    assert len(keys) == 2


def test_malformed_lines_are_skipped(tmp_path, make_item):
    d = tmp_path / "hi" / "qa"
    d.mkdir(parents=True)
    good = make_item(id="a", seed_id="seed-qa-001", target_language="hi", task_family="qa")
    (d / "drip_mock.jsonl").write_text(
        good.model_dump_json() + "\n"
        + "not json\n"
        + '{"id": "x", "no": "required keys"}\n',
        encoding="utf-8",
    )
    assert generated_seed_keys(tmp_path) == {("seed-qa-001", "hi", "qa")}
