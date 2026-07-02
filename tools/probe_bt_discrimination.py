"""Does the NLLB back-translation cosine DISCRIMINATE?

If a generation is faithful, cos(back-translation, its own seed) should be high;
cos(back-translation, a *random other* seed) should be low. If matched and
mismatched overlap, the signal is worthless regardless of translator. This probes
the signal's teeth, not the translator's beauty.
"""
from __future__ import annotations

import glob
import os
import random
import statistics

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

MODEL = "facebook/nllb-200-distilled-1.3B"
NLLB_CODE = {"hi": "hin_Deva", "ur": "urd_Arab", "ta": "tam_Taml", "ml": "mal_Mlym"}
PER_LANG = 4

print(f"loading {MODEL}...", flush=True)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
model.eval()


def _lang_id(code: str) -> int:
    i = tok.convert_tokens_to_ids(code)
    return i if (i is not None and i != tok.unk_token_id) else getattr(tok, "lang_code_to_id", {}).get(code)


ENG = _lang_id("eng_Latn")


def back_translate(text: str, lang: str) -> str:
    tok.src_lang = NLLB_CODE[lang]
    inp = tok(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        gen = model.generate(**inp, forced_bos_token_id=ENG, max_length=256, num_beams=4)
    return tok.batch_decode(gen, skip_special_tokens=True)[0]


seeds = {s.id: s for s in load_seeds("data/seeds/seed_pool_20260629.json")}
random.seed(7)

rows = []  # (lang, item, seed)
for lang in ["hi", "ur", "ta", "ml"]:
    pool = []
    for f in sorted(glob.glob(f"data/generated/{lang}/*/*.jsonl")):
        if "/translation/" in f.replace("\\", "/"):
            continue
        for line in open(f, encoding="utf-8"):
            if line.strip():
                it = SyntheticItem.model_validate_json(line)
                if it.seed_id in seeds:
                    pool.append(it)
    for it in random.sample(pool, min(PER_LANG, len(pool))):
        rows.append((lang, it, seeds[it.seed_id]))

emb = SbertEmbedder()
seed_texts = [s.prompt + (f"\n{s.expected}" if s.expected else "") for (_, _, s) in rows]
bts = [back_translate((it.prompt or "") + (f"\n{it.expected}" if it.expected else ""), lang)
       for (lang, it, _) in rows]
seed_vecs = emb.encode(seed_texts)
bt_vecs = emb.encode(bts)

matched = [cosine(seed_vecs[i], bt_vecs[i]) for i in range(len(rows))]
mismatched = []
for i in range(len(rows)):
    j = random.choice([k for k in range(len(rows)) if k != i])
    mismatched.append(cosine(seed_vecs[j], bt_vecs[i]))

print(f"\nN = {len(rows)} items ({PER_LANG}/language)")
print(f"MATCHED   (bt vs own seed)   : mean={statistics.mean(matched):.3f} "
      f"min={min(matched):.3f} max={max(matched):.3f}")
print(f"MISMATCHED(bt vs random seed): mean={statistics.mean(mismatched):.3f} "
      f"min={min(mismatched):.3f} max={max(mismatched):.3f}")
print(f"separation (mean matched - mean mismatched): "
      f"{statistics.mean(matched) - statistics.mean(mismatched):+.3f}")
overlap = sum(1 for m in matched if m <= max(mismatched))
print(f"matched items that fall at/below the worst mismatched: {overlap}/{len(rows)}")
