"""
Seed loading.

Seed files are JSON with a top-level ``"seeds"`` array of English seed tasks
(other top-level keys hold illustrative examples and are ignored). Each entry
parses into a :class:`SeedItem`.
"""
from __future__ import annotations

import json
from pathlib import Path

from .data_structures import SeedItem, TaskFamily

# Default seed file shipped with the repo.
DEFAULT_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seeds" / "sample_data.json"


def load_seeds(path: str | Path = DEFAULT_SEED_PATH) -> list[SeedItem]:
    """Load and parse every seed in ``path`` into :class:`SeedItem` objects.

    Raises ``FileNotFoundError`` if the path is missing and ``ValueError`` if
    the file has no ``"seeds"`` array.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if "seeds" not in raw:
        raise ValueError(f"Seed file {path} has no top-level 'seeds' array.")

    # Pydantic validates each record (task_family enum, required fields, etc.).
    return [SeedItem.model_validate(record) for record in raw["seeds"]]


def filter_by_task(seeds: list[SeedItem], task: TaskFamily) -> list[SeedItem]:
    """Return only the seeds whose ``task_family`` matches ``task``."""
    return [s for s in seeds if s.task_family == task]


def generated_seed_keys(out_root: str | Path) -> set[tuple[str, str, str]]:
    """Scan a generated-output tree for the ``(seed_id, language, task)`` triples
    already produced.

    Used as a de-duplication guard by the sweep commands (``generate-batch``,
    ``generate-drip``): a triple already present here has an item on disk, so
    regenerating it would only mint a near-duplicate (same seed, same target,
    differing only by teacher temperature). Returns an empty set if the tree is
    absent. Malformed or partial lines are skipped — a guard must never crash a
    generation run.
    """
    out_root = Path(out_root)
    keys: set[tuple[str, str, str]] = set()
    if not out_root.exists():
        return keys
    for f in out_root.glob("*/*/*.jsonl"):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    keys.add(
                        (rec["seed_id"], rec["target_language"], rec["task_family"])
                    )
                except (json.JSONDecodeError, KeyError):
                    pass
    return keys


def write_seeds(seeds: list[SeedItem], path: str | Path) -> Path:
    """Write ``seeds`` to ``path`` as a ``{"seeds": [...]}`` JSON file.

    Round-trips with :func:`load_seeds`. Parent directories are created. Written
    with ``ensure_ascii=False`` so any non-ASCII content stays human-readable.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seeds": [s.model_dump(mode="json") for s in seeds]}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path
