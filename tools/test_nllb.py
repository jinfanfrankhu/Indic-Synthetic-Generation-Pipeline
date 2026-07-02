"""Smoke-test NLLB-200 as the (independent, local) back-translator.

Back-translates 1-2 real generated items per language to English and reports the
SBERT cosine vs. the English seed — the full back-translation consistency signal,
using a model that is NOT the teacher.
"""
from __future__ import annotations

import glob
import os

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

print(f"loading {MODEL} (first run downloads ~5.5GB)...", flush=True)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
model.eval()


def _lang_id(code: str) -> int:
    i = tok.convert_tokens_to_ids(code)
    if i is None or i == tok.unk_token_id:
        i = getattr(tok, "lang_code_to_id", {}).get(code)
    return i


ENG = _lang_id("eng_Latn")


def back_translate(text: str, lang: str) -> str:
    tok.src_lang = NLLB_CODE[lang]
    inp = tok(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        gen = model.generate(**inp, forced_bos_token_id=ENG, max_length=256, num_beams=4)
    return tok.batch_decode(gen, skip_special_tokens=True)[0]


seeds = {s.id: s for s in load_seeds("data/seeds/seed_pool_20260629.json")}
emb = SbertEmbedder()

picks: dict[str, list[SyntheticItem]] = {}
for f in sorted(glob.glob("data/generated/*/*/*.jsonl")):
    parts = f.replace("\\", "/").split("/")
    lang, task = parts[2], parts[3]
    if task == "translation":  # embeds English source by design; skip for this demo
        continue
    picks.setdefault(lang, [])
    for line in open(f, encoding="utf-8"):
        if not line.strip() or len(picks[lang]) >= 2:
            continue
        it = SyntheticItem.model_validate_json(line)
        if it.seed_id in seeds:
            picks[lang].append(it)

for lang in ["hi", "ur", "ta", "ml"]:
    for it in picks.get(lang, []):
        seed = seeds[it.seed_id]
        gen_text = (it.prompt or "") + (f"\n{it.expected}" if it.expected else "")
        back = back_translate(gen_text, lang)
        seed_text = seed.prompt + (f"\n{seed.expected}" if seed.expected else "")
        sv, bv = emb.encode([seed_text, back])
        print(f"\n[{lang}/{it.task_family.value}] {it.id}")
        print(f"  seed (en)   : {seed_text[:110]}")
        print(f"  gen ({lang}) : {(it.prompt or '')[:80]}")
        print(f"  back (en)   : {back[:130]}")
        print(f"  cosine vs seed: {cosine(sv, bv):.3f}")
