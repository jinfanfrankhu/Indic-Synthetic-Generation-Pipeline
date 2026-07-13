# Per-Language Quality Metrics

_Score distributions over the **903 scored items** from the first generation batch, computed from `data/filtered/judge_scores.jsonl` and `data/filtered/backtranslation_scores.jsonl`. The corpus has since grown to 1,390 items (487 new seeds added 2026-07-13); the new items pass the deterministic gates (see the retention report) but are **not yet judge/back-translation scored** — that pass is pending._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores are collapsed to one value per item (mean across judges) before taking the per-language distribution. Judge dimensions are 0–1 (higher = better; `bias` = 1.0 means no detected English/source bias).

## Judge — overall score distribution

| Language | N items | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 225 | 0.954 | 0.967 | 0.908 | 1.000 |
| Urdu (ur) | 227 | 0.941 | 0.950 | 0.883 | 1.000 |
| Tamil (ta) | 222 | 0.934 | 0.950 | 0.867 | 0.991 |
| Malayalam (ml) | 227 | 0.924 | 0.943 | 0.813 | 0.997 |
| **all** | 901 | 0.938 | 0.955 | 0.867 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.924 | 0.956 | 0.982 | 0.954 |
| Urdu (ur) | 0.898 | 0.948 | 0.975 | 0.941 |
| Tamil (ta) | 0.889 | 0.942 | 0.972 | 0.934 |
| Malayalam (ml) | 0.881 | 0.922 | 0.969 | 0.924 |

## Back-translation — cosine similarity distribution

_Cosine similarity between the NLLB back-translation of the generated item and its English seed. Higher = more faithful round-trip._

| Language | N items | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 225 | 0.888 | 0.922 | 0.751 | 0.979 |
| Urdu (ur) | 228 | 0.873 | 0.904 | 0.759 | 0.973 |
| Tamil (ta) | 222 | 0.851 | 0.883 | 0.703 | 0.965 |
| Malayalam (ml) | 228 | 0.861 | 0.891 | 0.723 | 0.967 |
| **all** | 903 | 0.868 | 0.902 | 0.730 | 0.972 |

## Coverage caveats

| Language | items judged | ≥2 judges | back-translated |
| --- | --- | --- | --- |
| Hindi (hi) | 225 | 224 | 225 |
| Urdu (ur) | 227 | 0 | 228 |
| Tamil (ta) | 222 | 148 | 222 |
| Malayalam (ml) | 227 | 219 | 228 |

Ensemble judging is incomplete: some items carry only a single judge score (see ≥2-judges column), so the majority-vote design is not yet fully realized on this snapshot. Judge thresholds remain **score-only / uncalibrated** — no human gold set exists yet, so these distributions describe the data but do not (yet) drive rejection.
