# Per-Language Quality Metrics

_Snapshot over the current 5091-item corpus. Both subjective scorers run score-only (nothing dropped) until the human gold set calibrates their thresholds. **Back-translation** is complete — 4250/4250 non-translation items (100%) scored via local NLLB-200 (the translation family is covered by the dedicated translation check, per DESIGN Q5). **Judge scoring** accrues over the OpenRouter free tier (~900 attempts/day), so its coverage columns sit below 100% and keep rising; each new seed batch resets the denominator until the next daily pass catches up. Judge scores are the ensemble mean per item across the judges that scored it._

**Judge ensemble:** openrouter:nvidia/nemotron-3-super-120b-a12b:free, openrouter:openai/gpt-oss-20b:free. Scores 0-1, higher = better.

## Coverage (scoring in progress)

| Language | items | judged (>=1) | ensemble (>=2 judges) | back-translated |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 1264 | 826 | 815 | 1055/1055 |
| Urdu (ur) | 1277 | 831 | 785 | 1067/1067 |
| Tamil (ta) | 1272 | 826 | 788 | 1062/1062 |
| Malayalam (ml) | 1278 | 830 | 805 | 1066/1066 |

## Judge — overall score distribution (over scored items)

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 826 | 0.961 | 0.967 | 0.925 | 1.000 |
| Urdu (ur) | 831 | 0.935 | 0.950 | 0.858 | 0.992 |
| Tamil (ta) | 826 | 0.943 | 0.958 | 0.883 | 0.992 |
| Malayalam (ml) | 830 | 0.937 | 0.954 | 0.867 | 0.997 |
| **all** | 3313 | 0.944 | 0.958 | 0.883 | 0.994 |

## Judge — per-dimension mean (item-level)

| Language | fluency | faithfulness | bias | overall |
| --- | --- | --- | --- | --- |
| Hindi (hi) | 0.933 | 0.965 | 0.985 | 0.961 |
| Urdu (ur) | 0.886 | 0.951 | 0.968 | 0.935 |
| Tamil (ta) | 0.893 | 0.953 | 0.982 | 0.943 |
| Malayalam (ml) | 0.895 | 0.939 | 0.978 | 0.937 |

## Back-translation — cosine similarity distribution

| Language | N scored | mean | median | p10 | p90 |
| --- | --- | --- | --- | --- | --- |
| Hindi (hi) | 1055 | 0.882 | 0.915 | 0.733 | 0.987 |
| Urdu (ur) | 1067 | 0.861 | 0.896 | 0.699 | 0.978 |
| Tamil (ta) | 1062 | 0.850 | 0.879 | 0.692 | 0.969 |
| Malayalam (ml) | 1066 | 0.855 | 0.885 | 0.708 | 0.968 |
| **all** | 4250 | 0.862 | 0.893 | 0.707 | 0.979 |

## Known gaps

- **Back-translation is complete corpus-wide** (4250/4250 non-translation items). The 07-31 batch added 400 items; a further pass closed the remaining 121 stragglers.
- Judge scoring is OpenRouter-free-tier / daily-capped (~900 attempts/day), and the free judges frequently congest, so full ensemble coverage accrues over several days. 1778 items remain unjudged.
- **Judge availability is the binding constraint, not the daily cap.** The 07-31 pass landed 324 scores from 429 attempts (~75% success) before all four configured judges congested out. Three runs on 08-02 managed 3 scores from 37 attempts (~8%) — the free pool's availability swings by an order of magnitude between windows, and failed attempts still consume the daily quota. Closing the remaining 1778 items on the free tier is therefore measured in days of wall-clock, not quota. If full ensemble coverage is required for the deliverable, a paid tier for one reliable judge (with the free models kept as opportunistic ensemble members) or an explicitly sampled coverage target are the two realistic options.
- Only two of the four configured judges have ever returned scores (nemotron-3-super, gpt-oss-20b — ~3460 each); llama-3.3-70b and qwen3-next-80b have congested out on every run so far and have contributed nothing.
- **Back-translation can hang silently.** The 07-31 run wedged mid-pass — process alive, no output, no error — and sat for two days before it was noticed and restarted. The pass is resumable so no scores were lost, but unattended/weekend runs need a watchdog or a progress-staleness check.
- Structural filter false positive: the truncation heuristic ("no terminal punctuation") fires on classification prompts that legitimately end with their inline option list, which is now the standard shape after the Week 6 options-inline fix. It cost 2 valid Hindi items in the 07-31 batch and will recur every batch until the heuristic or the template changes.
