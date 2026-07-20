# Per-Language Quality Metrics

_Live snapshot over the current 2347-item corpus. **Scoring is still in progress** (back-translation and judge passes run resumably), so the coverage columns are below 100% and will rise. Judge scores are the ensemble mean per item across the judges that scored it; the back-translation column excludes the translation family (covered by the dedicated translation check, per DESIGN Q5)._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 578 | 481 | 246 | 477/481 |
| Urdu (ur) | 591 | 215 | 0 | 216/493 |
| Tamil (ta) | 586 | 206 | 137 | 206/488 |
| Malayalam (ml) | 592 | 441 | 208 | 215/492 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 481 | 0.963 | 0.975 | 0.917 | 1.000 |
| Urdu (ur) | 215 | 0.939 | 0.950 | 0.883 | 1.000 |
| Tamil (ta) | 206 | 0.932 | 0.950 | 0.867 | 0.983 |
| Malayalam (ml) | 441 | 0.928 | 0.955 | 0.808 | 1.000 |
| **all** | 1343 | 0.943 | 0.963 | 0.867 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.937 | 0.966 | 0.987 | 0.963 |
| Urdu (ur) | 0.896 | 0.945 | 0.974 | 0.939 |
| Tamil (ta) | 0.887 | 0.938 | 0.971 | 0.932 |
| Malayalam (ml) | 0.882 | 0.926 | 0.975 | 0.928 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 477 | 0.887 | 0.922 | 0.745 | 0.990 |
| Urdu (ur) | 216 | 0.870 | 0.902 | 0.754 | 0.973 |
| Tamil (ta) | 206 | 0.849 | 0.881 | 0.690 | 0.964 |
| Malayalam (ml) | 215 | 0.858 | 0.890 | 0.718 | 0.967 |
| **all** | 1114 | 0.871 | 0.904 | 0.731 | 0.980 |

## Known gaps

- **Urdu ensemble:** 0 Urdu items have >=2 judges. The 2nd core judge (`gpt-oss-20b:free`) is frequently congested on the OpenRouter free tier, so the majority-vote design is under-realized for Urdu. A more reliable 2nd/3rd judge would close this.
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day) and back-translation is CPU-only NLLB, so full coverage accrues over several days.
