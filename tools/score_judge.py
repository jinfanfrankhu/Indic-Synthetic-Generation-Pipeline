"""Resumable, budget-bounded LLM-judge ensemble scoring via OpenRouter (free tier).

Scores each generated item on fluency / faithfulness / bias with a panel of
decorrelated, non-teacher judges. Score-only (DESIGN.md Q3/Q5): nothing is dropped.

Free-tier reality: popular free models are often provider-429-congested, so:
  - **Resumable per (item, judge)** — only SUCCESSFUL scores are recorded, so a 429'd
    pair is retried on the next run (weekend congestion clears at off-peak hours).
  - **Budget-bounded** — <= --daily-cap ATTEMPTS per UTC day (OpenRouter free = 1000/day,
    and failed attempts count against it, so we cap attempts, not successes).
  - **Congestion-aware** — a judge that fails N times in a row is dropped for the rest
    of THIS run and retried next run, so budget isn't burned on a temporarily-dead model.

Usage:
  python tools/score_judge.py --per-run-budget 300
  python tools/score_judge.py --judges openrouter:nvidia/nemotron-3-super-120b-a12b:free,...
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
_cf = os.environ.get("SSL_CERT_FILE")
if _cf and not os.path.exists(_cf):
    import certifi

    os.environ["SSL_CERT_FILE"] = certifi.where()

from syndata.client import build_client
from syndata.data_structures import SyntheticItem
from syndata.judge import score_item
from syndata.seeds import load_seeds

SCORES = "data/filtered/judge_scores.jsonl"
LEDGER = "tools/judge_ledger.json"
DEFAULT_JUDGES = [
    "openrouter:nvidia/nemotron-3-super-120b-a12b:free",  # reliable core (NVIDIA)
    "openrouter:openai/gpt-oss-20b:free",                 # reliable core (OpenAI)
    "openrouter:meta-llama/llama-3.3-70b-instruct:free",  # best-effort (Meta)
    "openrouter:qwen/qwen3-next-80b-a3b-instruct:free",   # best-effort (Alibaba)
]
MAX_CONSEC_FAIL = 4  # drop a judge for the rest of the run after this many in a row


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _done_pairs() -> set[tuple[str, str]]:
    done: set[tuple[str, str]] = set()
    if os.path.exists(SCORES):
        for line in open(SCORES, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done.add((r["item_id"], r["judge"]))
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default=",".join(DEFAULT_JUDGES))
    ap.add_argument("--per-run-budget", type=int, default=300, help="max attempts this run")
    ap.add_argument("--daily-cap", type=int, default=900, help="max attempts per UTC day")
    ap.add_argument("--calls-per-minute", type=float, default=15.0)
    ap.add_argument("--seeds", default="data/seeds/seed_pool_20260629.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--include-translation", action="store_true")
    args = ap.parse_args()

    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    day = _utc_day()
    ledger = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    used = int(ledger.get(day, 0))
    budget = min(args.per_run_budget, args.daily_cap - used)
    if budget <= 0:
        print(f"[judge] daily cap reached for {day} (used {used}/{args.daily_cap}); nothing to do.")
        return 0

    done = _done_pairs()
    seeds = {s.id: s for s in load_seeds(args.seeds)}
    items = []
    for f in sorted(glob.glob("data/generated/**/*.jsonl", recursive=True)):
        if not args.include_translation and "/translation/" in f.replace("\\", "/"):
            continue
        for line in open(f, encoding="utf-8"):
            if line.strip():
                items.append(SyntheticItem.model_validate_json(line))
    if args.limit:
        items = items[:args.limit]

    # Item-major work list so every item accrues a full ensemble before we move on.
    work = [(it, j) for it in items for j in judges
            if (it.id, j) not in done and it.seed_id in seeds]
    if not work:
        print(f"[judge] all (item,judge) pairs already scored; nothing to do.")
        return 0

    clients = {j: build_client(j, calls_per_minute=args.calls_per_minute, max_retries=1) for j in judges}
    consec_fail = {j: 0 for j in judges}
    congested: set[str] = set()

    attempts = success = 0
    overalls: list[float] = []
    t0 = time.time()
    os.makedirs(os.path.dirname(SCORES), exist_ok=True)
    with open(SCORES, "a", encoding="utf-8") as out:
        for it, j in work:
            if attempts >= budget:
                break
            if j in congested:
                continue
            attempts += 1
            used += 1
            ledger[day] = used
            json.dump(ledger, open(LEDGER, "w"), indent=2)
            try:
                sc = score_item(it, seeds[it.seed_id], j, clients[j])
                task = it.task_family.value if hasattr(it.task_family, "value") else str(it.task_family)
                rec = {"item_id": it.id, "seed_id": it.seed_id, "lang": it.target_language,
                       "task": task, "judge": j,
                       **{a.value: round(v, 4) for a, v in sc.scores.items()},
                       "overall": round(sc.overall, 4), "rationale": sc.judge_rationale,
                       "ts": datetime.now(timezone.utc).isoformat()}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                success += 1
                overalls.append(sc.overall)
                consec_fail[j] = 0
            except Exception:  # noqa: BLE001 — congestion/parse error; retry next run
                consec_fail[j] += 1
                if consec_fail[j] >= MAX_CONSEC_FAIL:
                    congested.add(j)
            if attempts % 25 == 0:
                print(f"[judge] {attempts} attempts, {success} ok "
                      f"({attempts - success} fail); congested={sorted(c.split('/')[-1] for c in congested)}",
                      flush=True)

    dist = (f"mean={statistics.mean(overalls):.3f} median={statistics.median(overalls):.3f}"
            if overalls else "no successful scores")
    print(f"[judge] day={day}: {attempts} attempts, {success} scored in {time.time()-t0:.0f}s; "
          f"quota used {used}/{args.daily_cap}; overall {dist}")
    if congested:
        print(f"[judge] congested this run (retry next): {sorted(congested)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
