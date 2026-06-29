# Buttery

Synthetic instruction-data generation pipeline for low-resource Indic languages:
Hindi (`hi`), Urdu (`ur`), Tamil (`ta`), and Malayalam (`ml`).

The pipeline generates instruction / QA / classification / summarization /
translation / reasoning data with a strong teacher LLM, then scores each item
through a chain of complementary quality filters. See [DESIGN.md](DESIGN.md) for the
methodology decisions and [TIMELINE.md](TIMELINE.md) for the project plan.

## Install

```bash
python -m pip install -e .            # base pipeline (lightweight)
python -m pip install -e .[dev]       # + pytest
python -m pip install -e .[backtranslation]   # + sentence-transformers/PyTorch (heavy, optional)
```

Requires Python 3.11+. The `backtranslation` extra is **only** needed to run the
back-translation filter with a real SBERT model — everything else, including that
filter's tests, runs without it.

## API keys (multi-provider)

Models are addressed through one OpenAI-compatible client. A model id may carry a
`provider:` prefix; each provider resolves its own key from the environment or a
local `.env` (all gitignored):

| Provider | Prefix | Key | Notes |
| --- | --- | --- | --- |
| Google AI Studio | `gemini:` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | **Teacher.** `gemini-3.1-flash-lite` = 15 RPM / 500 RPD. |
| NVIDIA Build | *(none — bare id)* | `NVIDIA_API_KEY` | Judge candidates. Free tier bursts → multi-hour 429 lockouts; not for batch. |
| OpenRouter | `openrouter:` | `OPENROUTER_API_KEY` | Alternate judge access. |

```bash
export GEMINI_API_KEY=...      # or put keys in .env
```

You can build and exercise the **whole pipeline offline** with `--teacher mock`
(canned output, no key, no network).

### Why Gemini is the teacher

NVIDIA Build's free tier proved unusable for batch (per-model multi-hour 429
lockouts). The teacher migrated to `gemini:gemini-3.1-flash-lite` — clean JSON,
~1s/item, fluent localized output, 500 calls/day. DeepSeek V4 Flash is the
documented fallback. Full rationale: [docs/model_selection.md](docs/model_selection.md).

## Generation

```bash
# Offline smoke test — canned output, no network, no key:
syndata generate --language hi --task qa --n 5 --teacher mock

# Real generation against the teacher:
syndata generate --language hi --task qa --n 50 --teacher gemini:gemini-3.1-flash-lite
```

Output is JSONL (one `SyntheticItem` per line) at
`data/generated/<lang>/<task>/<model>_<timestamp>.jsonl` (non-clobbering).

### Resilient batch generation (`generate-drip`)

The preferred way to scale: serial generation across every language × task, pacing
call starts and applying escalating backoff on throttle. Resumable — it counts what
is already on disk and fills only the gap.

```bash
syndata generate-drip --languages hi,ur,ta,ml --tasks all \
  --per-combo 20 --teacher gemini:gemini-3.1-flash-lite \
  --calls-per-minute 12 --seeds data/seeds/<your-seeds>.json
```

`--calls-per-minute` paces *starts* for low-RPM providers; `--backoffs` controls the
escalating waits on failure. (`generate-batch` is the older concurrent sweep; prefer
`generate-drip` against throttled endpoints.)

### Growing the seed pool (`bootstrap-seeds`)

The curated seed pool is small, and scaling against too few seeds just regenerates
near-duplicates. Expand it with self-instruct first, then **hand-review** before use:

```bash
syndata bootstrap-seeds --tasks all --n 200 --per-call 8 \
  --teacher gemini:gemini-3.1-flash-lite --calls-per-minute 12
#  -> data/seeds/bootstrapped_<timestamp>.json
```

Verbose / long-form families (summarization, reasoning) need a smaller `--per-call`
and larger `--max-tokens` so the JSON array isn't truncated, e.g.
`--tasks summarization,reasoning --per-call 3 --max-tokens 3072`.

## Quality filters

```bash
# Deterministic gates only (no API, no key): structural + language-ID
syndata filter --generated data/generated

# Add the score-only LLM-judge ensemble and/or back-translation:
syndata filter --generated data/generated \
  --judges z-ai/glm-5.1,mistralai/mistral-small-4-119b-2603,nvidia/nemotron-3-super-120b-a12b \
  --back-translate gemini:gemini-3.1-flash-lite --calls-per-minute 12
```

`filter` runs the chain over a generated pool and writes:
- **per-item verdicts** → `data/filtered/verdicts_<ts>.jsonl` (every filter's call on every item)
- **a retention report** → `docs/filter_retention_<ts>.md` (per-language and per-task pass rates)

The four filters (`syndata/filters/`):

| Filter | Kind | Drops? | Notes |
| --- | --- | --- | --- |
| `structural` | deterministic | yes | Presence, answer-required, scaffolding leak, truncation, >75%-repetition (UPDESH). |
| `language_id` | deterministic | yes | Target-script proportion ≥ 0.75. **Translation family exempt** (it carries source-language text by design). |
| `llm_judge` | API (ensemble) | no — score-only | Fluency / faithfulness / bias, mean/median across judges. |
| `back_translation` | API + local SBERT | no — score-only | Back-translate to English, cosine vs the seed. Needs the `backtranslation` extra. |

**Two-tier philosophy:** objective gates are strict from day one (spec-mandated or
definitional thresholds); subjective scores run **score-only** — recorded, never
enforced — until calibrated against the human gold set. No threshold is guessed. See
[DESIGN.md](DESIGN.md) Q3/Q5 and [docs/gold_standard_protocol.md](docs/gold_standard_protocol.md).

### Judge evidence + gold set

```bash
syndata judge-compare --language ta --task qa --judges ...   # discrimination probe
syndata judge-score   --generated data/generated --judges ... # persist ensemble + per-judge scores
syndata export-gold   --generated data/generated --scores <scores>.jsonl  # blind rater bundle + private manifest
```

## Module map

| Module | Role |
| --- | --- |
| `data_structures.py` | Pydantic v2 schemas (`SeedItem`, `SyntheticItem`, `QualityScore`, `QualityFilterResult`, …). |
| `seeds.py` | Load/parse/filter English `SeedItem`s; `{"seeds": [...]}` JSON. |
| `templates.py` | Teacher-prompt registry: top-down translate vs. bottom-up adapt-and-localize per task family. |
| `client.py` | `ChatClient` protocol; `OpenAICompatibleClient` + provider registry; `MockClient` (offline). |
| `ratelimit.py` | Shared min-interval throttle on call starts. |
| `generator.py` | Seed + `GenerationConfig` → teacher call → parse → `SyntheticItem`. |
| `parsing.py` | Salvage JSON from fenced / preamble-wrapped teacher output. |
| `bootstrap.py` | Self-instruct seed expansion + structural pre-filters. |
| `compare.py` | Model bake-off → Markdown report. |
| `judge.py` | LLM-as-judge engine (`score_item`, judge panel). |
| `gold.py` | Gold-set selection, rater bundle + manifest assembly. |
| `filters/` | `structural`, `language_id`, `llm_judge`, `back_translation`, `FilterChain`, retention reporting. |
| `cli.py` | All subcommands (below). |

**CLI:** `generate`, `generate-drip`, `generate-batch`, `compare`, `bootstrap-seeds`,
`filter`, `judge-compare`, `judge-score`, `export-gold`.

## Testing

```bash
python -m pytest tests/        # deterministic filters, chain, retention, back-translation (no torch needed)
```

## Windows note

To print Indic scripts to the console, run with `PYTHONUTF8=1` (or
`PYTHONIOENCODING=utf-8`). Output **files** are always UTF-8 regardless.

## Roadmap

See [TIMELINE.md](TIMELINE.md). Threshold calibration against the human gold set and
full-scale generation are the active Week 5 work.
