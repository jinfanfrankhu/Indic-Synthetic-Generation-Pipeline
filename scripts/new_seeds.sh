#!/usr/bin/env bash
#
# Author N new English seeds with an LLM, validate them, print a review report.
#
# This deliberately STOPS before generation. The 2026-07-13 full-corpus review
# (docs/error_taxonomy.md) found bootstrapped seeds defect at 5.2% vs 0.8% for
# hand-curated ones, and a single bad seed propagates into all four target
# languages. The review gate is the cheap part; regenerating four languages is not.
#
# Authoring runs through the local Claude Code CLI (`claude -p`) via the
# `claude-cli` teacher, so it needs no API key or provider account - just your
# existing Claude Code login.
#
# Usage:
#   scripts/new_seeds.sh                    # 125 seeds via claude-cli:sonnet
#   N=60 scripts/new_seeds.sh               # fewer
#   TEACHER=claude-cli:opus scripts/new_seeds.sh   # stronger authoring model
#   TEACHER=gemini:gemini-3.1-flash-lite scripts/new_seeds.sh  # or any provider
#
# Env:
#   N        total seeds, split across the 6 task families (default 125)
#   TEACHER  seed-authoring model: claude-cli[:sonnet|:opus], or provider:model
#   POOL     existing pool used for few-shot examples + dedup + id allocation
#
set -euo pipefail
cd "$(dirname "$0")/.."

N="${N:-125}"
# Authoring quality drives corpus quality (a bad seed corrupts all 4 languages),
# so this is worth a strong model. claude-cli:opus if you want more headroom.
TEACHER="${TEACHER:-claude-cli:sonnet}"
POOL="${POOL:-data/seeds/seed_pool_20260713.json}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT="data/seeds/bootstrapped_${TS}.json"

# Windows consoles default to cp1252, which cannot print seed content containing
# typographic characters (em dashes, minus signs) — the report would crash after
# authoring succeeded. Force UTF-8 for every python in this script.
export PYTHONIOENCODING=utf-8

# This box's SSL_CERT_FILE points at a miniconda bundle that does not exist,
# which breaks httpx TLS. Point it at certifi's.
if [ -n "${SSL_CERT_FILE:-}" ] && [ ! -f "${SSL_CERT_FILE}" ]; then
  SSL_CERT_FILE="$(python -c 'import certifi; print(certifi.where())')"
  export SSL_CERT_FILE
fi

echo "==> Authoring ~${N} seeds with ${TEACHER} (pool: ${POOL})"
python -m syndata.cli bootstrap-seeds \
  --tasks all --n "${N}" --teacher "${TEACHER}" \
  --seeds "${POOL}" --out "${OUT}"

echo
echo "==> Review report"
python - "${OUT}" "${POOL}" <<'PY'
import json, sys, collections, re

new_path, pool_path = sys.argv[1], sys.argv[2]
new = json.load(open(new_path, encoding="utf-8"))["seeds"]
pool = json.load(open(pool_path, encoding="utf-8"))["seeds"]

def norm(p):
    return " ".join((p or "").lower().split())

pool_norm = {norm(s["prompt"]) for s in pool}
pool_ids = {s["id"] for s in pool}

by_task = collections.Counter(s["task_family"] for s in new)
print(f"  total new seeds: {len(new)}")
for t, n in sorted(by_task.items()):
    print(f"    {t:16s} {n}")

# Guardrails the pre-filters should already have enforced - verify, don't trust.
dups = [s["id"] for s in new if norm(s["prompt"]) in pool_norm]
id_clash = [s["id"] for s in new if s["id"] in pool_ids]
bad_label = [
    s["id"] for s in new
    if s["task_family"] == "classification"
    and (not s.get("labels") or s.get("expected") not in s["labels"])
]
no_opts = [
    s["id"] for s in new
    if s["task_family"] == "classification"
    and sum(1 for x in (s.get("labels") or []) if str(x).lower() in s["prompt"].lower()) < 2
]
missing_exp = [
    s["id"] for s in new
    if s["task_family"] in ("qa", "reasoning") and not s.get("expected")
]

print()
print(f"  duplicate prompt vs pool : {len(dups)}   {dups[:5]}")
print(f"  id collision vs pool     : {len(id_clash)} {id_clash[:5]}")
print(f"  classification expected not in labels : {len(bad_label)} {bad_label[:5]}")
print(f"  classification options missing from prompt : {len(no_opts)} {no_opts[:5]}")
print(f"  qa/reasoning missing expected : {len(missing_exp)} {missing_exp[:5]}")

print()
print("  --- samples (eyeball these) ---")
seen = collections.Counter()
for s in new:
    t = s["task_family"]
    if seen[t] >= 2:
        continue
    seen[t] += 1
    print(f"  [{t}] {s['id']}")
    print(f"    prompt  : {s['prompt'][:150]}")
    if s.get("expected"):
        print(f"    expected: {str(s['expected'])[:150]}")
    if s.get("labels"):
        print(f"    labels  : {s['labels']}")
PY

cat <<EOF

==> REVIEW GATE - nothing has been generated.

  1. Read ${OUT} and fix/delete any bad seed.
     Pay special attention to qa/reasoning 'expected' correctness: a wrong answer
     silently corrupts one item per language.

  2. Then run the drip YOURSELF (needs a fresh 500/day Gemini window). Run it one
     task family at a time with --per-combo set to that family's new-seed count,
     so each seed is generated exactly once per language:

     python -m syndata.cli generate-drip --languages hi,ur,ta,ml \\
       --tasks <family> --per-combo <that family's seed count> \\
       --teacher gemini:gemini-3.1-flash-lite --calls-per-minute 12 \\
       --seeds ${OUT} --out-dir data/generated_<date>

     The dup guard makes re-runs safe; merge into data/generated when happy.
EOF
