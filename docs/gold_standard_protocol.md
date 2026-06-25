# Gold-Standard Rating Protocol

How we collect human ratings to (a) measure whether our LLM-judge ensemble can be
trusted on Indic languages, and (b) calibrate rejection thresholds against real
ground truth. This is the linchpin of the Week 4 quality work: per UPDESH, human–LLM
agreement on Indic linguistic plausibility is only ~50%, so every threshold we set is
indefensible until we have a human reference to check it against.

This doc pins the data contract and the rating rubric *before* any UI is built. The
schema matters more than the framework — a Next.js page, an Airtable, or a Google Form
could all collect the same records.


---

## Decisions locked

| Decision | Choice | Rationale |
|---|---|---|
| Axes rated | **fluency, faithfulness, bias** | Mirror the judge ensemble (locked Week 4) so we can compute per-axis agreement. Format/correctness are handled deterministically and are not rated by humans. |
| Scale | **1–4 ordinal, no midpoint** | Forces a good/bad lean; kills central-tendency pile-up. Fine-grained (1–10/1–100) scales have poor inter-rater reliability — that disagreement is noise. |
| Ground-truth accept/reject | **Derived from the axis scores**, not asked directly | Keeps rater burden to three judgements; the keep/drop label for threshold calibration is computed from the ordinal scores (see Analysis). |
| Set size | **~80 items / language**, ~20% double-rated | Enough for κ with a usable confidence interval; overlap gives a human–human ceiling. |
| Stratification | **~60% normal sample, ~40% judge-borderline** | The borderline items (near the judge's score median) force coverage of the decision boundary, where agreement matters most. A seeded "known-bad" stratum was considered and dropped — we have no in-language bad examples and don't want to manufacture failure modes that may not occur naturally. |
| Blindness | Raters never see model names, judge scores, or stratum | Prevents anchoring. Enforced by splitting bundle (blind) from manifest (private). |
| Export | Separate `syndata export-gold` CLI step | Keeps generation clean; lets us re-sample the gold set without regenerating. |
| Packaging | One bundle for all 4 languages; app filters by `language` | Simpler to version than per-language files. |

---

## Two kinds of filter — and what we don't filter yet

The word "filter" covers two different things; only one of them is the "don't be
aggressive" one (DESIGN.md Q3).

- **Objective validity gates** (structural, language-ID): broken regardless of taste —
  empty prompt, missing answer, English-left-in / wrong script, scaffolding leak,
  degenerate repetition. Thresholds are spec-mandated (language-ID 0.75) or definitional
  (UPDESH's >75% repetition rule), not ours to guess, so these are strict from day one.
- **Subjective quality scores** (LLM judge: fluency/faithfulness/bias; back-translation
  similarity): no defensible cutoff exists yet. These run **score-only** — recorded,
  never enforced — until calibrated against this gold set (Phase B). Inventing a
  threshold now is the over-aggression we're avoiding.

Everything runs score-only regardless: the chain records `would_pass` and keeps each
filter's continuous `score`, but discards nothing. The boolean is advisory; the
threshold is movable.

**Gold-set non-contamination rule:** never pre-filter the human rating set by the
*subjective* scores. Showing raters only items the judge already liked hides exactly the
judge–human disagreements we're trying to measure. The borderline stratum *uses* judge
scores only to *select* boundary items, never to exclude. Pre-filtering by the
*objective* gates is fine (don't pay a rater to score English-left-in garbage) — and a
few such failures can double as attention-checks against rubber-stamping.

## The three axes — plain-language rater instructions

Reviewers are native speakers, not NLP researchers. The rater UI/guidelines must use
these plain-language framings, **not** the internal jargon. Internal keys
(`fluency`/`faithfulness`/`bias`) map 1:1 to the `QualityAxis` enum for the analysis join.

The single most important instruction to give every rater up front:

> **These three questions are independent. A sentence can read beautifully and still mean
> the wrong thing. Please judge each question on its own.**

### 1. Naturalness  (internal key: `fluency`) — *source not shown*

> **"Does this read like something a real, educated native speaker would write?"**
> Ignore the English original (you won't see it here). Judge only the [language] text:
> grammar, word choice, and whether it sounds natural — not translated, not robotic.

- **1** — Ungrammatical or clearly not written by a native speaker.
- **2** — Understandable, but awkward or stilted ("translationese").
- **3** — Natural, with only minor slips.
- **4** — Indistinguishable from a fluent native writer.

### 2. Meaning match  (internal key: `faithfulness`) — *English source shown*

Faithfulness is the axis most likely to confuse raters, so it gets the most explicit
framing. The trap is conflating it with the other two axes. State the boundaries directly:

> **"Does the [language] version ask for — or say — the same thing as the English original
> shown above it?"**
>
> You are comparing **meaning only**. Specifically:
> - **Do NOT** judge whether the [language] is good or natural — that is the previous
>   question (Naturalness).
> - **Do NOT** judge whether any *answer* is factually correct — a faithful translation of
>   a wrong question is still a faithful translation.
> - **DO** check: same task, same details, nothing added, nothing dropped, nothing changed.

Worked contrast (give raters at least one in their language):

> English: *"List three causes of the French Revolution."*
> - Faithful (4): [language for] "List three causes of the French Revolution."
> - Drifted (2): [language for] "Describe the French Revolution." — same topic, **different task**.
> - Unfaithful (1): [language for] "List three causes of the American Revolution." — detail changed.

- **1** — Different meaning, contradicts, or unrelated to the English.
- **2** — Same topic but the task or key details changed (partial meaning loss).
- **3** — Same meaning with minor drift.
- **4** — Fully preserves the English intent; nothing added or lost.

### 3. Cultural fit  (internal key: `bias`) — *English source shown*

> **"Does this feel like it was written for [language]-speaking readers, or like a foreign
> text wearing [language] clothes?"**
> Look for English/Western assumptions left in by accident — names, examples, units,
> idioms, or framing that a [language]-speaking writer wouldn't naturally use.

- **1** — Imposes English/Western framing; clearly foreign.
- **2** — Noticeably foreign in places.
- **3** — Mostly appropriate.
- **4** — Culturally natural for a [language]-speaking audience.


---

## File 1 — `rater_bundle.json`  (served to the app; blind)

```json
{
  "bundle_id": "gold-2026-06-26-all",
  "created_at": "2026-06-26T10:00:00Z",
  "instructions_version": "v1",
  "rating_schema": {
    "axes": [
      {"key": "fluency",      "label": "Naturalness",  "scale": [1, 4], "needs_source": false},
      {"key": "faithfulness", "label": "Meaning match", "scale": [1, 4], "needs_source": true},
      {"key": "bias",         "label": "Cultural fit",  "scale": [1, 4], "needs_source": true}
    ],
    "optional": ["unsure", "comment"]
  },
  "items": [
    {
      "task_id": "hi-qa-000142",
      "language": "hi",
      "task_family": "qa",
      "source_prompt": "What is the capital of France?",
      "source_expected": "Paris",
      "generated_prompt": "फ़्रांस की राजधानी क्या है?",
      "generated_expected": "पेरिस",
      "show_source": true
    }
  ]
}
```

- `task_id` **is** `SyntheticItem.id` — the join key back to the generation and its judge score.
- `source_*` fields are displayed only when the focused axis has `needs_source: true`
  (Meaning match, Cultural fit). Naturalness hides the source.
- No model names, no scores, no stratum. Anything that could anchor a rater lives in File 2.

## File 2 — `assignment_manifest.json`  (private; never sent to the app)

```json
{
  "bundle_id": "gold-2026-06-26-all",
  "assignments": [
    {"task_id": "hi-qa-000142", "raters": ["r_anita", "r_dev"],
     "overlap": true, "stratum": "known_bad"}
  ],
  "provenance": {
    "hi-qa-000142": {
      "teacher_model": "deepseek-ai/deepseek-v4-flash",
      "judge_scores": {"fluency": 0.4, "faithfulness": 0.9, "bias": 0.7},
      "judge_model_ensemble": ["sarvamai/sarvam-m", "z-ai/glm-5.1"],
      "back_translation_cos": 0.81
    }
  }
}
```

- `overlap: true` marks the ~20% double-rated items → human–human agreement ceiling.
- `stratum` (`normal` | `borderline`) confirms the set spans the boundary. `borderline`
  items are selected near the judge's score median, so the judge must have run in
  score-only mode before a bundle can be assembled (we use its scores only to *select*
  boundary items, never as ground truth).

## File 3 — `ratings.jsonl`  (returned; one record per rater × item)

```json
{"task_id": "hi-qa-000142", "rater_id": "r_anita", "language": "hi",
 "fluency": 2, "faithfulness": 4, "bias": 3,
 "unsure": false, "comment": "translationese phrasing",
 "instructions_version": "v1",
 "started_at": "2026-06-27T14:03:11Z", "submitted_at": "2026-06-27T14:03:48Z"}
```

- `started_at`/`submitted_at` are QC signals — implausibly fast submissions flag a
  rubber-stamping rater whose records we drop.
- `instructions_version` lets us discard ratings collected under a superseded rubric.

---

## Analysis (the join, and what each metric answers)

`ratings.jsonl` ⨝ `assignment_manifest.provenance` on `task_id`:

| Question | Method |
|---|---|
| Can the judge be trusted, per axis per language? | **Spearman ρ** (human 1–4 ordinal vs. judge 0–1 continuous, no binning) and **quadratic-weighted Cohen's κ** (judge binned to 4; QWK penalizes far-off disagreement — standard for ordinal). Headline reliability table. |
| Where do we set the rejection thresholds? | Derive a per-item human accept/reject from the axis scores (e.g. reject if **any** axis ≤ 2; sensitivity-check the rule). Treat that as ground truth, sweep judge / back-translation thresholds, plot **ROC**, pick the operating point (e.g. Youden's J). This is the evidence behind DESIGN.md Q3. |
| What's the best agreement we could hope for? | **Krippendorff's α / Fleiss' κ** among raters on the `overlap` items = human–human ceiling. Judge–human κ approaching this means the judge is "as good as a person." |
| Does the ensemble beat a single judge? | Recompute the per-axis agreement using (a) each single model and (b) the ensemble vote; compare. |

---
