# Project Spec — Synthetic Data Generation Pipeline for Low-Resource Languages

**Intern:** Jinfan "Frank" Hu
**Duration:** 8 weeks
**Stack:** Python 3.11+, Pydantic 2, HuggingFace `datasets`, NVIDIA Build (OpenAI-compatible LLM API)

---

## The Problem

Billions of people speak languages that current LLMs barely handle. Swahili, Tagalog, Yoruba, Quechua, Haitian Creole — these are well-studied in linguistics but underserved by foundation models because there's not enough training data in modern, instruction-tuned formats.

The standard academic move is to document the problem in a paper. The startup move is to actually generate the missing data. Synthetic data generation — using a strong LLM in a high-resource language as a teacher to produce instruction-tuned examples in low-resource languages — is now tractable, but the quality control and methodology are unsolved enough that there's real room to contribute.

## What You're Building

A standalone Python pipeline — call it whatever name you want — that:

1. **Generates** instruction-following / QA / classification / summarization data in your target low-resource languages, using strong LLMs as the source.
2. **Quality-filters** the generated data through multiple complementary signals — LLM-as-judge, back-translation consistency, structural validity, and native-speaker review hooks.
3. **Publishes** a clean, documented HuggingFace dataset that other researchers and practitioners can actually use.
4. **Documents** the methodology so the dataset is defensible as a research artifact, not just a dump.

End artifacts:
- Public GitHub repo (MIT license)
- One or more public HuggingFace datasets (with thoughtful licenses — CC-BY-SA 4.0 is reasonable for derivative datasets)
- A short methodology paper / blog post (~2,500–3,500 words) describing what you did, what worked, and what didn't
- A 5-slide final presentation

## Languages

You pick. Pick **3–5 languages** in Week 1 based on:

- Genuine personal interest (you'll be staring at the data for 8 weeks)
- Availability of high-quality reference material (Wikipedia, government corpora, Tatoeba, ALT corpus) — needed for back-translation and seed prompts
- LLM coverage on the source side (the teacher LLM needs to be at least competent in the language; check NVIDIA Build's model coverage)
- Existing benchmarks in the target language (FLORES-200, MASAKHANE benchmarks, XNLI) — needed for measuring whether your synthetic data actually moves the needle

Document the selection rationale in Week-1 scope doc.

## Pipeline Architecture (suggested — refine in Week 2)

```
┌────────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐    ┌────────┐
│ Seed tasks │ -> │  Generate  │ -> │ Multi-pass  │ -> │ Native-  │ -> │ HF     │
│ (English)  │    │  (LLM)     │    │ quality     │    │ speaker  │    │ publ.  │
└────────────┘    └────────────┘    │ filter      │    │ review   │    └────────┘
                                    └─────────────┘    │ hooks    │
                                                       └──────────┘
```

Quality filter passes you should at least implement:

- **LLM-as-judge** — strong model rates each generated item for linguistic fluency, semantic correctness, and task-format adherence
- **Back-translation consistency** — translate back to English and check semantic preservation against the seed
- **Structural validity** — task-specific format checks (e.g., for QA: is there an answer? for classification: is it one of the allowed labels?)
- **Optional: native-speaker review interface** — even if you can't find native speakers in 8 weeks, the pipeline should support exporting items in a reviewable format

## Data Model

See `syndata/data_structures.py`. Key Pydantic types:

- `SeedItem` — original English task/prompt/expected
- `GenerationConfig` — model, language, params, prompt template
- `SyntheticItem` — generated item in target language with provenance
- `QualityScore` — multi-axis assessment (fluency, faithfulness, format)
- `QualityFilter` (protocol) — pluggable filter contract
- `GenerationRun` — metadata about a generation session
- `DatasetMetadata` — for HF publication

## Sample Data

`data/seeds/sample_data.json` contains:

- ~15 English seed items demonstrating five task families: instruction-following, QA, classification, summarization, translation
- Example synthetic items in Swahili and Tagalog (machine-generated samples — treat as illustrative, not authoritative)
- A small set of "what bad generation looks like" examples to inform your quality filters

These are bootstrapping data. By Week 3 you'll be generating your own seed and synthetic items at scale.

## LLM Access

Same as Matt's project — NVIDIA Build, OpenAI-compatible, free.

Recommended teacher-model candidates:
- `meta/llama-3.3-70b-instruct` — strong multilingual, good default
- `qwen/qwen3-5-122b-a10b` — particularly strong in Asian languages (good if Tagalog is on your list)
- `deepseek-ai/deepseek-v4-pro` — strong reasoning, good for judge role
- `mistralai/mixtral-8x22b-instruct` — good European/African language coverage

Use one model as **teacher** (generates) and a different model as **judge** (rates). Same-model judging is methodologically weak.

## Design Questions to Answer

Document your reasoning in `DESIGN.md`:

1. **Seed strategy.** Curated seed prompts vs. translated public datasets vs. LLM-generated meta-prompts. Defend your choice and document the limitations.
2. **Direct generation vs. translate-then-adapt.** Generating directly in the target language vs. generating in English then translating. Each has failure modes — which is right per task type?
3. **Filter aggressiveness.** Reject 10% to keep volume high vs. reject 50% to keep quality high. Where's the trade-off for your use case? What's the recall/precision target?
4. **Bias inheritance.** Strong English-source models carry English-cultural biases into generated content. How do you measure this? Mitigate it?
5. **Evaluation.** How do you know your synthetic dataset is *good* without a panel of native speakers? Surrogate signals — readability, format validity, downstream eval improvement — what's defensible?

## Deliverable Checklist

By Week 8 you should have:

- [ ] Public GitHub repo (MIT)
- [ ] CLI: `syndata generate --language sw --task qa --n 500 --teacher meta/llama-3.3-70b-instruct --judge qwen/qwen3-5-122b-a10b`
- [ ] At least one published HuggingFace dataset (one language, one task family minimum — ideally more)
- [ ] At least 4 task families implemented (instruction, QA, classification, summarization)
- [ ] At least 3 quality filters implemented (LLM-judge, back-translation, structural)
- [ ] Per-language quality metrics: filter retention rate, judge score distribution, manual spot-check summary
- [ ] `README.md` with reproduction instructions
- [ ] `DESIGN.md` with methodology decisions
- [ ] `METHODOLOGY.md` — paper-style writeup (2,500–3,500 words) suitable for blog publication or arXiv submission
- [ ] Jupyter notebook with exploratory analysis of generated data
- [ ] 5-slide final presentation (PDF, due 48h before Week 8 meeting)

## Out of Scope

- Actually fine-tuning models on your synthetic data — that's a whole separate project. Generation + publication is the deliverable.
- Building a native-speaker review platform — just exporting in a reviewable format is enough.
- Languages requiring scripts not in standard Unicode (avoid headaches).

## Stretch Goals

- **Fine-tune a small model** (Llama 3.2 1B, Phi-mini) on your synthetic dataset and measure improvement vs. base on FLORES-200 or a language-specific benchmark.
- **Multi-teacher ensemble** — generate with two teachers, intersect on quality. Does diversity improve the dataset?
- **Adversarial filter** — train a small classifier to distinguish your synthetic data from real native text. Track this signal as a quality metric.
- **arXiv preprint** — the methodology writeup, formatted for arXiv submission. You'd be a published author at the end of the summer.

## Resources

- [NVIDIA Build (LLM endpoints)](https://build.nvidia.com)
- [HuggingFace datasets — publishing guide](https://huggingface.co/docs/datasets/upload_dataset)
- [MASAKHANE](https://www.masakhane.io) — African NLP community + benchmarks
- [FLORES-200](https://github.com/facebookresearch/flores) — Meta's 200-language translation benchmark
- [Tatoeba](https://tatoeba.org) — sentence pairs across 400+ languages
- [Aya dataset](https://huggingface.co/datasets/CohereForAI/aya_dataset) — Cohere's massive multilingual instruction dataset, useful reference for format
- [Self-Instruct paper](https://arxiv.org/abs/2212.10560) — foundational reference for LLM-generated instruction data
- [Alpaca paper](https://crfm.stanford.edu/2023/03/13/alpaca.html) — practical recipe for synthetic instruction tuning

## Notes for Frank specifically

- **You're the most senior intern in the cohort.** The PM template is calibrated for general engineering work; your project is closer to research-engineering. Your manager 1:1s can go deeper than ship/next/stuck — bring methodology questions, prior art, design trade-offs.
- **Don't skip Week 2.** "Research & Requirements" looks light, but for a research project, the literature review IS the work. Document what's been done (Self-Instruct, Aya, Bactrian-X, etc.), what worked, what didn't, and where the room to contribute is. The rest of the project is downstream of that doc.
- **Treat dataset publishing as a craft.** A poorly-documented HuggingFace dataset is worse than no dataset — it actively misleads users. Document license, generation methodology, known limitations, examples of failure modes. The dataset card is part of your deliverable.
- **The methodology writeup is not bonus.** Plan to write throughout, not at the end. The difference between a forgettable summer project and a publishable artifact is documentation quality.
