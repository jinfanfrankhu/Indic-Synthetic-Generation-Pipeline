# Weekend automation — status & handoff (set up Thu 2026-07-02)

Durable record of the unattended weekend runs (Jul 3–5) so nothing depends on chat memory.

## Scheduled tasks (Windows Task Scheduler)
- **ButteryTranslationRegen** — Fri 2026-07-03 03:15 ET, one-shot, self-unregisters.
  Runs `tools/regen_translation.ps1`: cleans the 57 broken translation items
  (empty/echo) then re-drips translation with the corrected `translation_task`
  template (uses Gemini teacher; needs the day's fresh 500 RPD quota).
- **ButteryWeekendRun** — 9 AM & 3 PM ET, Fri/Sat/Sun (6 bounded `-Once` triggers).
  Runs `tools/weekend_run.ps1`: back-translation (local NLLB) → judge drip
  (OpenRouter free) → `tools/audit.py` → read-only `claude -p` interpretation →
  commit to `weekend-batch` → **guaranteed email** to jinfanfrank@gmail.com.

## Scoring
- **Back-translation** = local NLLB-200 (`facebook/nllb-200-distilled-1.3B`),
  deliberately NOT the Gemini teacher (independence + literalness; see
  `docs/lit_review.md`, DESIGN.md Q5). Score-only. Output: `data/filtered/backtranslation_scores.jsonl`.
  Full run of ~800 non-translation items started Thu ~12:00 ET (~5 hr on CPU;
  ~25 s/item for long items). Resumable via `tools/score_backtranslation.py`.
- **LLM-judge** = ensemble via OpenRouter free tier, `tools/score_judge.py`.
  Output: `data/filtered/judge_scores.jsonl`. Resumable per (item, judge),
  budget-capped (900 attempts/UTC-day, ledger `tools/judge_ledger.json`),
  congestion-aware (drops a judge after 4 consecutive fails, retries next run).

## Judge panel — WHY effectively 2 right now
Picked 4 decorrelated, non-teacher judges:
- `openrouter:nvidia/nemotron-3-super-120b-a12b:free` — reliable (matches DESIGN panel)
- `openrouter:openai/gpt-oss-20b:free` — reliable
- `openrouter:meta-llama/llama-3.3-70b-instruct:free` — **best-effort (429-congested)**
- `openrouter:qwen/qwen3-next-80b-a3b-instruct:free` — **best-effort (429-congested)**

Only 2 respond reliably on the free tier (popular free models are provider-429
throttled). The other 2 free reliable models were more NVIDIA Nemotron variants
(same family → not decorrelated), so the free roster gives 2 distinct reliable
families. Best-effort judges add coverage as congestion clears over the weekend.
**To guarantee 3–4:** point llama/qwen at their PAID endpoints (drop `:free`) in
`DEFAULT_JUDGES` — pennies from the $10 OpenRouter deposit.

## Known state / caveats
- Judges score good items ~0.98 (leniency expected; discrimination validated on
  English controls per DESIGN). Calibrated against the human gold set later.
- Translation family is broken (57 items) until the Fri 3:15 regen clears it.
- Everything lands on **`weekend-batch`**, never `main`.
- Safety backstop: `.claude/settings.local.json` denies push/reset/rm/curl/hf/webfetch
  for the read-only weekend agent.

## Monday
1. Write METHODOLOGY.md results section from the weekend numbers (`<!-- TODO -->` markers).
2. Review `weekend-batch` diffs + the 6 emails; merge to `main`.
3. If best-effort judge coverage is thin, switch llama/qwen to paid + top up.

## Check / cancel
```powershell
Get-ScheduledTaskInfo -TaskName 'ButteryWeekendRun'
Unregister-ScheduledTask -TaskName 'ButteryWeekendRun','ButteryTranslationRegen' -Confirm:$false
```
