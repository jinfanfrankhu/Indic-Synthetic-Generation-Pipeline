# Per-Language Quality Metrics

_Snapshot over the current 2347-item corpus. **Back-translation is complete** (100% of non-translation items; the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring is still accruing** (OpenRouter free tier, ~900 attempts/day), so its coverage columns are below 100% and will keep rising. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 578 | 499 | 492 | 500/481 |
| Urdu (ur) | 591 | 253 | 151 | 516/493 |
| Tamil (ta) | 586 | 322 | 199 | 506/488 |
| Malayalam (ml) | 592 | 516 | 446 | 517/492 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 499 | 0.961 | 0.967 | 0.922 | 1.000 |
| Urdu (ur) | 253 | 0.932 | 0.950 | 0.867 | 0.992 |
| Tamil (ta) | 322 | 0.938 | 0.950 | 0.883 | 0.983 |
| Malayalam (ml) | 516 | 0.936 | 0.955 | 0.867 | 1.000 |
| **all** | 1590 | 0.944 | 0.958 | 0.883 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.933 | 0.963 | 0.986 | 0.961 |
| Urdu (ur) | 0.886 | 0.944 | 0.967 | 0.932 |
| Tamil (ta) | 0.900 | 0.941 | 0.974 | 0.938 |
| Malayalam (ml) | 0.895 | 0.934 | 0.979 | 0.936 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 500 | 0.888 | 0.924 | 0.745 | 0.989 |
| Urdu (ur) | 516 | 0.867 | 0.904 | 0.715 | 0.977 |
| Tamil (ta) | 506 | 0.857 | 0.888 | 0.699 | 0.974 |
| Malayalam (ml) | 517 | 0.859 | 0.892 | 0.716 | 0.968 |
| **all** | 2039 | 0.868 | 0.901 | 0.720 | 0.979 |

## Known gaps

- **Urdu ensemble:** 151 Urdu items have >=2 judges. The 2nd core judge (`gpt-oss-20b:free`) is frequently congested on the OpenRouter free tier, so the majority-vote design is under-realized for Urdu. A more reliable 2nd/3rd judge would close this.
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day) and back-translation is CPU-only NLLB, so full coverage accrues over several days.
