"""Back-translation consistency scoring with a local, independent MT (NLLB-200).

Back-translates every generated item to English with **NLLB-200** — a dedicated MT
model, deliberately NOT the Gemini teacher (independence + literalness are what make
back-translation a valid check; see docs/lit_review.md and DESIGN.md Q5) — and records
the SBERT cosine vs. the English seed. Score-only: nothing is dropped.

Local and unlimited, so it scores the whole corpus in one resumable pass (no API, no
quota). Resumable: already-scored item ids in the output are skipped, so a crash or a
second run (e.g. after Friday's translation regen) just fills the gap.

Usage:
  python tools/score_backtranslation.py            # score all unscored (skips translation)
  python tools/score_backtranslation.py --limit 20 # smoke test
  python tools/score_backtranslation.py --include-translation   # after the regen
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import time

_cf = os.environ.get("SSL_CERT_FILE")
if _cf and not os.path.exists(_cf):
    import certifi

    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from syndata.data_structures import SyntheticItem
from syndata.filters.back_translation import SbertEmbedder, cosine
from syndata.seeds import load_seeds

SCORES = "data/filtered/backtranslation_scores.jsonl"
MODEL = "facebook/nllb-200-distilled-1.3B"
NLLB_CODE = {"hi": "hin_Deva", "ur": "urd_Arab", "ta": "tam_Taml", "ml": "mal_Mlym"}


def _scored_ids() -> set[str]:
    ids: set[str] = set()
    if os.path.exists(SCORES):
        for line in open(SCORES, encoding="utf-8"):
            if line.strip():
                ids.add(json.loads(line)["id"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="data/seeds/seed_pool_20260629.json")
    ap.add_argument("--limit", type=int, default=0, help="0 = all unscored")
    ap.add_argument("--include-translation", action="store_true",
                    help="also score the translation family (skipped by default until regen)")
    args = ap.parse_args()

    done = _scored_ids()
    items: list[SyntheticItem] = []
    for f in sorted(glob.glob("data/generated/**/*.jsonl", recursive=True)):
        if not args.include_translation and "/translation/" in f.replace("\\", "/"):
            continue
        for line in open(f, encoding="utf-8"):
            if line.strip():
                it = SyntheticItem.model_validate_json(line)
                if it.id not in done:
                    items.append(it)
    if args.limit:
        items = items[:args.limit]
    if not items:
        print(f"[bt] all applicable items already scored ({len(done)} on file); nothing to do.")
        return 0

    seeds = {s.id: s for s in load_seeds(args.seeds)}
    print(f"[bt] loading NLLB-200 + SBERT (first run downloads the model)...", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
    model.eval()
    eng = tok.convert_tokens_to_ids("eng_Latn")
    if eng is None or eng == tok.unk_token_id:
        eng = getattr(tok, "lang_code_to_id", {}).get("eng_Latn")
    emb = SbertEmbedder()

    def back_translate(text: str, lang: str) -> str:
        tok.src_lang = NLLB_CODE[lang]
        inp = tok(text, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            gen = model.generate(**inp, forced_bos_token_id=eng, max_length=256, num_beams=4)
        return tok.batch_decode(gen, skip_special_tokens=True)[0]

    os.makedirs(os.path.dirname(SCORES), exist_ok=True)
    cos_all: list[float] = []
    t0 = time.time()
    n = 0
    with open(SCORES, "a", encoding="utf-8") as out:
        for it in items:
            task = it.task_family.value if hasattr(it.task_family, "value") else str(it.task_family)
            rec = {"id": it.id, "seed_id": it.seed_id, "lang": it.target_language,
                   "task": task, "translator": "nllb-200-distilled-1.3B"}
            seed = seeds.get(it.seed_id)
            if seed is None:
                rec.update({"cos": None, "error": "no seed"})
            else:
                try:
                    gen_text = (it.prompt or "") + (f"\n{it.expected}" if it.expected else "")
                    back = back_translate(gen_text, it.target_language)
                    seed_text = seed.prompt + (f"\n{seed.expected}" if seed.expected else "")
                    sv, bv = emb.encode([seed_text, back])
                    c = cosine(sv, bv)
                    rec.update({"cos": round(c, 4), "back_translation": back})
                    cos_all.append(c)
                except Exception as err:  # noqa: BLE001 — record + keep going
                    rec.update({"cos": None, "error": str(err)[:200]})
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            n += 1
            if n % 50 == 0:
                rate = n / (time.time() - t0)
                print(f"[bt] {n}/{len(items)}  ({rate:.2f}/s)  "
                      f"cos_mean={statistics.mean(cos_all):.3f}", flush=True)

    dist = (f"mean={statistics.mean(cos_all):.3f} median={statistics.median(cos_all):.3f} "
            f"min={min(cos_all):.3f}" if cos_all else "no successful scores")
    print(f"[bt] done: {n} scored in {time.time() - t0:.0f}s; cosine {dist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
