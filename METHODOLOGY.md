# Buttery: Synthetic Instruction Data for Low-Resource Indic Languages

*Methodology writeup — draft. Target 2,500–3,500 words. Sections marked
`<!-- TODO -->` are filled incrementally by the weekend automated runs once the
back-translation scoring they depend on is complete; do not fabricate results.*

## 1. Introduction

Billions of people speak languages that today's large language models handle only
weakly, not because the languages are intrinsically hard but because there is little
instruction-tuned data in them. Buttery is an eight-week effort to *generate* that
missing data rather than merely document its absence: it uses a strong teacher LLM to
produce instruction-following, QA, classification, summarization, reasoning, and
translation examples in four South Asian languages — Hindi (`hi`), Urdu (`ur`), Tamil
(`ta`), and Malayalam (`ml`) — and then subjects every generated item to a chain of
complementary quality signals before anything is published. The contribution is not a
new model; it is a defensible *method* for producing and vetting synthetic
low-resource data, and a documented dataset that other practitioners can trust.

The central difficulty is quality control without native-speaker review at scale. Prior
work (UPDESH) reports only ~50% human–LLM agreement on Indic linguistic plausibility, so
a single automated judge cannot be trusted as ground truth. Our response is to lean on
several *decorrelated* surrogate signals — structural validity, script/language-ID,
an ensemble LLM judge, and back-translation consistency — and to calibrate them against
a small human gold set rather than asserting thresholds. This writeup describes the
language and model choices, the generation strategy, the filter design, and what the
surrogate signals do and do not tell us.

## 2. Background and related work

Buttery builds on a now-standard recipe for synthetic instruction data. Self-Instruct
(Wang et al. 2022) and Alpaca (Stanford 2023) established LLM-driven expansion of a small
seed set into a large, diverse instruction pool. Bactrian-X applied the translate-then-
generate idea multilingually; MURI (Köksal et al. 2024) introduced *reverse instruction*
— generating native content first and then the instruction that would produce it — to
avoid the "translationese" that afflicts culturally grounded tasks. UPDESH (Husain et al.
2025) is the closest prior art for Indic specifically, and its two findings shape our
design: (i) no single generation strategy is right for every task family, and (ii)
cross-lingual LLM-as-judge reliability is low, motivating ensembles and human calibration.

<!-- TODO: expand related work with the LLM-as-judge reliability literature (Fu et al. 2025) and how our ensemble + gold-set calibration differs. ~200 words. -->

## 3. Language selection

The four targets were chosen as **two controlled comparison pairs**, so the dataset
doubles as a small natural experiment rather than an arbitrary set:

- **Hindi / Urdu** share a spoken standard (Hindustani) but diverge sharply in script
  (Devanagari vs. Nastaliq/Perso-Arabic). Holding the spoken language roughly fixed while
  varying the writing system isolates the effect of *script* on generation quality.
- **Tamil / Malayalam** are both South Dravidian and comparable in corpus size (CC-100
  ~5.9 GB vs. ~7.6 GB), but Tamil appears in GLUECoS/XNLI while Malayalam does not — a
  natural **benchmark-coverage gap** to fill.

All four are mid-resource (CC-100 5.9–20 GB): large enough that a strong teacher is
competent, underserved enough that synthetic instruction data is a real contribution.
Their scripts occupy **disjoint Unicode blocks**, a property the language-ID filter
exploits directly. Combined first-language population exceeds 900M.

## 4. Teacher and judge model selection

The teacher is **Gemini 3.1 Flash Lite**, selected from a Hindi QA bake-off for clean
JSON adherence, ~1s/item latency, fluent localized output, and — decisively — an
operable free-tier quota (500 requests/day) after NVIDIA Build's free tier proved
unusable for batch work (multi-hour per-model 429 lockouts). DeepSeek V4 Flash is the
documented fallback. The judge role is deliberately assigned to *different* model
families than the teacher, since same-model judging is methodologically weak; the
provisional ensemble is GLM-5.1 + Mistral Small 4 + Nemotron-3 Super, with an Indic
specialist (Sarvam-m) retained as a minority voice.

<!-- TODO: pipeline architecture — seeds -> templates -> generator -> filter chain, with the data_structures schema and provenance model. ~300 words. -->

## 5. Generation strategy

<!-- TODO: the split by task family (top-down translate for culture-agnostic; bottom-up reverse-instruction for culturally grounded), why, and the translation-task template fix that eliminated the ~36% empty/echo defect. ~350 words. -->

## 6. Quality filter design

<!-- TODO: the two-tier philosophy (strict objective gates; score-only subjective signals until calibrated), each of the four filters, and the per-task language-ID exemption for translation. ~400 words. -->

## 7. Evaluation and results

<!-- TODO: fill ONLY from real audit output — structural retention, back-translation cosine distribution overall and per language/task, and what the low-cosine tail looks like. Do not invent numbers. ~400 words. -->

## 8. Limitations

<!-- TODO: English-seed cultural bounding, unmeasured judge quality without the gold set, small calibration sample, no downstream fine-tune eval. ~250 words. -->

## 9. Future work

<!-- TODO: gold-set calibration, seed-pool expansion for genuine scale, in-language seed arm, downstream benchmark delta. ~150 words. -->
