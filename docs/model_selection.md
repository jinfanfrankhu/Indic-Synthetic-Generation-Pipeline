# Model Selection

Teacher and judge models are drawn from NVIDIA Build's free hosted endpoints (OpenAI-compatible, no self-hosting). Selection optimizes for two axes that matter for this project: **Indic/multilingual quality** (not recency or coding-benchmark strength, which dominate most model marketing) and **teacher≠judge family diversity**, required by the ensemble-judging decision that addresses the ~50% human–LLM agreement on Indic linguistic plausibility reported in UPDESH. The candidate pool was filtered by *model type* first: only general-purpose chat LLMs can serve as teacher or judge, which rules out NVIDIA's safety classifiers and rerankers despite their "free endpoint" availability. The three chat LLMs below went into a small bake-off (same hi/ta QA seeds through each, run via `syndata compare`), and the decision below follows from that evidence.

## Decision (from the bake-off)

Reports: [`model_comparison_hi_qa.md`](model_comparison_hi_qa.md), [`model_comparison_ta_qa.md`](model_comparison_ta_qa.md).

 - **Teacher → DeepSeek V4 Flash** (`deepseek-ai/deepseek-v4-flash`). Fastest by far (~1–3 s/item vs ~10–20 s for Sarvam, vs Qwen timing out), clean JSON every call, and fully fluent in both Hindi and Tamil — including unprompted localization of answers into the target script (e.g. `ब्रासीलिया`, `பிரசிலியா`). The practical winner for generating thousands of items.
 - **Judge → an ensemble (see [Judging](#judging) below).** Not a single model: per UPDESH / the LLM-as-judge literature, cross-lingual judges are individually unreliable (~0.3 Fleiss' κ), and majority voting across *decorrelated* models is the proposed remedy.
 - **Qwen3.5-122b — dropped.** Although it produced correct Hindi on a single warm call, it repeatedly timed out under the bake-off's concurrent load (one run hung for ~1 h without honoring the request timeout). At 122B it is too slow and unreliable to be a practical teacher at scale.

Caveat: the bake-off covered QA only — the most culture-agnostic task, where Sarvam's specialization is least likely to show. A follow-up `instruction`/`classification` bake-off (bottom-up `adapt_and_localize`) would further stress-test the teacher choice before full-scale generation.

## Judging

Report: [`judge_probe_ta.md`](judge_probe_ta.md). Harness: `syndata judge-compare`; probe: `scripts/probe_judge_discrimination.py`.

The teacher (DeepSeek) is **excluded** from judging — a model grades its own output too kindly (self-preference). The judge ensemble draws only from *other* families. The candidate pool (respond on the free tier, parse cleanly, and zero-out an English-text control on both hi and ta): **Sarvam-m, Mistral Small 4, GLM-5.1, Nemotron-3 Super**. Qwen times out; Gemma-4-31b's endpoint is non-responsive.

**Discrimination probe (Tamil, graded code-switching).** The English-vs-Tamil control only tests the trivial case, so we judged the *same* Tamil question at known quality tiers — clean → 1 English word → heavy code-switch → full English — giving ground-truth ordering. Fluency scores:

| tier (known quality) | Sarvam | Mistral | GLM | Nemotron |
| --- | --- | --- | --- | --- |
| clean (best) | 0.90 | 1.00 | 1.00 | 0.90 |
| code-switch ×1 | 0.50 | 0.30 | 0.50 | 0.20 |
| code-switch heavy | **0.60** | 0.00 | 0.20 | 0.00 |
| English (worst) | 0.00 | 0.00 | 0.00 | 0.00 |

Findings:
 - **The judges discriminate finely** — fluency grades down smoothly (catching even one stray English word), not a 1.0→0.0 cliff. The earlier worry that they're blind to subtle Tamil flaws is *refuted* for code-switching.
 - **Their errors are decorrelated** — real spread on the ambiguous tiers (up to 0.60 on heavy code-switch). This is the precondition that *justifies* an ensemble: they agree on clear cases, diverge on hard ones.
 - **The a-priori favorite is the weakest judge.** Sarvam scored the heavy code-switch (three English words) at 0.60 fluency — *higher* than the milder 1-word version (0.50), i.e. **non-monotonic**. The Indic specialist is the *least* reliable at catching Tamil code-switching; the generalists (Mistral, Nemotron) correctly tank it to 0.00, and **GLM gives a perfect monotonic gradient**.
 - **The `bias` axis is noisy** (inter-judge spread up to 0.80) — judges interpret it inconsistently; it should not be a hard gate.

**Provisional panel: GLM-5.1 + Mistral Small 4 + Nemotron-3 Super** — three monotonic, decorrelated, distinct-family discriminators. Sarvam-m is **demoted, not deleted**: weakest on code-switching here, but this probe doesn't test subtle grammar or cultural grounding where its Indic training may still pay off, and it's the only Indic-specialist in the pool.

Caveats / still open:
 - **One item, one failure mode.** Robust weights need more items and other modes (mistranslation, wrong answer, dropped detail).
 - **No human ground truth for absolute quality** — the probe has ordering ground truth (we constructed the tiers) but not native-speaker calibration. Final ensemble weights should come from a small human-labelled gold set (κ vs humans, per language).
 - Code-switching is *also* caught deterministically by the planned **IndicLID language-ID gate**, so a judge's leniency there is backstopped; the judge's real value is subtler fluency/faithfulness the gate can't see.

## Candidates (general chat LLMs)

 - **Qwen3.5-122b-a10b** (`qwen/qwen3.5-122b-a10b`) — current baseline, already wired and producing correct Hindi. 122B MoE / 10B active; one of the strongest open families for Asian-language coverage. https://build.nvidia.com/qwen/qwen3.5-122b-a10b
 - **Sarvam** (3B / 30B / 100B sovereign family) — purpose-built for Indian languages by Sarvam AI, trained with NVIDIA on H100s; supports 22 Indian languages + English, math, and code, with a custom tokenizer up to ~4× more efficient on Indic text. Covers all four targets (hi/ur/ta/ml). The strongest a-priori fit for this project. https://www.sarvam.ai/models · https://www.sarvam.ai/blogs/sarvam-30b-105b
 - **DeepSeek V4 Flash** — capable generalist MoE from a different family than Qwen, so it preserves the bias-avoidance rule; strong judge candidate. Indic quality unverified (coding/agent-marketed), hence in the bake-off rather than assumed. https://build.nvidia.com/deepseek-ai

## Ruled out (wrong model type, not wrong quality)

 - **Nemotron 3.5 Content Safety** / **Llama 3.1 Nemotron Safety Guard 8B** — content-*moderation* classifiers over NVIDIA's 13-category Aegis taxonomy; they output safe/unsafe labels, not fluency/faithfulness/format scores, so they cannot serve as the quality judge. Nemotron 3.5 (Gemma-3-4B base, multilingual across 12 languages, ~97% harmful-content accuracy) is, however, a viable *optional safety-filter pass* in Week 4+. https://huggingface.co/blog/nvidia/nemotron-3-5-content-safety · https://docs.nvidia.com/nim/llama-3-1-nemotron-safety-guard-8b/latest/index.html
 - **rerank-qa-mistral-4b** — a cross-encoder reranker for RAG (relevance logit, 503-token limit, `/ranking` endpoint, not chat). Cannot generate text and does not fit the `ChatClient` interface. https://build.nvidia.com/nvidia/nv-rerankqa-mistral-4b-v3/modelcard
 - **Mistral Large 3 675B** — capable but Mistral historically trails the Qwen/Sarvam tier on Indic scripts; large and slow for marginal multilingual benefit. Deprioritized unless the bake-off contradicts this.
