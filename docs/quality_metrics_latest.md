# Per-Language Quality Metrics

_Snapshot over the current 3651-item corpus. Both subjective scorers run score-only (nothing dropped) until the human gold set calibrates their thresholds. **Back-translation** is complete — 3050/3050 non-translation items (100%) scored via local NLLB-200 (the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring** accrues over the OpenRouter free tier (~900 attempts/day), so its coverage columns sit below 100% and keep rising; each new seed batch resets the denominator until the next daily pass catches up. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 904 | 587 | 581 | 755/755 |
| Urdu (ur) | 917 | 591 | 560 | 767/767 |
| Tamil (ta) | 912 | 585 | 562 | 762/762 |
| Malayalam (ml) | 918 | 592 | 577 | 766/766 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 587 | 0.959 | 0.967 | 0.921 | 1.000 |
| Urdu (ur) | 591 | 0.935 | 0.950 | 0.858 | 0.993 |
| Tamil (ta) | 585 | 0.943 | 0.958 | 0.883 | 0.992 |
| Malayalam (ml) | 592 | 0.933 | 0.950 | 0.858 | 0.996 |
| **all** | 2355 | 0.943 | 0.958 | 0.875 | 0.994 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.931 | 0.962 | 0.985 | 0.959 |
| Urdu (ur) | 0.889 | 0.949 | 0.967 | 0.935 |
| Tamil (ta) | 0.894 | 0.954 | 0.982 | 0.943 |
| Malayalam (ml) | 0.889 | 0.933 | 0.977 | 0.933 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 755 | 0.884 | 0.919 | 0.739 | 0.990 |
| Urdu (ur) | 767 | 0.862 | 0.898 | 0.697 | 0.979 |
| Tamil (ta) | 762 | 0.853 | 0.884 | 0.694 | 0.973 |
| Malayalam (ml) | 766 | 0.861 | 0.889 | 0.728 | 0.970 |
| **all** | 3050 | 0.865 | 0.896 | 0.715 | 0.980 |

## Known gaps

- **Urdu ensemble gap — resolved.** Urdu now has 560 items with >=2 judges, balanced with the other languages. It had been stuck at 0: judge scoring processed items in glob order (hi, ml, ta, ur), so the daily cap was always spent before reaching Urdu. Fixed by fair, ensemble-first item ordering (round-robin across languages).
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the two free judges frequently congest, so full ensemble coverage accrues over several days.
- **Back-translation is complete corpus-wide** (3050/3050 non-translation items). A 07-22 pass closed 728 previously-unscored items — including ~356 stragglers that predated the newest batch — so the earlier 'complete' claim is now actually true.
- The newest seed batch (07-22, +448 items) is fully back-translated but only partially judged (today's 900-attempt quota was spent); its ensemble coverage continues to fill in over the next daily judge windows. No Gemini quota involved.
