# Per-Language Quality Metrics

_Snapshot over the current 3231-item corpus. Both subjective scorers run score-only (nothing dropped) until the human gold set calibrates their thresholds. **Back-translation** is complete — 2682/2682 non-translation items (100%) scored via local NLLB-200 (the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring** accrues over the OpenRouter free tier (~900 attempts/day), so its coverage columns sit below 100% and keep rising; each new seed batch resets the denominator until the next daily pass catches up. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 799 | 569 | 494 | 663/663 |
| Urdu (ur) | 812 | 562 | 468 | 675/675 |
| Tamil (ta) | 807 | 554 | 464 | 670/670 |
| Malayalam (ml) | 813 | 574 | 493 | 674/674 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 569 | 0.959 | 0.967 | 0.923 | 1.000 |
| Urdu (ur) | 562 | 0.936 | 0.952 | 0.858 | 1.000 |
| Tamil (ta) | 554 | 0.944 | 0.958 | 0.883 | 0.993 |
| Malayalam (ml) | 574 | 0.933 | 0.950 | 0.844 | 1.000 |
| **all** | 2259 | 0.943 | 0.958 | 0.875 | 1.000 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.932 | 0.961 | 0.984 | 0.959 |
| Urdu (ur) | 0.890 | 0.950 | 0.967 | 0.936 |
| Tamil (ta) | 0.893 | 0.956 | 0.983 | 0.944 |
| Malayalam (ml) | 0.889 | 0.933 | 0.977 | 0.933 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 663 | 0.884 | 0.917 | 0.739 | 0.990 |
| Urdu (ur) | 675 | 0.863 | 0.899 | 0.700 | 0.978 |
| Tamil (ta) | 670 | 0.856 | 0.886 | 0.699 | 0.974 |
| Malayalam (ml) | 674 | 0.860 | 0.891 | 0.725 | 0.969 |
| **all** | 2682 | 0.865 | 0.897 | 0.716 | 0.980 |

## Known gaps

- **Urdu ensemble gap — resolved.** Urdu now has 468 items with >=2 judges, balanced with the other languages. It had been stuck at 0: judge scoring processed items in glob order (hi, ml, ta, ur), so the daily cap was always spent before reaching Urdu. Fixed by fair, ensemble-first item ordering (round-robin across languages).
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the two free judges frequently congest, so full ensemble coverage accrues over several days.
- **Back-translation is complete corpus-wide** (2682/2682 non-translation items). A 07-22 pass closed 728 previously-unscored items — including ~356 stragglers that predated the newest batch — so the earlier 'complete' claim is now actually true.
- The newest seed batch (07-22, +448 items) is fully back-translated but only partially judged (today's 900-attempt quota was spent); its ensemble coverage continues to fill in over the next daily judge windows. No Gemini quota involved.
