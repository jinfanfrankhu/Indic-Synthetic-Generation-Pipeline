
Language Selection

I selected four South Asian languages as two controlled comparison pairs: Hindi/Urdu and Tamil/Malayalam. Hindi and Urdu share a spoken standard (Hindustani) but diverge sharply in script (Devanagari vs. Nastaliq) which isolates the effect of writing system on generation quality. Tamil and Malayalam are both South Dravidian and similar in size by CC-100 corpus (~5.9 GB and ~7.6 GB compressed), but Tamil appears in GLUECoS and XNLI while Malayalam does not, which creates a natural benchmark gap to fill. All four fall in the mid-resource range (CC-100: 5.9--20 GB), which means they're large enough for teacher LLMs to handle competently, but underserved enough that synthetic instruction data is a real contribution. Combined speaker population exceeds 900M.

Considerations Going Forward

The central design question from the lit review is judge reliability. UPDESH found only ~50% human--LLM agreement on linguistic plausibility for Indic languages, which means the quality filter will carry a lot of uncertainty on Tamil and Malayalam fluency judgments. To address this, I'll use ensemble judging (majority vote across models) rather than a single judge model, and supplement with the IndicLID language-ID filter (dropping outputs where the model is less than 75% confident the output is in the target language). On the generation side, the same UPDESH finding suggests splitting by task type: top-down translation from English for reasoning and culture-agnostic tasks, and bottom-up reverse-instruction generation (the MURI approach) for tasks that require cultural grounding. Teacher model will be Qwen3; judge will be Llama 3.3 70B, a different architecture to avoid same-model judging bias.

data/language_statistics.csv contains some quick facts that are relevant about each of the languages.
docs/sources.md includes some sources I used.
docs/lit_review.md includes some notes on some papers I read.

## Week 1: Foundation 
*June 1–7*

First meetings

---

## Week 2: Design & Decisions 
*June 8–14- Language selection (Hindi, Urdu, Tamil, Malayalam) with rationale

- `data/language_statistics.csv`: corpus sizes, benchmark coverage, scripts
- `docs/sources.md`: academic citations
- Literature review (`docs/lit_review.md`): Bactrian-X, MURI, UPDESH, Alpaca, LLM-as-judge reliability
- Write `DESIGN.md`: language rationale, seed strategy, direct-gen vs. translate-then-adapt, filter aggressiveness, bias, evaluation signals
- Finalize teacher/judge model choice (Qwen3-5-122b teacher, Llama-3.3-70b judge; upgrade to Gemini if budget approved)
- Confirm API budget with manager (DONE)
- Review `syndata/data_structures.py` and `data/seeds/sample_data.json`: understand the scaffolding

**Exit criteria:** `DESIGN.md` written, models locked, scaffolding understood.

---

## Week 3: Pipeline Skeleton
*June 15–21*

- Implement generator module: takes `SeedItem` + `GenerationConfig`, calls teacher LLM, returns `SyntheticItem`
- Implement seed loader: load/parse the 5 task families (instruction, QA, classification, summarization, translation) from seed files
- Wire up CLI: `syndata generate --language hi --task qa --n 50 --teacher ... --judge ...`
- Run first end-to-end generation (small batch, any one language), confirm output shape matches `SyntheticItem` schema
- Write basic `README.md` stub

**Exit criteria:** CLI runs, generates real output, data saved to disk in valid schema.

---

## Week 4: Quality Filters Pass 1
*June 22–28*

- Implement structural validity filter: task-specific format checks (answer present for QA, valid label for classification, length bounds, etc.)
- Implement LLM-as-judge filter: call judge model per item, score on fluency / faithfulness / format adherence; store as `QualityScore`
- Implement language-ID gate (IndicLID or langdetect): drop items where model isn't ≥75% confident in target language
- Filter by back-translation to English to judge accuracy
- Define and tune rejection thresholds; log filter retention rates per pass
- Generate mid-scale batch (100–200 items per language) and run both filters

**Exit criteria:** 3 filter passes running, per-language retention rates logged, batch survives the full filter chain.

---

## Week 5: Back-Translation + Scale Generation
*June 29–July 5*

- Implement back-translation consistency filter: translate generated item back to English, compute semantic similarity vs. seed (BERTScore or cosine on embeddings), drop below threshold
- Generate at scale: all 4 languages × 4 task families (target 500+ items per language per task family)
- Run full filter chain on all generated data; log per-language, per-task retention + score distributions
- Start drafting `METHODOLOGY.md` (write while the pipeline decisions are fresh)

**Exit criteria:** Full-scale generation complete, all 3+ filters applied, retention metrics logged, methodology draft begun.

---

## Week 6: Evaluation & Dataset Curation
*July 6–12*

- Manual spot-check: sample 20–30 items per language, document error taxonomy (hallucination, wrong language, format failures, cultural oddities)
- Compute per-language quality metrics: judge score distribution, filter retention rate, back-translation similarity distribution
- Curate final dataset: apply final thresholds, deduplicate, format for HuggingFace `datasets`
- Write dataset card (license, methodology summary, known limitations, failure mode examples)
- Publish draft HuggingFace dataset (private or gated initially)

**Exit criteria:** Dataset card written, dataset published privately on HuggingFace, quality metrics documented.

---

## Week 7: Documentation & Writeup
*July 13–19*

- Complete `METHODOLOGY.md` (2,500–3,500 words): background, language/model selection, pipeline architecture, filter design, evaluation, limitations, future work
- Finalize `DESIGN.md`: fill in anything deferred from Week 2
- Complete `README.md`: reproduction instructions, CLI usage, dataset links, citation
- Jupyter notebook: exploratory analysis of generated data (score distributions, examples, failure modes, cross-language comparison)
- Make HuggingFace dataset public (CC-BY-SA 4.0)

**Exit criteria:** All prose docs complete, dataset public, notebook runnable from scratch.

---

## Week 8: Polish & Present
*July 20–26*

- Final repo cleanup: consistent naming, remove dead code, docstrings on public interfaces
- 5-slide presentation (PDF due 48h before Week 8 meeting): problem, approach, data overview, quality metrics, takeaways/future work
- Stretch (if time): arXiv formatting pass on `METHODOLOGY.md`; or run fine-tune experiment on Llama 3.2 1B to show downstream improvement
- Final 1:1 with manager: walkthrough of dataset, pipeline, and writeup

**Exit criteria:** Presentation delivered, GitHub repo public, HuggingFace dataset public, all deliverables checked off.

---
