# Buttery

Synthetic instruction-data generation pipeline for low-resource Indic languages:
Hindi (`hi`), Urdu (`ur`), Tamil (`ta`), and Malayalam (`ml`).

> Status: **Week 3 — pipeline skeleton.** Generation runs end-to-end; quality
> filtering (LLM-as-judge, language-ID gate, back-translation) lands in Week 4.

## Install

```bash
python -m pip install -e .
```

Requires Python 3.11+.

## API key

Generation uses [NVIDIA Build](https://build.nvidia.com) (free, rate-limited,
OpenAI-compatible). Get a key and make it available via environment variable or
a local `.env` file:

```bash
export NVIDIA_API_KEY=nvapi-...      # or put it in .env
```

You can build and test the whole pipeline without a key using `--teacher mock`.

## Usage

```bash
# Offline smoke test — canned output, no network, no key:
syndata generate --language hi --task qa --n 5 --teacher mock

# Real generation against the teacher model:
syndata generate \
  --language hi --task qa --n 50 \
  --teacher qwen/qwen3-5-122b \
  --judge meta/llama-3.3-70b-instruct
```

Output is written as JSONL (one `SyntheticItem` per line) to
`data/generated/<lang>_<task>_<n>.jsonl` by default; override with `--out`.

`--judge` is accepted and recorded for provenance but not yet invoked
(filtering is Week 4).

### Windows note

To print Indic scripts to the console, run with `PYTHONUTF8=1`. Output **files**
are always UTF-8 regardless.

## How it works

| Module | Role |
| --- | --- |
| `seeds.py` | Load/parse/filter English `SeedItem`s from `data/seeds/`. |
| `templates.py` | Build the teacher prompt. Picks **top-down translation** for reasoning/QA/summarization/translation and **bottom-up adapt-and-localize** for instruction/classification. |
| `client.py` | `ChatClient` protocol + `NvidiaClient` (live, with retry/backoff) and `MockClient` (offline). |
| `generator.py` | Seed + `GenerationConfig` → teacher call → parse → `SyntheticItem` with full provenance. |
| `cli.py` | The `syndata generate` command. |

Teacher responses are requested as JSON; the parser salvages fenced or
preamble-wrapped output and falls back to keeping the raw text. The raw response
is always stored on `SyntheticItem.raw_response` for audit.

## Roadmap

See [TIMELINE.md](TIMELINE.md). Next up (Week 4): structural validity, LLM-judge,
and language-ID filters.
