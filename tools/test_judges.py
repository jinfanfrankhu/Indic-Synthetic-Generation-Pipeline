"""Probe OpenRouter free judge candidates for availability + valid JSON scoring.

Picks the ensemble empirically: run each candidate on one real item, keep the ones
that respond with parseable axis scores.
"""
from __future__ import annotations

import glob
import os

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

CANDIDATES = [
    "openrouter:nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter:nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter:openai/gpt-oss-120b:free",
    "openrouter:openai/gpt-oss-20b:free",
    "openrouter:nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter:meta-llama/llama-3.3-70b-instruct:free",
    "openrouter:qwen/qwen3-next-80b-a3b-instruct:free",
]

seeds = {s.id: s for s in load_seeds("data/seeds/seed_pool_20260629.json")}
item = None
for f in sorted(glob.glob("data/generated/hi/qa/*.jsonl")):
    for line in open(f, encoding="utf-8"):
        if line.strip():
            it = SyntheticItem.model_validate_json(line)
            if it.seed_id in seeds:
                item = it
                break
    if item:
        break
seed = seeds[item.seed_id]
print(f"probing on {item.id}\n")

ok = []
for j in CANDIDATES:
    try:
        c = build_client(j, calls_per_minute=20, max_retries=1)
        sc = score_item(item, seed, j, c)
        axes = {a.value: round(v, 2) for a, v in sc.scores.items()}
        print(f"OK   {j:58} overall={sc.overall:.2f} {axes}")
        ok.append(j)
    except Exception as e:  # noqa: BLE001
        msg = repr(e)
        tag = "429/busy" if "429" in msg else msg[:70]
        print(f"ERR  {j:58} {tag}")

print(f"\nresponding: {len(ok)}/{len(CANDIDATES)}")
for j in ok:
    print(f"  {j}")
