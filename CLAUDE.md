# CLAUDE.md

## Project

**Buttery** — synthetic data generation pipeline for low-resource Indic languages (Hindi, Urdu, Tamil, Malayalam). 8-week internship deliverable; fine-tuning and a review platform are explicitly out of scope.

## Repo layout

```
syndata/              # Python package — all pipeline code goes here
  __init__.py
  data_structures.py  # Pydantic v2 schemas (SeedItem, SyntheticItem, QualityScore, …)
  seeds.py            # load/parse/filter SeedItems from seed JSON
  client.py           # ChatClient protocol; NvidiaClient (live) + MockClient (offline)
  templates.py        # prompt registry — translate vs. adapt-and-localize per task family
  generator.py        # SeedItem + GenerationConfig -> teacher call -> SyntheticItem
  cli.py              # `syndata generate` command

data/
  language_statistics.csv   # corpus sizes, benchmark coverage, scripts per language
  seeds/
    sample_data.json         # bootstrapping seeds + bad-generation examples
  generated/                 # JSONL generation output (created on first run)

docs/
  lit_review.md    # notes on Bactrian-X, MURI, UPDESH, Alpaca, LLM-as-judge papers
  sources.md       # academic citations (APA)

pyproject.toml     # deps + `syndata` console entry point
README.md          # install, API key, CLI usage, module map
SPEC.md            # project spec from manager
REQUIREMENTS.md    # formal requirements with checkboxes
TIMELINE.md        # week-by-week plan with exit criteria
DESIGN.md          # (to be written in Week 2) — answers the 5 methodology questions
```

## Stack

- Python 3.11+, Pydantic v2, HuggingFace `datasets`
- LLM access via `openai` SDK pointed at NVIDIA Build (`base_url=https://integrate.api.nvidia.com/v1`); key in `NVIDIA_API_KEY` (or `.env`). Free, rate-limited tier.
- Teacher LLM: **Qwen3-5-122b** via NVIDIA Build (OpenAI-compatible). Exact catalog id (likely namespaced, e.g. `qwen/qwen3-...`) still to be confirmed against the live model list — passed as a CLI value, no code change needed.
- Judge LLM: **Llama 3.3 70B** via NVIDIA Build (different model to avoid same-model bias)
- Target languages: `hi` (Hindi), `ur` (Urdu), `ta` (Tamil), `ml` (Malayalam)
- Use `--teacher mock` (offline `MockClient`) to exercise the full pipeline without a key or network.

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
- `METHODOLOGY.md` — 2,500–3,500 word paper-style writeup
- Quality filters in `syndata/filters/` (LLM-judge, language-ID gate, back-translation, structural) — Week 4+
- Test suite (`MockClient` is built to be the fixture)
- Jupyter notebook (exploratory analysis)
- 5-slide presentation PDF

## Done (Week 3 — pipeline skeleton)

- Generation pipeline in `syndata/`: seed loader, prompt templates, chat clients, generator, CLI
- `pyproject.toml` (deps + `syndata` entry point); `README.md` stub
- End-to-end verified with `MockClient`: CLI writes JSONL that round-trips through `SyntheticItem`
- Teacher responses requested as JSON; parser salvages fenced/preamble output and always keeps `raw_response`
- Still pending: first *live* run (needs `NVIDIA_API_KEY`); `--judge` is recorded but inert until Week 4
