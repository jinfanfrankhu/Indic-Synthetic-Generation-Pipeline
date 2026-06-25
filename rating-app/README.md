# Buttery — rating app

A tiny Next.js app for collecting **native-speaker ratings** of the synthetic Indic
data, used to validate the LLM judge against humans (see
[`../docs/gold_standard_protocol.md`](../docs/gold_standard_protocol.md)).

A rater enters an ID, picks a language, and rates ~20 items on three 1–4 axes:
**Naturalness** (source hidden), then **Meaning match** + **Cultural fit** (English
source revealed). Ratings are written to a **Neon Postgres** table.

## Stack
- Next.js (App Router) on **Vercel**
- **Neon** serverless Postgres via `@neondatabase/serverless`
- The blind item set ships in `public/rater_bundle.json` (no scores/answer key)

## Setup

1. **Install**
   ```bash
   cd rating-app
   npm install
   ```
2. **Database** — create the table once (Neon SQL editor, or psql):
   ```bash
   psql "$DATABASE_URL" -f lib/schema.sql
   ```
3. **Env** — copy `.env.example` to `.env.local` and paste your Neon **pooled**
   connection string into `DATABASE_URL`.
4. **Run locally**
   ```bash
   npm run dev      # http://localhost:3000
   ```

## Deploy (Vercel)
- Import the repo, set **Root Directory = `rating-app`**.
- Add the `DATABASE_URL` env var (same Neon string) in Project Settings → Environment Variables.
- Deploy. Share `https://<your-app>.vercel.app` with raters (one link; they pick their language).

## Refreshing the item set
`public/rater_bundle.json` is a copy of `data/gold/rater_bundle.json`. After a new
`syndata export-gold` run (e.g. re-scored with a better judge), refresh it:
```bash
cp ../data/gold/rater_bundle.json public/rater_bundle.json
```

## Getting ratings back out
Each row mirrors syndata's `ratings.jsonl` schema. Export for the κ analysis:
```bash
psql "$DATABASE_URL" -c "\copy (select task_id, rater_id, language, task_family, fluency, faithfulness, bias, unsure, comment, instructions_version, started_at, submitted_at from ratings) to 'ratings.csv' csv header"
```
Then join `task_id` against `data/gold/assignment_manifest.json` (the private answer key
with the judge scores) to compute judge-vs-human agreement.

## Notes
- **Blind by design:** the app only ever loads `rater_bundle.json`, which carries no
  scores, model names, or stratum. The answer key lives in the gitignored manifest.
- Per-item `started_at`/`submitted_at` are recorded for QC (implausibly fast = suspect).
- A rater re-rating the same item upserts (unique on `rater_id, task_id`).
