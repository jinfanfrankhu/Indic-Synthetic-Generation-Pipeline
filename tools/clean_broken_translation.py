"""Remove structurally-invalid translation items so `generate-drip` refills them
with the corrected `translation_task` template.

The Week-5 drip produced ~57 broken translation items (empty answer or a no-op
echo where expected == prompt). The structural filter now rejects these; this
script rewrites each translation JSONL keeping only items that pass, leaving a gap
that a subsequent `generate-drip --tasks translation` fills with good output.

Idempotent: a second run removes nothing. Pass --dry-run to report without writing.
"""
from __future__ import annotations

import glob
import sys

from syndata.data_structures import SyntheticItem
from syndata.filters.structural import StructuralFilter

DRY = "--dry-run" in sys.argv
flt = StructuralFilter()
removed_total = 0

for path in sorted(glob.glob("data/generated/*/translation/*.jsonl")):
    kept: list[str] = []
    removed = 0
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        item = SyntheticItem.model_validate_json(line)
        if flt.evaluate(item).passed:
            kept.append(line if line.endswith("\n") else line + "\n")
        else:
            removed += 1
    if removed and not DRY:
        with open(path, "w", encoding="utf-8") as out:
            out.writelines(kept)
    removed_total += removed
    print(f"{'[dry] ' if DRY else ''}{path}: kept {len(kept)}, removed {removed}")

print(f"{'[dry] ' if DRY else ''}TOTAL removed: {removed_total}")
