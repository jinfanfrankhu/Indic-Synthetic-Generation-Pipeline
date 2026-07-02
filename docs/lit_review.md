

## Bactrian-X paper: https://arxiv.org/abs/2305.15011

 - Bactrian-X is a multilingual dataset of instruction-response pairs across 52 languages
 - Using this, train adapters using low-rank adaptation (LoRA) which integrate LLMs (frozen)
 - Adapters are small trainable modules (weights, neurons, etc) injected into the transformer at the attention weight matrices. If a normal output is W * x, in LoRA output = W * x + (B * A) * x. Therefore W_eff = W + BA
 - LoRA based models outperform both vanilla models (just token prediction) and instruction-tuned models (assistant type models)


## MURI paper: https://arxiv.org/abs/2409.12958

 - MURI, Multilingual Reverse Instructions, generates instruction-tuning datasets for LRLangs without needing human annotation or pre-existing multilingual models
 - instead of responding to: "write me an article," instead, it responds to: "what question could have prompted this article?"
 - pretty effective for NLU (Natural Language Understanding)


## UPDESH paper: https://arxiv.org/abs/2509.21294

 - UPDESH: a high-quality large-scale instruction-following dataset across 13 Indian languages and English
 - Use both Top-down data generation (start with English, then translate. ie, Bactrian-X) and bottom-up (how MURI approaches)
    - Top-down is only used for reasoning tasks (culture-agnostic) while generative tasks use bottom-up (needs cultural grounding)
 - Used data filtration using tool called IndicLID. If model isn't 75% sure output is in target language, output is dropped. If more than 75% of words are repeated, output is dropped.
 - Used GPT-4o as an automated judge and compared against native speakers. over 90% agreement for toxicity, problematic content, and cultural relevance. Only ~50% agreement on repetitiveness, persona adherence, and linguistic plausibility.
 - Models trained on UPDESH get consistent improvement in NLU and NLG (Natural Language Generation)


## How Reliable are LLM-as-judge paper: https://arxiv.org/abs/2505.12201

 - LLMs struggle to achieve consistent judgement across languages with average Fleiss' Kappa = ~0.3
 - Particularly poor performance in low-resource languages
 - Neither training on multilingual data nor increasing model scale improves judgement consistency
 - Prompts with explanation generation consistently achieve better consistency results
 - Proposed fix is ensemble: majority voting across multiple models
 - Telugu called out as once of the worst performers: 0.002 Cohen's Kappa...


## Alpaca - Stanford: https://crfm.stanford.edu/2023/03/13/alpaca.html

 - Fine-tune Meta's LLaMa 7B model to Alpaca. Used OpenAI API to generate instruction following examples from seeds.
 - LLaMa 7B was just text, didn't have instruction-tuning.


## Sentence-BERT / sentence-transformers: https://arxiv.org/abs/1908.10084

 - Why we use it: the back-translation filter needs a semantic-similarity score between the English seed and the back-translated generation. SBERT encodes each sentence to a fixed vector once, so similarity is a single cosine — O(1) per pair, runs locally, no extra teacher/judge API calls (matters under the 40/min NVIDIA cap).
 - Contrast with the obvious alternatives:
    - **BERTScore** does token-level greedy matching every comparison (no reusable sentence vector) and correlates with fluency more than with adequacy — heavier and less aligned with what we want to measure.
    - **spBLEU/ChrF** (the FLORES MT metrics) are surface n-gram overlap; back-translation paraphrases heavily, so lexical overlap punishes valid paraphrases. Embedding cosine is meaning-level, which is the right granularity for a consistency check.
 - SBERT vs. vanilla BERT: averaging BERT's token vectors gives sentence embeddings *worse* than GloVe for similarity; SBERT's siamese fine-tuning on NLI/STS is what makes cosine meaningful. So "use sentence-transformers" is a deliberate choice, not just "embed with a transformer."
 - Multilingual: Reimers & Gurevych (2020) distill a multilingual student so paraphrase-multilingual MiniLM/mpnet land translations and their source in a *shared* space — cross-lingual cosine is meaningful, which is exactly the back-translation setup (English seed vs. back-translated English, but also lets us sanity-check target-language pairs in one space). Models cover all four of our languages.
 - Practical: relative score only (we threshold against the gold set in Phase B, not an absolute cutoff); pick a paraphrase-multilingual model for speed, document the exact checkpoint for reproducibility.


## Back-translation model: dedicated MT (NLLB-200), NOT the teacher

Sources: NLLB Team (2022) https://arxiv.org/abs/2207.04672 ; IndicTrans2, Gala et al. (2023) https://arxiv.org/abs/2305.16307

 - The back-translation filter needs a model to render each generated target-language item back into English for the cosine-vs-seed check. The convenient choice is to reuse the teacher (Gemini) — and the original code did — but that is the wrong model for a *checker*, for two reasons:
    - **Independence.** If the same model both generates and back-translates, it marks its own homework: it can silently "read through" and repair its own errors, so the drift we want to detect never surfaces. This is the same circularity SPEC.md forbids for the judge ("same-model judging is methodologically weak").
    - **Literalness.** A dedicated MT translates what is on the page; an instruction-tuned LLM paraphrases and normalises ("Classify…"→"Rate…", quietly fixes tense/number slips). For generation that fluency is a feature; for a checker it is a bug that hides the exact flaws we probe for.
 - **Choice: NLLB-200 (`facebook/nllb-200-distilled-1.3B`).** Public, first-class `transformers` (no gated repo, no custom toolkit, loads on transformers v5), covers all four targets (hin_Deva, urd_Arab, tam_Taml, mal_Mlym → eng_Latn), and runs **locally** — no API, no quota, no lockouts, so the whole corpus scores in one pass. License CC-BY-NC, fine for an internal QC signal we do not redistribute.
 - **IndicTrans2 (AI4Bharat) preferred on paper** — SOTA for Indic, MIT — but its HF weights are gated and its toolkit lagged transformers v5; NLLB was the zero-friction choice and is more than adequate for a *relative*, calibrated signal. Revisit against the gold set if warranted.
 - **Validated by a discrimination probe** (`tools/probe_bt_discrimination.py`, N=16, 4/lang): cos(back-translation, own seed) mean **0.83** vs cos(back-translation, a random other seed) mean **0.06** — **+0.77** separation, **0/16** overlap. The signal cleanly separates faithful from mismatched generations, which is the only property that makes it worth keeping. NLLB's own translation noise (e.g. an "early"→"ago" slip on an otherwise-faithful item) is real but *independent* of generation error, which is why back-translation stays one of several decorrelated, score-only signals thresholded against the human gold set — never a standalone gate.
