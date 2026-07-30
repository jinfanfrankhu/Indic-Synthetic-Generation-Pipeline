# Per-Language Quality Metrics

_Snapshot over the current 4611-item corpus. Both subjective scorers run score-only (nothing dropped) until the human gold set calibrates their thresholds. **Back-translation** is complete — 3850/3850 non-translation items (100%) scored via local NLLB-200 (the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring** accrues over the OpenRouter free tier (~900 attempts/day), so its coverage columns sit below 100% and keep rising; each new seed batch resets the denominator until the next daily pass catches up. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 1144 | 796 | 769 | 955/955 |
| Urdu (ur) | 1157 | 796 | 743 | 967/967 |
| Tamil (ta) | 1152 | 775 | 751 | 962/962 |
| Malayalam (ml) | 1158 | 781 | 768 | 966/966 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 796 | 0.962 | 0.967 | 0.925 | 1.000 |
| Urdu (ur) | 796 | 0.935 | 0.951 | 0.857 | 0.992 |
| Tamil (ta) | 775 | 0.944 | 0.958 | 0.883 | 0.992 |
| Malayalam (ml) | 781 | 0.937 | 0.955 | 0.867 | 0.997 |
| **all** | 3148 | 0.944 | 0.958 | 0.883 | 0.997 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.934 | 0.965 | 0.986 | 0.962 |
| Urdu (ur) | 0.885 | 0.952 | 0.968 | 0.935 |
| Tamil (ta) | 0.894 | 0.955 | 0.982 | 0.944 |
| Malayalam (ml) | 0.895 | 0.939 | 0.978 | 0.937 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 955 | 0.883 | 0.915 | 0.740 | 0.988 |
| Urdu (ur) | 967 | 0.861 | 0.897 | 0.700 | 0.978 |
| Tamil (ta) | 962 | 0.851 | 0.880 | 0.695 | 0.969 |
| Malayalam (ml) | 966 | 0.858 | 0.887 | 0.716 | 0.968 |
| **all** | 3850 | 0.863 | 0.894 | 0.713 | 0.979 |

## Known gaps

- **Urdu ensemble gap — resolved.** Urdu now has 743 items with >=2 judges, balanced with the other languages. It had been stuck at 0: judge scoring processed items in glob order (hi, ml, ta, ur), so the daily cap was always spent before reaching Urdu. Fixed by fair, ensemble-first item ordering (round-robin across languages).
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the two free judges frequently congest, so full ensemble coverage accrues over several days.
- **Back-translation is complete corpus-wide** (3850/3850 non-translation items). A 07-22 pass closed 728 previously-unscored items — including ~356 stragglers that predated the newest batch — so the earlier 'complete' claim is now actually true.
- The newest seed batch (07-22, +448 items) is fully back-translated but only partially judged (today's 900-attempt quota was spent); its ensemble coverage continues to fill in over the next daily judge windows. No Gemini quota involved.
