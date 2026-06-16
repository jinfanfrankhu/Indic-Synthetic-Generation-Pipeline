# Requirements — Buttery Synthetic Data Pipeline

**Scope:** 8-week internship deliverable. Fine-tuning models and building a native-speaker review platform are explicitly out of scope.

---

## R1 — Pipeline Functional Requirements

### R1.1 — Generation
- [ ] Generate instruction-following, QA, classification, summarization, and translation data in target languages using a teacher LLM
- [ ] Support configurable teacher model, target language, task family, and N items via CLI
- [ ] CLI invocation: `syndata generate --language <lang> --task <task> --n <N> --teacher <model> --judge <model>`
- [ ] Output conforms to `SyntheticItem` Pydantic schema with full provenance (seed ID, model, timestamp, prompt template)

### R1.2 — Seed Management
- [ ] Load and parse seed items from the 5 task families (using `SeedItem` schema)
- [ ] Seed strategy must be documented and defended in `DESIGN.md`

### R1.3 — Quality Filters (minimum 3 required)
- [ ] **Structural validity filter:** task-specific format checks (answer present for QA, valid label for classification, length bounds, no truncation artifacts)
- [ ] **LLM-as-judge filter:** judge model scores each item on fluency, faithfulness, and format adherence; scores stored as `QualityScore`; uses a different model than the teacher
- [ ] **Back-translation consistency filter:** back-translate to English, compute semantic similarity vs. seed, reject below threshold
- [ ] **Language-ID gate:** drop items where model is <75% confident output is in target language (e.g., IndicLID)
- [ ] Filter chain is pluggable via `QualityFilter` protocol; filters can be toggled independently

### R1.4 — Languages & Scale
- [ ] All 4 target languages implemented: Hindi (hi), Urdu (ur), Tamil (ta), Malayalam (ml)
- [ ] Minimum 4 task families per language
- [ ] Target: 500+ post-filter items per language per task family at final generation run

### R1.5 — Native-Speaker Review Hook
- [ ] Pipeline exports flagged/sampled items in a human-reviewable format (e.g., CSV or JSON with source, generated, scores) even if no actual review is conducted

---

## R2 — Quality & Metrics Requirements

- [ ] Per-language, per-task filter retention rate logged and reported
- [ ] Per-language judge score distribution (mean, median, p10, p90) computed
- [ ] Per-language back-translation similarity distribution computed
- [ ] Manual spot-check of 20–30 items per language with documented error taxonomy
- [ ] Rejection threshold rationale documented in `DESIGN.md`

---

## R3 — Output Artifact Requirements

### R3.1 — GitHub Repository
- [ ] Public GitHub repo, MIT license
- [ ] Reproducible from `README.md` instructions
- [ ] Clean structure: no dead code, consistent naming

### R3.2 — HuggingFace Dataset
- [ ] At least one published dataset (minimum: one language, one task family)
- [ ] Target: all 4 languages, 4 task families
- [ ] License: CC-BY-SA 4.0
- [ ] Dataset card documents: generation methodology, teacher/judge models, filter chain, known limitations, failure mode examples, citation

### R3.3 — Documentation Files
- [ ] `README.md` — reproduction instructions, CLI reference, dataset links, citation
- [ ] `DESIGN.md` — answers all 5 design questions from SPEC.md (seed strategy, direct-gen vs. translate, filter aggressiveness, bias inheritance, evaluation approach)
- [ ] `METHODOLOGY.md` — 2,500–3,500 word paper-style writeup covering background, approach, results, limitations, future work; suitable for blog or arXiv
- [ ] `TIMELINE.md` — project plan (this exists)
- [ ] `REQUIREMENTS.md` — this file

### R3.4 — Jupyter Notebook
- [ ] Exploratory analysis notebook: score distributions, qualitative examples, cross-language comparison, failure mode analysis
- [ ] Runnable from scratch against published dataset

### R3.5 — Final Presentation
- [ ] 5-slide PDF deck (due 48h before Week 8 meeting)
- [ ] Slide structure: problem/motivation, approach, dataset overview, quality metrics, takeaways & future work

---

## R4 — Design Questions (must be answered in DESIGN.md)

1. **Seed strategy:** Curated seeds vs. translated public datasets vs. LLM meta-prompts — choice, rationale, and limitations
2. **Direct generation vs. translate-then-adapt:** Per task type, which approach and why
3. **Filter aggressiveness:** Rejection threshold decision — volume vs. quality trade-off, target precision/recall
4. **Bias inheritance:** How English-source bias is measured and (if possible) mitigated
5. **Evaluation without native speakers:** Surrogate signals used and their defensibility

---

## R5 — Stretch Goals (not required, pursue in Week 8 if ahead)

- Fine-tune Llama 3.2 1B or Phi-mini on synthetic data, measure benchmark delta vs. base
- Multi-teacher ensemble generation; compare quality metrics
- Adversarial filter: small classifier to distinguish synthetic from real native text
- arXiv preprint formatting pass on `METHODOLOGY.md`

---

## Deliverable Checklist (from SPEC.md)

- [ ] Public GitHub repo (MIT)
- [ ] Working CLI (`syndata generate ...`)
- [ ] Published HuggingFace dataset (≥1 language, ≥1 task family; target: 4×4)
- [ ] ≥4 task families implemented
- [ ] ≥3 quality filters implemented
- [ ] Per-language quality metrics documented
- [ ] `README.md` with reproduction instructions
- [ ] `DESIGN.md` with all 5 methodology decisions
- [ ] `METHODOLOGY.md` (2,500–3,500 words)
- [ ] Exploratory analysis Jupyter notebook
- [ ] 5-slide final presentation PDF
