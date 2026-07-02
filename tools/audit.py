"""Compact, read-only audit for the weekend runs (no API).

Two health signals in one command:
  1. Structural validity of the generated corpus (empty/echo/wrong-script/etc.).
  2. Back-translation cosine distribution so far, overall and per language/task,
     with low-cosine (<0.5) items surfaced as review candidates.

Used by the weekend operator run to decide what to report and what to flag.
"""
from __future__ import annotations

import collections
import glob
import json
import statistics

from syndata.data_structures import SyntheticItem
from syndata.filters.structural import StructuralFilter

SCORES = "data/filtered/backtranslation_scores.jsonl"
LOW_COS = 0.5


def main() -> int:
    flt = StructuralFilter()
    fails = collections.Counter()
    totals = collections.Counter()
    fail_examples: list[str] = []
    for f in sorted(glob.glob("data/generated/**/*.jsonl", recursive=True)):
        task = f.replace("\\", "/").split("/")[3]
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            it = SyntheticItem.model_validate_json(line)
            totals[task] += 1
            res = flt.evaluate(it)
            if not res.passed:
                fails[task] += 1
                if len(fail_examples) < 8:
                    fail_examples.append(f"{it.id}: {res.reason}")

    print("== structural (fail/total by task) ==")
    for t in sorted(totals):
        print(f"  {t:16} {fails.get(t, 0)}/{totals[t]}")
    if fail_examples:
        print("  examples:")
        for e in fail_examples:
            print(f"    {e}")

    recs = []
    try:
        for line in open(SCORES, encoding="utf-8"):
            if line.strip():
                recs.append(json.loads(line))
    except FileNotFoundError:
        pass

    cos = [r["cos"] for r in recs if r.get("cos") is not None]
    total_items = sum(totals.values())
    print(f"\n== back-translation ({len(recs)} scored / {total_items} items, "
          f"{len(cos)} with cosine) ==")
    if cos:
        srt = sorted(cos)
        print(f"  overall: mean={statistics.mean(cos):.3f} median={statistics.median(cos):.3f} "
              f"min={min(cos):.3f} p10={srt[len(srt)//10]:.3f} max={max(cos):.3f}")
        by = collections.defaultdict(list)
        for r in recs:
            if r.get("cos") is not None:
                by[(r["lang"], r["task"])].append(r["cos"])
        print("  by lang/task (mean cosine, n):")
        for k in sorted(by):
            print(f"    {k[0]}/{k[1]:16} {statistics.mean(by[k]):.3f}  (n={len(by[k])})")
        low = [r for r in recs if r.get("cos") is not None and r["cos"] < LOW_COS]
        print(f"  LOW cosine (<{LOW_COS}): {len(low)} — review candidates")
        for r in low[:10]:
            print(f"    {r['id']} cos={r['cos']}")
    errs = [r for r in recs if r.get("error")]
    if errs:
        print(f"  scoring errors: {len(errs)} (e.g. {str(errs[0].get('error'))[:100]})")
    print(f"  unscored remaining (back-translation): {total_items - len(recs)}")

    # --- LLM-judge ensemble ---
    jrecs = []
    try:
        for line in open("data/filtered/judge_scores.jsonl", encoding="utf-8"):
            if line.strip():
                jrecs.append(json.loads(line))
    except FileNotFoundError:
        pass
    if jrecs:
        print(f"\n== judge ensemble ({len(jrecs)} judge-scores) ==")
        by_judge = collections.Counter(r["judge"].split("/")[-1] for r in jrecs)
        print(f"  coverage by judge: {dict(by_judge)}")
        for axis in ("fluency", "faithfulness", "bias", "overall"):
            vals = [r[axis] for r in jrecs if r.get(axis) is not None]
            if vals:
                print(f"  {axis:12} mean={statistics.mean(vals):.3f} min={min(vals):.3f}")
        by_item = collections.defaultdict(list)
        for r in jrecs:
            if r.get("overall") is not None:
                by_item[r["item_id"]].append(r["overall"])
        ens = [statistics.mean(v) for v in by_item.values()]
        low = [iid for iid, v in by_item.items() if statistics.mean(v) < 0.6]
        if ens:
            print(f"  ensemble-mean overall: {statistics.mean(ens):.3f}; "
                  f"items with ensemble<0.6: {len(low)} (review candidates)")
            for iid in low[:8]:
                print(f"    {iid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
