# Buttery

Synthetic instruction-data pipeline for low-resource Indic languages: Hindi (`hi`), Urdu (`ur`), Tamil (`ta`), Malayalam (`ml`).

Generates instruction / QA / classification / summarization / translation / reasoning data with a teacher LLM, then scores each item through a chain of quality filters. See [DESIGN.md](DESIGN.md) for methodology.

## Corpus

**5,101 items** — 4 languages × 6 task families.

| Task | hi | ur | ta | ml |
| --- | --- | --- | --- | --- |
| classification | 216 | 218 | 216 | 216 |
| instruction | 220 | 219 | 220 | 219 |
| qa | 191 | 193 | 191 | 193 |
| reasoning | 216 | 221 | 219 | 222 |
| summarization | 216 | 218 | 218 | 218 |
| translation | 209 | 210 | 210 | 212 |

Filter retention ~99–100%. BT similarity mean 0.86. Judge ensemble mean 0.94 (score-only; not yet calibrated against a gold set).

## Install

```bash
pip install -e .               # base pipeline
pip install -e .[dev]          # + pytest
pip install -e .[backtranslation]  # + SBERT/PyTorch for back-translation filter
```

Requires Python 3.11+.

## API keys

Put keys in `.env` (gitignored):

| Provider | Prefix | Env var |
| --- | --- | --- |
| Google AI Studio | `gemini:` | `GEMINI_API_KEY` |
| NVIDIA Build | *(bare id)* | `NVIDIA_API_KEY` |
| OpenRouter | `openrouter:` | `OPENROUTER_API_KEY` |

Use `--teacher mock` to run the whole pipeline offline with no key.

## CLI

```bash
# Generate
syndata generate --language hi --task qa --n 50 --teacher gemini:gemini-3.1-flash-lite

# Resilient batch (resumable, paced for free-tier rate limits)
syndata generate-drip --languages hi,ur,ta,ml --tasks all --per-combo 20 \
  --teacher gemini:gemini-3.1-flash-lite --calls-per-minute 12 \
  --seeds data/seeds/<your-seeds>.json

# Expand seed pool (hand-review output before generating against it)
syndata bootstrap-seeds --tasks all --n 200 --teacher gemini:gemini-3.1-flash-lite

# Quality filter chain
syndata filter --generated data/generated

# Model bake-off
syndata compare --language hi --task qa --n 5 --models model-a,model-b
```

## Filters

| Filter | Drops? | Signal |
| --- | --- | --- |
| `structural` | yes | Format, length, truncation, repetition |
| `language_id` | yes | Target-script proportion ≥ 0.75 (translation family exempt) |
| `llm_judge` | no — score only | Fluency / faithfulness / bias ensemble |
| `back_translation` | no — score only | NLLB-200 → English cosine vs. seed |

## Tests

```bash
pytest tests/
```

## Notes

- On Windows, set `PYTHONUTF8=1` to print Indic scripts to the console.
- Output files are always UTF-8.
