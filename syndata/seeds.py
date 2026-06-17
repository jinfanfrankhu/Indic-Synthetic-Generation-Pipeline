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
