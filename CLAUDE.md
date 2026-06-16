# CLAUDE.md

## Project

**Buttery** — synthetic data generation pipeline for low-resource Indic languages (Hindi, Urdu, Tamil, Malayalam). 8-week internship deliverable; fine-tuning and a review platform are explicitly out of scope.

## Repo layout

```
syndata/              # Python package — all pipeline code goes here
  __init__.py
  data_structures.py  # Pydantic v2 schemas (SeedItem, SyntheticItem, QualityScore, …)

data/
  language_statistics.csv   # corpus sizes, benchmark coverage, scripts per language
  seeds/
    sample_data.json         # bootstrapping seeds + bad-generation examples

docs/
  lit_review.md    # notes on Bactrian-X, MURI, UPDESH, Alpaca, LLM-as-judge papers
  sources.md       # academic citations (APA)

SPEC.md            # project spec from manager
REQUIREMENTS.md    # formal requirements with checkboxes
TIMELINE.md        # week-by-week plan with exit criteria
DESIGN.md          # (to be written in Week 2) — answers the 5 methodology questions
```

## Stack

- Python 3.11+, Pydantic v2, HuggingFace `datasets`
- Teacher LLM: **Qwen3-5-122b** via NVIDIA Build (OpenAI-compatible)
- Judge LLM: **Llama 3.3 70B** via NVIDIA Build (different model to avoid same-model bias)
- Target languages: `hi` (Hindi), `ur` (Urdu), `ta` (Tamil), `ml` (Malayalam)

## Key decisions already made

- Ensemble judging (majority vote across models) to address ~50% human–LLM agreement on Indic linguistic plausibility (per UPDESH)
- IndicLID language-ID gate: drop items where model is <75% confident output is in target language
- Generation strategy split by task type: top-down translation for reasoning/culture-agnostic tasks; bottom-up reverse-instruction (MURI approach) for culturally-grounded tasks
- API budget confirmed with manager

## CLI target

```
syndata generate --language hi --task qa --n 500 --teacher <model> --judge <model>
```

## What still needs to be written

- `DESIGN.md` — 5 methodology decisions (seed strategy, direct-gen vs. translate, filter aggressiveness, bias, evaluation)
- `README.md` — reproduction instructions, CLI reference, dataset links
- `METHODOLOGY.md` — 2,500–3,500 word paper-style writeup
- Pipeline code in `syndata/` (generator, filters, seed loader, CLI)
- Jupyter notebook (exploratory analysis)
- 5-slide presentation PDF
