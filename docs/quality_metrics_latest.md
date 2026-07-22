# Per-Language Quality Metrics

_Snapshot over the current 3231-item corpus. Both subjective scorers run score-only (nothing dropped) until the human gold set calibrates their thresholds. **Back-translation** covers 2039/2682 non-translation items (76%); it had reached 100% on the prior corpus and the newest seed batch is queued for the next local NLLB pass (the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring** accrues over the OpenRouter free tier (~900 attempts/day), so its coverage columns sit below 100% and keep rising; each new seed batch resets the denominator. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 799 | 499 | 492 | 500/663 |
| Urdu (ur) | 812 | 496 | 458 | 516/675 |
| Tamil (ta) | 807 | 490 | 445 | 506/670 |
| Malayalam (ml) | 813 | 516 | 475 | 517/674 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 499 | 0.961 | 0.967 | 0.922 | 1.000 |
| Urdu (ur) | 496 | 0.932 | 0.950 | 0.850 | 0.993 |
| Tamil (ta) | 490 | 0.943 | 0.957 | 0.883 | 0.992 |
| Malayalam (ml) | 516 | 0.933 | 0.950 | 0.854 | 1.000 |
| **all** | 2001 | 0.942 | 0.958 | 0.875 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.933 | 0.963 | 0.986 | 0.961 |
| Urdu (ur) | 0.885 | 0.947 | 0.965 | 0.932 |
| Tamil (ta) | 0.895 | 0.954 | 0.981 | 0.943 |
| Malayalam (ml) | 0.891 | 0.931 | 0.978 | 0.933 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 500 | 0.888 | 0.924 | 0.745 | 0.989 |
| Urdu (ur) | 516 | 0.867 | 0.904 | 0.715 | 0.977 |
| Tamil (ta) | 506 | 0.857 | 0.888 | 0.699 | 0.974 |
| Malayalam (ml) | 517 | 0.859 | 0.892 | 0.716 | 0.968 |
| **all** | 2039 | 0.868 | 0.901 | 0.720 | 0.979 |

## Known gaps

- **Urdu ensemble gap — resolved.** Urdu now has 458 items with >=2 judges, balanced with the other languages. It had been stuck at 0: judge scoring processed items in glob order (hi, ml, ta, ur), so the daily cap was always spent before reaching Urdu. Fixed by fair, ensemble-first item ordering (round-robin across languages).
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the two free judges frequently congest, so full ensemble coverage accrues over several days.
- **Newest seed batch (07-22, +448 items) awaits scoring.** Those items are in the corpus but not yet judged or back-translated, which is why coverage percentages dipped against the larger denominator. Back-translation (local NLLB, no API budget) and the next judge pass close this; neither touches the Gemini quota.
