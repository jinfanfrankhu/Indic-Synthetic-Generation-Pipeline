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
  compare.py          # model bake-off: same seeds through N models -> Markdown report
  cli.py              # `syndata generate` + `syndata compare`

data/
  language_statistics.csv   # corpus sizes, benchmark coverage, scripts per language
  seeds/
    sample_data.json         # bootstrapping seeds + bad-generation examples
  generated/                 # JSONL output: <lang>/<task>/<model>_<timestamp>.jsonl (gitignored)

docs/
  lit_review.md          # notes on Bactrian-X, MURI, UPDESH, Alpaca, LLM-as-judge papers
  sources.md             # academic citations (APA)
  model_selection.md     # teacher/judge model rationale + ruled-out models
  model_comparison_*.md  # bake-off reports (committed as model-choice evidence)

pyproject.toml     # deps + `syndata` console entry point
README.md          # install, API key, CLI usage, module map
SPEC.md            # project spec from manager
REQUIREMENTS.md    # formal requirements with checkboxes
TIMELINE.md        # week-by-week plan with exit criteria
DESIGN.md          # (to be written in Week 2) — answers the 5 methodology questions
```

## Stack

- Python 3.11+, Pydantic v2, HuggingFace `datasets`
- LLM access via `openai` SDK pointed at NVIDIA Build (`base_url=https://integrate.api.nvidia.com/v1`). Free, rate-limited tier; `NvidiaClient` has a 90s per-request timeout and disables the SDK's own retries (`max_retries=0`) so the timeout isn't silently multiplied.
- **One `NVIDIA_API_KEY`** in `.env` (gitignored) covers every model — NVIDIA Build keys are account-level; the model is chosen per request, not by the key.
- **Rate limit: 40 API calls/minute** (account-level, free tier). Pace concurrency with `--workers`; `NvidiaClient` waits ~12s on a 429 before retrying. At scale (Week 5), throttle generation to stay under this.
- Teacher LLM: **DeepSeek V4 Flash** (`deepseek-ai/deepseek-v4-flash`) — chosen from the hi/ta bake-off (fast, clean JSON, fluent). See `docs/model_selection.md`.
- Judge LLM: ensemble TBD. Candidates that respond + discriminate (English-control check): `sarvamai/sarvam-m`, `mistralai/mistral-small-4-119b-2603`, `z-ai/glm-5.1`, `nvidia/nemotron-3-super-120b-a12b`. Qwen times out; Gemma endpoint down. **Note:** runs so far are only liveness/format/trivial-discrimination screens — judge *quality* needs a human gold set (no ground truth yet).
- Target languages: `hi` (Hindi), `ur` (Urdu), `ta` (Tamil), `ml` (Malayalam)
- Use `--teacher mock` (offline `MockClient`) to exercise the full pipeline without a key or network.

## Key decisions already made

- Ensemble judging (majority vote across models) to address ~50% human–LLM agreement on Indic linguistic plausibility (per UPDESH)
- IndicLID language-ID gate: drop items where model is <75% confident output is in target language
- Generation strategy split by task type: top-down translation for reasoning/culture-agnostic tasks; bottom-up reverse-instruction (MURI approach) for culturally-grounded tasks
- API budget confirmed with manager

## CLI

```
# Generate (output -> data/generated/<lang>/<task>/<model>_<timestamp>.jsonl)
syndata generate --language hi --task qa --n 500 --teacher <model> --judge <model>

# Model bake-off: same seeds through several models -> docs/model_comparison_<lang>_<task>.md
syndata compare --language hi --task qa --n 2 \
  --models qwen/qwen3.5-122b-a10b,sarvamai/sarvam-m,deepseek-ai/deepseek-v4-flash
```

`compare` logs per-call progress (`[n/total]`, elapsed, preview) to stderr by default.

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
- End-to-end verified with `MockClient` *and* live: first real Hindi QA item generated via Qwen3.5
- Teacher responses requested as JSON; parser salvages fenced/preamble output and always keeps `raw_response`
- Per-vendor API key resolution; 90s request timeout + retry/backoff on `NvidiaClient`
- `syndata compare` bake-off command (verbose progress, Markdown report) for evidence-based model selection
- Output paths are non-clobbering (`<lang>/<task>/<model>_<timestamp>.jsonl`)
- Still pending: lock teacher/judge from the bake-off; `--judge` is recorded but inert until Week 4
