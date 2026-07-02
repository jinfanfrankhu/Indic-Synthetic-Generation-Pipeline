"""Resumable, budget-bounded back-translation scoring for the weekend runs.

Scores generated items with the back-translation consistency signal (Gemini
back-translate -> multilingual-SBERT cosine vs. the English seed), but two ways
that the plain `syndata filter --back-translate` can't:

  * **Budget-bounded** — makes at most N Gemini calls per run and never exceeds a
    daily cap, so it stays under the free-tier RPD while unattended.
  * **Resumable** — records which items are scored (data/filtered/backtranslation_
    scores.jsonl) and a per-day call ledger (tools/quota_ledger.json), so runs
    across the weekend pick up exactly where the last one stopped.

Score-only by design (DESIGN.md Q3/Q5): we record cosines, we do not drop anything.

Usage:
  python tools/score_backtranslation.py --per-run-budget 210 --calls-per-minute 12
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
from datetime import datetime, timedelta

from dotenv import load_dotenv

from syndata.client import build_client
from syndata.data_structures import SyntheticItem
from syndata.filters.back_translation import BackTranslationFilter, SbertEmbedder
from syndata.seeds import load_seeds

# conda on Windows points SSL_CERT_FILE at a base-env cacert.pem that often doesn't
# exist, which breaks httpx/HuggingFace TLS. Fall back to certifi's real bundle.
_cf = os.environ.get("SSL_CERT_FILE")
if _cf and not os.path.exists(_cf):
    import certifi

    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

SCORES = "data/filtered/backtranslation_scores.jsonl"
LEDGER = "tools/quota_ledger.json"
MODEL = "gemini:gemini-3.1-flash-lite"


def quota_day() -> str:
    """Bucket calls by Gemini's reset boundary (midnight PT ~= 03:00 ET).

    Subtracting 3h from local (Eastern) time puts everything before 3 AM into the
    previous quota-day, matching Google's daily RPD reset without a tz dependency.
    """
    return (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d")


def _load_json(path: str, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def _scored_ids() -> set[str]:
    ids: set[str] = set()
    if os.path.exists(SCORES):
        for line in open(SCORES, encoding="utf-8"):
            if line.strip():
                ids.add(json.loads(line)["id"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-run-budget", type=int, default=210, help="max Gemini calls this run")
    ap.add_argument("--daily-cap", type=int, default=420, help="max Gemini calls per quota-day")
    ap.add_argument("--calls-per-minute", type=int, default=12)
    ap.add_argument("--seeds", default="data/seeds/seed_pool_20260629.json")
    args = ap.parse_args()

    load_dotenv()  # resolve GEMINI_API_KEY from repo .env (standalone script, no cli.main)
    day = quota_day()
    ledger = _load_json(LEDGER, {})
    used = int(ledger.get(day, 0))
    budget = min(args.per_run_budget, args.daily_cap - used)
    if budget <= 0:
        print(f"[scorer] daily cap reached for {day} (used {used}/{args.daily_cap}); nothing to do.")
        return 0

    done = _scored_ids()
    unscored: list[SyntheticItem] = []
    for f in sorted(glob.glob("data/generated/**/*.jsonl", recursive=True)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                it = SyntheticItem.model_validate_json(line)
                if it.id not in done:
                    unscored.append(it)
    if not unscored:
        print(f"[scorer] all {len(done)} items already scored; nothing to do.")
        return 0

    seeds = load_seeds(args.seeds)
    seed_lookup = {s.id: s for s in seeds}
    client = build_client(MODEL, max_retries=1, calls_per_minute=args.calls_per_minute)
    flt = BackTranslationFilter(
        translator_model=MODEL, seed_lookup=seed_lookup, embedder=SbertEmbedder(), client=client
    )

    os.makedirs(os.path.dirname(SCORES), exist_ok=True)
    calls = 0
    errors = 0
    cosines: list[float] = []
    with open(SCORES, "a", encoding="utf-8") as out:
        for it in unscored:
            if calls >= budget:
                break
            task = it.task_family.value if hasattr(it.task_family, "value") else str(it.task_family)
            rec = {"id": it.id, "seed_id": it.seed_id, "lang": it.target_language, "task": task}
            seed = seed_lookup.get(it.seed_id)
            if seed is None:
                rec.update({"cos": None, "error": "no seed"})  # no API call; not counted
            else:
                try:
                    cos, bt = flt.similarity(it, seed)
                    rec.update({"cos": round(cos, 4), "back_translation": bt})
                    cosines.append(cos)
                except Exception as err:  # noqa: BLE001 — record + keep going
                    rec.update({"cos": None, "error": str(err)[:200]})
                    errors += 1
                calls += 1
                used += 1
                ledger[day] = used
                json.dump(ledger, open(LEDGER, "w"), indent=2)  # flush each call: crash-safe
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()

    dist = (
        f"mean={statistics.mean(cosines):.3f} median={statistics.median(cosines):.3f} "
        f"min={min(cosines):.3f} max={max(cosines):.3f}"
        if cosines else "no successful scores"
    )
    print(f"[scorer] day={day}: {calls} calls ({len(cosines)} ok, {errors} errors); "
          f"quota used today {used}/{args.daily_cap}")
    print(f"[scorer] cosine {dist}")
    print(f"[scorer] unscored remaining (approx): {max(0, len(unscored) - calls)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
