# DESIGN.md — Methodology Decisions

This document answers the five methodology questions the project spec (`SPEC.md`)
requires us to defend. It records *why* the pipeline is built the way it is; the
*how* lives in `README.md` and the code, and the long-form writeup is `METHODOLOGY.md`.

Status note (Week 4): decisions below are locked unless marked *provisional* or
*open*. Where a choice depends on the human gold set (not yet collected), the
threshold is deliberately deferred — see Q3 and Q5.

---

## Language selection (context for everything below)

Four South Asian languages, chosen as **two controlled comparison pairs** so the
dataset doubles as a small natural experiment:

- **Hindi (hi) / Urdu (ur)** — share a spoken standard (Hindustani) but diverge
  sharply in script (Devanagari vs. Nastaliq/Perso-Arabic). Isolates the effect of
  *writing system* on generation quality with the spoken language held roughly fixed.
- **Tamil (ta) / Malayalam (ml)** — both South Dravidian, similar in corpus size
  (CC-100 ~5.9 GB vs ~7.6 GB), but Tamil appears in GLUECoS/XNLI and Malayalam does
  not. A natural **benchmark-coverage gap** to fill.

All four are mid-resource (CC-100 5.9–20 GB): large enough that a teacher LLM is
competent, underserved enough that synthetic instruction data is a real
contribution. Combined speaker population exceeds 900M. Scripts occupy **disjoint**
Unicode blocks, which the language-ID gate exploits (Q3). See
`data/language_statistics.csv`.

---

## Q1 — Seed strategy

**Decision: curated English seeds, expanded by LLM self-instruct, with a mandatory
hand-review gate. English is the pivot language for all seeds.**

The three options the spec poses:

1. **Curated seed prompts** — hand-written, high quality, low volume, no licensing risk.
2. **Translated public datasets** (Alpaca, Dolly, Aya) — high volume, but inherits the
   source dataset's licensing, its biases, and its task distribution wholesale.
3. **LLM-generated meta-prompts** (Self-Instruct / Alpaca recipe) — high volume and
   diversity, but drifts toward the teacher's preferences and can collapse to
   near-duplicates without dedup.

We use **(1) seeded, then (3) expanded** and explicitly avoid (2) as the primary
source. A small curated set (`data/seeds/sample_data.json`, 29 seeds across six task
families) anchors the task distribution and format; `syndata bootstrap-seeds` then
runs Self-Instruct-style expansion (Wang et al. 2022) off those exemplars to reach
the diversity needed for scale, with structural pre-filters and a **hand-review gate
before any item is generated against the expanded pool** (CLAUDE.md). This is the
Alpaca recipe (Stanford 2023) adapted with a human checkpoint.

**Why English seeds rather than seeding in-language.** The teacher is strongest in
English, the four targets are mid-resource, and the back-translation consistency
filter (Q5) needs an English reference to compare against. Keeping the seed in
English gives every generated item a provenance anchor (`SyntheticItem.seed_id`) and
a fixed point for the faithfulness and back-translation checks.

**Limitations (documented honestly):**
- An English seed distribution bounds cultural coverage — it can only ask the
  questions an English author thought to ask. The bottom-up generation path (Q2)
  and the `bias` axis (Q4) are the partial mitigations.
- Self-instruct expansion biases toward the teacher's idea of a "typical" task and
  can under-sample the long tail. The hand-review gate and structural dedup are the
  guardrails; this is why we do not generate directly off raw bootstrap output.
- Why not translated public datasets: we would inherit another project's bias and
  license, and lose the clean English→target provenance the filters depend on. A
  translated-dataset arm is a reasonable future comparison, not the base method.

---

## Q2 — Direct generation vs. translate-then-adapt

**Decision: split by task type. Top-down translate-then-adapt for culture-agnostic
tasks; bottom-up reverse-instruction for culturally-grounded tasks.**

This follows UPDESH (Husain et al. 2025), whose central finding is that no single
generation strategy is right for all task families in Indic languages:

| Task family | Strategy | Template | Rationale |
|---|---|---|---|
| reasoning, QA, classification (culture-agnostic) | **Top-down**: translate the English seed and localize the answer | `direct_translate` | Meaning is language-invariant; the risk is fluency/script, which translation handles well. Mirrors Bactrian-X. |
| instruction, summarization (culturally grounded) | **Bottom-up**: reverse-instruction (MURI) — generate native content, then ask "what instruction would produce this?" | `adapt_and_localize` | Avoids "translationese" and English-centric framing; produces text a native writer would actually generate. |

**Why not direct generation everywhere.** Generating directly in the target language
for a reasoning task risks the teacher being subtly less reliable in a mid-resource
language than in English — and we lose the English reference the faithfulness and
back-translation filters need. For culture-agnostic tasks, translate-then-adapt keeps
the strong-English reasoning and pays only a translation cost the filters can verify.

**Why not translate everywhere.** Translation imports English framing (units, names,
idioms, examples) that is wrong for culturally-grounded generation — exactly the bias
Q4 is about. Reverse-instruction (MURI, Köksal et al. 2024) sidesteps this by starting
from native-plausible content.

The split is implemented in the prompt registry (`syndata/templates.py`,
`default_template_for`), so the strategy is selected per task family automatically.

**Open:** the teacher/judge bake-off so far covered QA only (the most culture-agnostic
task). A follow-up bake-off on `instruction`/`classification` under `adapt_and_localize`
would stress-test the bottom-up path before full-scale generation
(`docs/model_selection.md`).

---

## Q3 — Filter aggressiveness

**Decision: two-tier. Objective validity gates are strict from day one; subjective
quality scores run score-only (record, never drop) until calibrated against the human
gold set. Reject nothing on a guessed threshold.**

The word "filter" covers two different things, and only one of them is the
volume-vs-quality trade-off the spec is asking about
(`docs/gold_standard_protocol.md`):

- **Objective gates — strict immediately.** Structural validity (empty prompt,
  missing answer, scaffolding leak, truncation, UPDESH's >75%-repetition rule) and the
  language-ID gate. These are broken *regardless of taste*, and their thresholds are
  either spec-mandated (language-ID **0.75**, from UPDESH/IndicLID) or definitional
  (the repetition rule), not ours to invent. Rejecting these costs us nothing we want
  to keep.
- **Subjective scores — score-only until calibrated.** LLM-judge axes
  (fluency/faithfulness/bias) and back-translation cosine. **No defensible cutoff
  exists yet**, because per UPDESH human–LLM agreement on Indic linguistic
  plausibility is only ~50%. Inventing a threshold now *is* the over-aggression we are
  trying to avoid. These run through the chain, get a continuous `score` and an
  advisory `would_pass`, but **discard nothing** until thresholds are set against the
  gold set (Q5).

So the volume-vs-quality dial is, for now, deliberately **not turned**: we collect
score distributions first, then place thresholds where the human ROC curve says to
(target operating point via Youden's J), rather than picking 10%/50% blind. The
`FilterChain` is built for exactly this — it runs every filter and reports each
verdict without dropping (`syndata/filters/base.py`).

**Per-task filter design (a Week-4 finding).** A filter can be correct in general and
wrong for one task family. The whole-item language-ID gate flagged **100% of its
rejections as translation items** — *correct* translations, failed only because a
translation prompt embeds its English source sentence by design (e.g.
`"Translate into Hindi: 'Good morning.'"` is ~45% Latin letters). The script gate was
measuring the wrong text. **Resolution: the translation family is exempt from the
language-ID gate** (`LanguageIDFilter.exempt_tasks`, configurable); translation
quality is the job of the back-translation/faithfulness filters, which are the right
signal for it. The verdict trail still records the real script proportion for audit.
Retention on the 192-item Week-4 batch went from 89% → 100% with the exemption, with
the translation items now judged by the correct filter rather than rejected by the
wrong one. This is *less* aggressive in the right place, not a blanket loosening.

**Precision/recall target.** Because the objective gates are strict and the
subjective scores are not yet enforced, current "precision" against native judgement
is unmeasured by construction — that is the gold set's job. The intent is a
**high-precision** dataset (a published low-resource dataset that misleads is worse
than a smaller honest one — SPEC.md), accepting lower recall: we would rather drop a
borderline-good item than ship a bad one.

---

## Q4 — Bias inheritance

**Decision: measure English-source bias as a first-class quality axis (`bias` /
"cultural fit"); mitigate structurally via bottom-up generation for culturally-grounded
tasks. Treat the measurement as noisy and never a hard gate.**

Strong English teachers carry Western framing — names, units, idioms, examples,
assumptions — into generated text. We attack it on three fronts:

1. **Measurement (LLM judge).** The judge ensemble scores a `bias` axis: *is this free
   of unwanted English-source cultural framing?* (`QualityAxis.BIAS`).
2. **Measurement (human).** The gold-standard rubric rates the same axis as "Cultural
   fit" — *"does this feel written for [language] readers, or a foreign text wearing
   [language] clothes?"* (`docs/gold_standard_protocol.md`), with the English source
   shown so raters can spot what leaked through. Human–judge agreement on this axis is
   part of the Q5 reliability table.
3. **Mitigation (generation strategy).** Bottom-up reverse-instruction for
   culturally-grounded tasks (Q2) is the main structural mitigation: starting from
   native-plausible content imports less English framing than translating an English
   prompt does.

**Honest caveats:**
- The `bias` axis is the **noisiest** judge signal — inter-judge spread up to 0.80 in
  the discrimination probe (`docs/model_selection.md`). Judges interpret "cultural
  bias" inconsistently, so it is a **reported metric, never a rejection gate**. The
  human ratings are the real instrument; the LLM `bias` score is a weak proxy whose
  trustworthiness we are explicitly testing.
- We measure *surface* cultural fit, not deep representational bias. Detecting that,
  say, generated stories systematically center certain professions or genders is out
  of scope for an 8-week pipeline and flagged as future work.

---

## Q5 — Evaluation without native speakers

**Decision: a chain of decorrelated surrogate signals, calibrated against a small
human gold set that we *do* collect — not in place of human judgement, but to measure
how far each surrogate can be trusted.**

No native-speaker panel for the full dataset, so we lean on surrogates — but a surrogate
is only as good as its agreement with a human, so the design's core is *measuring that
agreement* on a sample:

**Surrogate signals (apply to all items):**
1. **Structural validity** — deterministic, ground-truth by construction.
2. **Language-ID gate** — script-proportion confidence; objective, catches the failure
   mode (English-left-in, code-switching) that actually occurs here. Exploits the
   disjoint-script property of our four targets.
3. **LLM-judge ensemble** — fluency/faithfulness/bias. Single cross-lingual judges are
   unreliable (~0.3 Fleiss' κ; Fu et al. 2025), so we use a **majority/mean across
   decorrelated, distinct-family models**. Probe (`docs/model_selection.md`) shows the
   panel discriminates finely on Tamil code-switching and disagrees on the hard cases —
   the precondition that justifies an ensemble. Provisional panel: **GLM-5.1 + Mistral
   Small 4 + Nemotron-3 Super** (Sarvam-m demoted for non-monotonic scoring but kept as
   the only Indic specialist).
4. **Back-translation consistency** — back-translate the generation to English with an
   **independent MT (NLLB-200), deliberately *not* the teacher** (same-model back-translation
   is circular and hides self-consistent errors; a dedicated MT is also more literal, so it
   exposes drift rather than smoothing it — see `docs/lit_review.md`), then cosine vs. the
   English seed via multilingual SBERT (Reimers & Gurevych 2019/2020). Embedding cosine over
   spBLEU/ChrF because back-translation paraphrases heavily and surface n-gram overlap punishes
   valid paraphrase; relative score, thresholded against the gold set, not an absolute cutoff.
   A discrimination probe (matched 0.83 vs mismatched 0.06 cosine, 0/16 overlap) confirms the
   signal separates faithful from mismatched generations. *(Implemented Week 5: `tools/score_backtranslation.py`.)*

**The calibration that makes the surrogates defensible.** We collect a human gold set —
**~80 items/language, ~20% double-rated, 60% normal + 40% judge-borderline**, blind to
model/score/stratum — rated on the same three axes on a 1–4 ordinal scale
(`docs/gold_standard_protocol.md`). The analysis then answers:

| Question | Method |
|---|---|
| Can the judge be trusted, per axis per language? | Spearman ρ + quadratic-weighted Cohen's κ (judge vs human) |
| Where do thresholds go? | Derive human accept/reject from axis scores, sweep judge/back-translation thresholds, pick operating point on the ROC (this is the evidence behind Q3) |
| Best achievable agreement? | Krippendorff's α among raters on overlap items = human–human ceiling |
| Does the ensemble beat a single judge? | Recompute per-axis agreement for each single model vs. the ensemble |

**Why this is defensible without a full native review:** every surrogate threshold is
either spec-mandated, definitional, or set from a *measured* human ROC — not asserted.
The gold set is small but stratified to cover the decision boundary, and its
double-rated subset bounds how good any automatic judge could possibly be. The honest
limit: ~80 items/language calibrates thresholds, it does not certify every one of
thousands of generated items — which is why the dataset card ships the retention
rates, score distributions, and known failure modes rather than a single "quality"
number.

**Out of scope (stretch):** the strongest evaluation — fine-tune a small model on the
synthetic data and measure a benchmark delta (FLORES-200/XNLI) — is explicitly out of
scope per SPEC.md and listed as a stretch goal.

---

## Cross-references

- Generation strategy split → `syndata/templates.py`
- Filter chain + per-task exemption → `syndata/filters/`, `docs/filter_retention_latest.md`
- Judge ensemble evidence → `docs/model_selection.md`, `docs/judge_probe_ta.md`
- Gold-set contract + rater rubric → `docs/gold_standard_protocol.md`
- Literature notes → `docs/lit_review.md`; citations → `docs/sources.md`
