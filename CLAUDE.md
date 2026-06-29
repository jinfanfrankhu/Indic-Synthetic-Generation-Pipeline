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
- **Multi-provider LLM access** via the `openai` SDK against any OpenAI-compatible endpoint (`syndata/client.py` → `OpenAICompatibleClient` + a `PROVIDERS` registry). A model id may carry a `provider:` prefix — `gemini:`, `openrouter:`, or default `nvidia` (bare ids). Each provider resolves its own key from `.env`: `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY` (all gitignored). 90s timeout, `max_retries=0` on the SDK (our loop owns retries).
- **Provider rate limits differ and are the main operational constraint.** NVIDIA Build free tier: nominal 40/min but bursts trigger **multi-hour per-model 429 lockouts** — unusable for batch (see `docs/model_selection.md`). Google AI Studio (Gemini) free tier is *per-model*: `gemini-3.1-flash-lite` = 15 RPM / **500 RPD** (the teacher); Flash models are only 20 RPD. `RateLimiter` (`syndata/ratelimit.py`) paces call *starts*; `generate-drip` adds escalating backoff for throttled endpoints.
- Teacher LLM: **Gemini 3.1 Flash Lite** (`gemini:gemini-3.1-flash-lite`) — migrated from DeepSeek V4 Flash in Week 4 after NVIDIA's batch lockouts; chosen from the hi bake-off (clean JSON, ~1s/item, fluent localized Hindi, 500/day). DeepSeek is the documented fallback. See `docs/model_selection.md`.
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

# Self-instruct seed expansion (English) -> data/seeds/bootstrapped_<ts>.json
# (hand-review the output before generating against it)
syndata bootstrap-seeds --tasks all --n 200 --teacher deepseek-ai/deepseek-v4-flash

# Batch sweep across all languages x tasks from a seed file -> data/generated/<lang>/<task>/...
syndata generate-batch --seeds data/seeds/bootstrapped_<ts>.json \
  --teacher deepseek-ai/deepseek-v4-flash --per-combo 8 --workers 4

# Resilient serial fill (preferred for throttled endpoints; resumable) -> same layout
syndata generate-drip --languages hi,ur,ta,ml --tasks all --per-combo 20 \
  --teacher gemini:gemini-3.1-flash-lite --calls-per-minute 12 --seeds data/seeds/<ts>.json

# Quality-filter chain -> data/filtered/verdicts_<ts>.jsonl + docs/filter_retention_<ts>.md
# Deterministic gates only (no API); add --judges / --back-translate for score-only passes.
syndata filter --generated data/generated
```

`compare` logs per-call progress (`[n/total]`, elapsed, preview) to stderr by default.

## What still needs to be written

- `METHODOLOGY.md` — 2,500–3,500 word paper-style writeup
- Jupyter notebook (exploratory analysis)
- 5-slide presentation PDF
- Threshold calibration: subjective filters (LLM-judge, back-translation) run score-only until tuned against the human gold set

Done since the skeleton: `DESIGN.md` (the 5 methodology decisions); all four quality
filters in `syndata/filters/` (structural, language-ID, LLM-judge, back-translation)
plus the `syndata filter` chain + retention reporting; a `tests/` suite (40 tests,
deterministic + injectable fakes, no API/torch needed).

## Done (Week 3 — pipeline skeleton)

- Generation pipeline in `syndata/`: seed loader, prompt templates, chat clients, generator, CLI
- `pyproject.toml` (deps + `syndata` entry point); `README.md` stub
- End-to-end verified with `MockClient` *and* live: first real Hindi QA item generated via Qwen3.5
- Teacher responses requested as JSON; parser salvages fenced/preamble output and always keeps `raw_response`
- Per-vendor API key resolution; 90s request timeout + retry/backoff on `NvidiaClient`
- `syndata compare` bake-off command (verbose progress, Markdown report) for evidence-based model selection
- Output paths are non-clobbering (`<lang>/<task>/<model>_<timestamp>.jsonl`)
- `syndata bootstrap-seeds` (self-instruct seed expansion + structural pre-filters; hand-review gate before use) and `syndata generate-batch` (concurrent sweep across languages × tasks) for the Week 3 demo set
- Global `RateLimiter` (36/min) wired into `NvidiaClient` so every live path stays under the 40/min cap
- Still pending: lock teacher/judge from the bake-off; `--judge` is recorded but inert until Week 4
