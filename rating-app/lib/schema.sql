-- Gold-standard rating store. Run once against your Neon database:
--   psql "$DATABASE_URL" -f lib/schema.sql
-- (or paste into the Neon SQL editor).
--
-- One row per rater × item. Mirrors syndata's ratings.jsonl schema so the
-- export below feeds straight into the judge-vs-human κ analysis.

create table if not exists ratings (
  id             bigserial primary key,
  task_id        text        not null,   -- == SyntheticItem.id (join key)
  rater_id       text        not null,
  language       text        not null,   -- hi | ur | ta | ml
  task_family    text,
  fluency        int         not null,   -- Naturalness, 1-4
  faithfulness   int         not null,   -- Meaning match, 1-4
  bias           int         not null,   -- Cultural fit, 1-4
  unsure         boolean     not null default false,
  comment        text,
  instructions_version text,
  started_at     timestamptz,            -- when the item was shown (QC: too-fast = suspect)
  submitted_at   timestamptz,
  created_at     timestamptz not null default now()
);

-- A rater shouldn't double-submit the same item; keep the latest if they do.
create unique index if not exists ratings_rater_task_uniq on ratings (rater_id, task_id);

create index if not exists ratings_task_idx on ratings (task_id);
create index if not exists ratings_lang_idx on ratings (language);
