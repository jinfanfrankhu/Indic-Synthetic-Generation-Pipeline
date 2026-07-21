# Per-Language Quality Metrics

_Snapshot over the current 2783-item corpus. **Back-translation is complete** (100% of non-translation items; the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring is still accruing** (OpenRouter free tier, ~900 attempts/day), so its coverage columns are below 100% and will keep rising. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 687 | 499 | 492 | 500/570 |
| Urdu (ur) | 700 | 393 | 361 | 516/582 |
| Tamil (ta) | 695 | 388 | 354 | 506/577 |
| Malayalam (ml) | 701 | 516 | 446 | 517/581 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 499 | 0.961 | 0.967 | 0.922 | 1.000 |
| Urdu (ur) | 393 | 0.928 | 0.948 | 0.850 | 0.992 |
| Tamil (ta) | 388 | 0.939 | 0.951 | 0.875 | 0.992 |
| Malayalam (ml) | 516 | 0.936 | 0.955 | 0.867 | 1.000 |
| **all** | 1796 | 0.942 | 0.958 | 0.875 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.933 | 0.963 | 0.986 | 0.961 |
| Urdu (ur) | 0.882 | 0.942 | 0.960 | 0.928 |
| Tamil (ta) | 0.893 | 0.947 | 0.977 | 0.939 |
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

- **Urdu ensemble gap — resolved.** Urdu now has 361 items with >=2 judges, balanced with the other languages. It had been stuck at 0: judge scoring processed items in glob order (hi, ml, ta, ur), so the daily cap was always spent before reaching Urdu. Fixed by fair, ensemble-first item ordering (round-robin across languages).
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the two free judges frequently congest, so full ensemble coverage accrues over several days. Back-translation (CPU-only NLLB) is complete.
