"""
Command-line interface.

    syndata generate --language hi --task qa --n 50 --teacher gemini:gemini-3.1-flash-lite

Subcommands fall into three groups:

  - **generation**: ``generate``, ``generate-drip`` (resilient serial fill),
    ``generate-batch`` (concurrent sweep), ``bootstrap-seeds`` (self-instruct seed
    expansion).
  - **quality**: ``filter`` (run the filter chain → per-item verdicts + retention
    report), ``judge-compare`` / ``judge-score`` (LLM-judge ensemble), ``export-gold``
    (assemble a blind human-rater bundle).
  - **evidence**: ``compare`` (model bake-off → Markdown).

Each ``cmd_*`` handler is thin: it parses args, wires modules from ``syndata.*``,
and writes artifacts. The heavy lifting lives in those modules, not here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from itertools import islice, cycle
from pathlib import Path

from .client import build_client
from .data_structures import GenerationConfig, TaskFamily
from .generator import generate
from .seeds import DEFAULT_SEED_PATH, filter_by_task, generated_seed_keys, load_seeds
from .templates import default_template_for

DEFAULT_OUTPUT_DIR = Path("data") / "generated"
GOLD_DIR = Path("data") / "gold"
# Filter verdicts live OUTSIDE data/generated so a later `filter` run (which
# recurses data/generated for *.jsonl) never re-ingests its own output as items.
FILTER_DIR = Path("data") / "filtered"
DOCS_DIR = Path("docs")


def _model_slug(model: str) -> str:
    """Filesystem-safe model id: ``gemini:gemini-2.5-flash`` -> ``gemini_gemini-2.5-flash``.

    Replaces both ``/`` and the ``provider:`` prefix's ``:`` (illegal in Windows paths).
    """
    return model.replace("/", "_").replace(":", "_")


def _run_path(language: str, task: TaskFamily, model: str) -> Path:
    """Non-clobbering output path: ``data/generated/<lang>/<task>/<model>_<ts>.jsonl``."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    return DEFAULT_OUTPUT_DIR / language / task.value / f"{_model_slug(model)}_{ts}.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="syndata")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate synthetic items from seeds.")
    gen.add_argument("--language", required=True, help="Target ISO code: hi, ur, ta, ml")
    gen.add_argument(
        "--task",
        required=True,
        choices=[t.value for t in TaskFamily],
        help="Task family to generate.",
    )
    gen.add_argument("--n", type=int, default=10, help="Number of items to generate.")
    gen.add_argument(
        "--teacher",
        default="mock",
        help="Teacher model id, or 'mock' for offline canned output.",
    )
    gen.add_argument(
        "--judge",
        default=None,
        help="Judge model id (recorded for provenance; not used until Week 4).",
    )
    gen.add_argument("--temperature", type=float, default=0.7)
    gen.add_argument("--max-tokens", type=int, default=1024)
    gen.add_argument(
        "--seeds", default=str(DEFAULT_SEED_PATH), help="Path to seed JSON file."
    )
    gen.add_argument(
        "--template",
        default=None,
        help="Prompt template override (default: chosen per task family).",
    )
    gen.add_argument(
        "--out",
        default=None,
        help="Output JSONL path (default: data/generated/<lang>/<task>/<model>_<timestamp>.jsonl).",
    )

    cmp = sub.add_parser(
        "compare", help="Bake-off: run the same seeds through several models."
    )
    cmp.add_argument("--language", required=True, help="Target ISO code: hi, ur, ta, ml")
    cmp.add_argument(
        "--task",
        required=True,
        choices=[t.value for t in TaskFamily],
        help="Task family to sample seeds from.",
    )
    cmp.add_argument(
        "--models",
        required=True,
        help="Comma-separated model ids to compare (e.g. qwen/...,sarvamai/sarvam-m).",
    )
    cmp.add_argument("--n", type=int, default=3, help="Number of seeds to run.")
    cmp.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Max concurrent API calls (1 = serialize, e.g. for tight rate limits).",
    )
    cmp.add_argument("--temperature", type=float, default=0.7)
    cmp.add_argument("--max-tokens", type=int, default=1024)
    cmp.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Per-request timeout in seconds (default: client default of 90).",
    )
    cmp.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    cmp.add_argument("--template", default=None, help="Prompt template override.")
    cmp.add_argument(
        "--out",
        default=None,
        help="Markdown report path (default: docs/model_comparison_<lang>_<task>.md).",
    )

    jc = sub.add_parser(
        "judge-compare",
        help="Validate judges: generate items, then score them across judge models.",
    )
    jc.add_argument("--language", required=True, help="Target ISO code: hi, ur, ta, ml")
    jc.add_argument(
        "--task", required=True, choices=[t.value for t in TaskFamily],
        help="Task family to sample seeds from.",
    )
    jc.add_argument(
        "--judges", required=True,
        help="Comma-separated judge model ids (e.g. sarvamai/sarvam-m,google/gemma-4-31b-it).",
    )
    jc.add_argument(
        "--teacher", default="deepseek-ai/deepseek-v4-flash",
        help="Model used to generate the items being judged.",
    )
    jc.add_argument("--n", type=int, default=2, help="Number of seeds to generate + judge.")
    jc.add_argument("--workers", type=int, default=6)
    jc.add_argument("--timeout", type=float, default=None, help="Per-request timeout (s).")
    # Reasoning judges (e.g. sarvam-m) spend many tokens on chain-of-thought
    # before the JSON; too low a budget truncates the answer. 1024 gives room.
    jc.add_argument("--max-tokens", type=int, default=1024)
    jc.add_argument(
        "--no-control", action="store_true",
        help="Skip the English-text control rows (a judge-discrimination check).",
    )
    jc.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    jc.add_argument(
        "--out", default=None,
        help="Markdown report path (default: docs/judge_comparison_<lang>_<task>.md).",
    )

    bs = sub.add_parser(
        "bootstrap-seeds",
        help="Self-instruct: expand the English seed pool with the teacher model.",
    )
    bs.add_argument(
        "--tasks", default="all",
        help="Comma-separated task families or 'all' (default: all 6).",
    )
    bs.add_argument("--n", type=int, default=200, help="Total new seeds (split across tasks).")
    bs.add_argument(
        "--teacher", default="deepseek-ai/deepseek-v4-flash",
        help="Model used to generate seeds (default: locked teacher).",
    )
    bs.add_argument("--per-call", type=int, default=8, help="Seeds requested per API call.")
    bs.add_argument(
        "--calls-per-minute", type=float, default=None,
        help="Pace teacher call starts (set for low-RPM providers like Gemini: 15 RPM).",
    )
    bs.add_argument(
        "--temperature", type=float, default=1.0,
        help="Higher than generation default — bootstrapping wants diversity.",
    )
    bs.add_argument("--max-tokens", type=int, default=1024)
    bs.add_argument(
        "--seeds", default=str(DEFAULT_SEED_PATH),
        help="Seed file used as few-shot exemplars.",
    )
    bs.add_argument(
        "--out", default=None,
        help="Output JSON (default: data/seeds/bootstrapped_<timestamp>.json).",
    )

    gb = sub.add_parser(
        "generate-batch",
        help="Sweep: generate items across many languages x tasks from a seed file.",
    )
    gb.add_argument(
        "--languages", default="hi,ur,ta,ml",
        help="Comma-separated ISO codes (default: all 4 targets).",
    )
    gb.add_argument(
        "--tasks", default="all",
        help="Comma-separated task families or 'all' (default: all 6).",
    )
    gb.add_argument(
        "--per-combo", type=int, default=8,
        help="Items per (language x task) combination.",
    )
    gb.add_argument(
        "--teacher", default="deepseek-ai/deepseek-v4-flash",
        help="Teacher model id (default: locked teacher).",
    )
    gb.add_argument(
        "--workers", type=int, default=4,
        help="Max concurrent calls; the rate limiter caps throughput regardless.",
    )
    gb.add_argument(
        "--calls-per-minute", type=float, default=36.0,
        help="Rate-limiter ceiling for call starts (lower if the account 429s).",
    )
    gb.add_argument("--temperature", type=float, default=0.7)
    gb.add_argument("--max-tokens", type=int, default=1024)
    gb.add_argument(
        "--seeds", default=str(DEFAULT_SEED_PATH),
        help="Seed file (point at a bootstrapped file for diversity).",
    )
    gb.add_argument(
        "--out-dir", default=str(DEFAULT_OUTPUT_DIR),
        help="Output root (default: data/generated).",
    )
    gb.add_argument(
        "--allow-dups", action="store_true",
        help="Disable the duplicate guard and allow regenerating a (seed, "
             "language, task) already present on disk. Off by default.",
    )

    js = sub.add_parser(
        "judge-score",
        help="Run the judge ensemble over a generated pool; persist ensemble + per-judge scores.",
    )
    js.add_argument(
        "--generated", default=str(DEFAULT_OUTPUT_DIR),
        help="Dir (recursed for *.jsonl) or a single JSONL file of generated items.",
    )
    js.add_argument(
        "--judges", required=True,
        help="Comma-separated judge model ids (the ensemble).",
    )
    js.add_argument("--aggregate", default="mean", choices=["mean", "median"])
    js.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    js.add_argument("--workers", type=int, default=6)
    js.add_argument(
        "--calls-per-minute", type=float, default=None,
        help="Pace each judge's call starts (set for low-RPM providers like Gemini).",
    )
    js.add_argument("--max-tokens", type=int, default=1024)
    js.add_argument("--timeout", type=float, default=None, help="Per-request timeout (s).")
    js.add_argument(
        "--out", default=None,
        help="Ensemble scores JSONL (default: data/gold/scores_<ts>.jsonl). "
             "Per-judge scores written alongside as *.per_judge.jsonl.",
    )

    eg = sub.add_parser(
        "export-gold",
        help="Assemble a blind rater bundle + private manifest from a judged pool.",
    )
    eg.add_argument(
        "--generated", default=str(DEFAULT_OUTPUT_DIR),
        help="Dir (recursed for *.jsonl) or a single JSONL file of generated items.",
    )
    eg.add_argument(
        "--scores", required=True,
        help="Ensemble scores JSONL produced by `judge-score`.",
    )
    eg.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    eg.add_argument(
        "--per-language", type=int, default=80,
        help="Target items per language in the gold set.",
    )
    eg.add_argument(
        "--normal-frac", type=float, default=0.6,
        help="Fraction sampled as 'normal'; the rest are judge-borderline.",
    )
    eg.add_argument("--raters-per-language", type=int, default=2)
    eg.add_argument(
        "--overlap", type=float, default=0.2,
        help="Fraction of items double-rated (needs >=2 raters/language).",
    )
    eg.add_argument(
        "--rng-seed", type=int, default=0,
        help="Seed for deterministic sampling + rater assignment.",
    )
    eg.add_argument("--bundle-id", default=None)
    eg.add_argument("--out-dir", default=str(GOLD_DIR))

    dr = sub.add_parser(
        "generate-drip",
        help="Resilient serial drip generation with escalating backoff (for throttled endpoints).",
    )
    dr.add_argument("--languages", default="hi,ur,ta,ml")
    dr.add_argument("--tasks", default="all")
    dr.add_argument(
        "--per-combo", type=int, default=8,
        help="Target items per (language x task); already-present items are skipped.",
    )
    dr.add_argument("--teacher", default="deepseek-ai/deepseek-v4-flash")
    dr.add_argument("--temperature", type=float, default=0.7)
    dr.add_argument("--max-tokens", type=int, default=1024)
    dr.add_argument(
        "--calls-per-minute", type=float, default=12.0,
        help="Gentle proactive pace between calls; backoff handles the rest.",
    )
    dr.add_argument(
        "--backoffs", default="60,300,900",
        help="Comma-separated escalating wait seconds on failure; last value repeats.",
    )
    dr.add_argument(
        "--max-attempts", type=int, default=6,
        help="Per-item attempts before skipping it and moving on.",
    )
    dr.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    dr.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    dr.add_argument(
        "--allow-dups", action="store_true",
        help="Disable the duplicate guard and allow regenerating a (seed, "
             "language, task) already present on disk (e.g. temperature "
             "augmentation). Off by default: each seed is generated at most once "
             "per language/task.",
    )

    ft = sub.add_parser(
        "filter",
        help="Run the quality-filter chain over a generated pool; log per-language retention.",
    )
    ft.add_argument(
        "--generated", default=str(DEFAULT_OUTPUT_DIR),
        help="Dir (recursed for *.jsonl) or a single JSONL file of generated items.",
    )
    ft.add_argument("--seeds", default=str(DEFAULT_SEED_PATH))
    ft.add_argument(
        "--judges", default=None,
        help="Comma-separated judge model ids to add the (score-only) LLM-judge pass. "
             "Omit to run the deterministic filters only (no API, no key needed).",
    )
    ft.add_argument("--aggregate", default="mean", choices=["mean", "median"])
    ft.add_argument(
        "--back-translate", default=None, metavar="MODEL",
        help="Add the back-translation filter using MODEL as translator + a local SBERT "
             "embedder. Requires the 'backtranslation' extra (pip install -e .[backtranslation]).",
    )
    ft.add_argument(
        "--sbert-model", default=None,
        help="Override the SBERT checkpoint used by --back-translate.",
    )
    ft.add_argument(
        "--lang-threshold", type=float, default=0.75,
        help="Min target-script confidence for the language-ID gate (spec default 0.75).",
    )
    ft.add_argument(
        "--calls-per-minute", type=float, default=None,
        help="Pace judge call starts (set for low-RPM providers like Gemini).",
    )
    ft.add_argument("--max-tokens", type=int, default=1024)
    ft.add_argument(
        "--verdicts", default=None,
        help="Per-item verdicts JSONL (default: data/filtered/verdicts_<ts>.jsonl).",
    )
    ft.add_argument(
        "--report", default=None,
        help="Retention Markdown report (default: docs/filter_retention_<ts>.md).",
    )
    return parser


def _resolve_tasks(spec: str) -> list[TaskFamily]:
    """Parse a --tasks value ('all' or a comma list) into TaskFamily members."""
    if spec.strip().lower() == "all":
        return list(TaskFamily)
    return [TaskFamily(t.strip()) for t in spec.split(",") if t.strip()]


def cmd_generate(args: argparse.Namespace) -> int:
    task = TaskFamily(args.task)
    seeds = filter_by_task(load_seeds(args.seeds), task)
    if not seeds:
        print(f"No seeds found for task '{task.value}' in {args.seeds}", file=sys.stderr)
        return 1

    template_name = args.template or default_template_for(task)
    client = build_client(args.teacher)

    # Cycle through available seeds to reach n (seed pool is small in Week 3).
    out_path = Path(args.out) if args.out else _run_path(args.language, task, args.teacher)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for i, seed in enumerate(islice(cycle(seeds), args.n)):
            config = GenerationConfig(
                seed_id=seed.id,
                target_language=args.language,
                teacher_model=args.teacher,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                prompt_template_name=template_name,
            )
            item = generate(seed, config, client)
            # Disambiguate ids when the seed pool is cycled more than once.
            if args.n > len(seeds):
                item.id = f"{item.id}-{i:04d}"
            fh.write(item.model_dump_json() + "\n")
            written += 1
            print(f"  [{written}/{args.n}] {item.id}", file=sys.stderr)

    print(f"Wrote {written} items to {out_path}")
    if args.judge:
        print(f"(judge '{args.judge}' recorded but not run — filtering is Week 4)")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from itertools import islice

    from .compare import render_markdown, run_comparison, write_report

    task = TaskFamily(args.task)
    seeds = list(islice(filter_by_task(load_seeds(args.seeds), task), args.n))
    if not seeds:
        print(f"No seeds found for task '{task.value}' in {args.seeds}", file=sys.stderr)
        return 1

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        print("No models given to --models.", file=sys.stderr)
        return 1

    print(f"Comparing {len(models)} models on {len(seeds)} {task.value} seeds...", file=sys.stderr)
    results = run_comparison(
        seeds, models, args.language,
        temperature=args.temperature, max_tokens=args.max_tokens, template=args.template,
        max_workers=args.workers, request_timeout=args.timeout,
    )
    report = render_markdown(seeds, models, results, args.language)

    out_path = Path(args.out) if args.out else (
        DOCS_DIR / f"model_comparison_{args.language}_{task.value}.md"
    )
    write_report(report, out_path)
    print(f"Wrote comparison report to {out_path}")
    return 0


def cmd_judge_compare(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    from .compare import write_report
    from .data_structures import GenerationConfig, SyntheticItem
    from .judge import JudgeTarget, render_markdown, run_judge_panel

    task = TaskFamily(args.task)
    seeds = list(islice(filter_by_task(load_seeds(args.seeds), task), args.n))
    if not seeds:
        print(f"No seeds found for task '{task.value}' in {args.seeds}", file=sys.stderr)
        return 1

    judges = [m.strip() for m in args.judges.split(",") if m.strip()]
    if not judges:
        print("No judges given to --judges.", file=sys.stderr)
        return 1

    # 1. Generate the items to be judged, using the teacher.
    print(f"Generating {len(seeds)} items with {args.teacher}...", file=sys.stderr)
    teacher = build_client(args.teacher)
    template_name = default_template_for(task)
    targets: list[JudgeTarget] = []
    for seed in seeds:
        config = GenerationConfig(
            seed_id=seed.id, target_language=args.language,
            teacher_model=args.teacher, prompt_template_name=template_name,
        )
        try:
            item = generate(seed, config, teacher)
        except Exception as err:  # noqa: BLE001 — skip a seed the teacher can't generate
            print(f"  skip {seed.id}: teacher failed ({err})", file=sys.stderr)
            continue
        targets.append(JudgeTarget(id=item.id, label="real", seed=seed, item=item))
        if not args.no_control:
            # Control: feed judges the raw English seed as if it were the output.
            # Fluency should score low — a discrimination sanity check.
            control = SyntheticItem(
                id=f"{item.id}-control", seed_id=seed.id, task_family=task,
                target_language=args.language, prompt=seed.prompt, expected=seed.expected,
                generation=config, generated_at=datetime.now(timezone.utc),
                raw_response="[control: raw English seed]",
            )
            targets.append(JudgeTarget(
                id=control.id, label="CONTROL: English text", seed=seed, item=control,
            ))

    if not targets:
        print("No items generated (teacher failed for every seed — likely rate-"
              "limited). Wait a bit and retry, or lower --workers.", file=sys.stderr)
        return 1

    # 2. Score every target with every judge.
    results = run_judge_panel(
        targets, judges, max_tokens=args.max_tokens,
        request_timeout=args.timeout, max_workers=args.workers,
    )
    report = render_markdown(targets, judges, results)
    out_path = Path(args.out) if args.out else (
        DOCS_DIR / f"judge_comparison_{args.language}_{task.value}.md"
    )
    write_report(report, out_path)
    print(f"Wrote judge comparison to {out_path}")
    return 0


def cmd_bootstrap_seeds(args: argparse.Namespace) -> int:
    from .bootstrap import bootstrap_seeds
    from .seeds import write_seeds

    tasks = _resolve_tasks(args.tasks)
    all_seeds = load_seeds(args.seeds)
    client_kwargs = (
        {"calls_per_minute": args.calls_per_minute}
        if args.calls_per_minute is not None else {}
    )
    client = build_client(args.teacher, **client_kwargs)

    # Split the requested total roughly evenly across task families.
    per_task = max(1, args.n // len(tasks))
    print(
        f"Bootstrapping ~{per_task} seeds x {len(tasks)} task(s) with "
        f"{args.teacher}...", file=sys.stderr,
    )

    collected: list = []
    summaries: list[str] = []
    for task in tasks:
        examples = filter_by_task(all_seeds, task)
        result = bootstrap_seeds(
            task, per_task, client, args.teacher, examples,
            per_call=args.per_call, temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        collected.extend(result.seeds)
        drops = ", ".join(f"{k}={v}" for k, v in sorted(result.drops.items())) or "none"
        summaries.append(
            f"  {task.value:14s} {len(result.seeds):4d}/{result.requested:<4d} accepted "
            f"(dropped: {drops})"
        )

    if not collected:
        print("No seeds produced (teacher failed or output unusable).", file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else (
        Path("data") / "seeds" / f"bootstrapped_{datetime.now():%Y%m%dT%H%M%S}.json"
    )
    write_seeds(collected, out_path)

    print("\n".join(summaries), file=sys.stderr)
    print(f"Wrote {len(collected)} seeds to {out_path}")
    print("Review/edit this file by hand before running `generate-batch` against it.")
    return 0


def cmd_generate_batch(args: argparse.Namespace) -> int:
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    languages = [c.strip() for c in args.languages.split(",") if c.strip()]
    tasks = _resolve_tasks(args.tasks)
    all_seeds = load_seeds(args.seeds)
    client = build_client(args.teacher, calls_per_minute=args.calls_per_minute)
    out_root = Path(args.out_dir)

    # Duplicate guard: never regenerate a (seed, language, task) already on disk,
    # and never schedule the same seed twice in one run (the seed pool's `cycle`
    # repeats once per_combo exceeds the unique seed count). `--allow-dups` opts out.
    seen = set() if args.allow_dups else generated_seed_keys(out_root)
    dup_skipped = 0

    # Build the work list: up to --per-combo distinct seeds per (language, task).
    jobs: list[tuple[str, TaskFamily, object, GenerationConfig]] = []
    for task in tasks:
        task_seeds = filter_by_task(all_seeds, task)
        if not task_seeds:
            print(f"  no seeds for task '{task.value}', skipping", file=sys.stderr)
            continue
        chosen = list(islice(cycle(task_seeds), args.per_combo))
        template_name = default_template_for(task)
        for lang in languages:
            for seed in chosen:
                key = (seed.id, lang, task.value)
                if not args.allow_dups and key in seen:
                    dup_skipped += 1
                    continue
                seen.add(key)
                config = GenerationConfig(
                    seed_id=seed.id, target_language=lang, teacher_model=args.teacher,
                    temperature=args.temperature, max_tokens=args.max_tokens,
                    prompt_template_name=template_name,
                )
                jobs.append((lang, task, seed, config))

    if dup_skipped:
        print(f"Duplicate guard: skipped {dup_skipped} already-generated "
              f"(seed, language, task) item(s). Use --allow-dups to override.",
              file=sys.stderr)

    if not jobs:
        print("No jobs to run (all matching seeds already generated, or none "
              "found).", file=sys.stderr)
        return 1

    total = len(jobs)
    workers = max(1, min(args.workers, total))
    print(
        f"Generating {total} items across {len(languages)} lang(s) x {len(tasks)} "
        f"task(s) with {args.teacher} ({workers} workers, rate-limited)...",
        file=sys.stderr,
    )

    def _call(seed, config):
        return generate(seed, config, client)

    def _path_for(lang: str, task_value: str) -> Path:
        out_path = _run_path(lang, TaskFamily(task_value), args.teacher)
        if args.out_dir != str(DEFAULT_OUTPUT_DIR):
            out_path = out_root / lang / task_value / out_path.name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return out_path

    # Stream each item to its (lang, task) file as it completes and flush, so a
    # throttled or interrupted run keeps whatever it already produced (rather than
    # buffering everything and writing only at the end — which loses all progress
    # if the account rate-limits mid-run).
    handles: dict[tuple[str, str], object] = {}
    counts: dict[tuple[str, str], int] = {}
    errors = 0
    done = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_call, seed, config): (lang, task)
                for (lang, task, seed, config) in jobs
            }
            for fut in as_completed(futures):
                lang, task = futures[fut]
                done += 1
                try:
                    item = fut.result()
                except Exception as err:  # noqa: BLE001 — isolate per-item failures
                    errors += 1
                    print(f"[{done}/{total}] ✗ {lang}/{task.value} failed — {err}",
                          file=sys.stderr)
                    continue
                key = (lang, task.value)
                if key not in handles:
                    handles[key] = _path_for(lang, task.value).open("w", encoding="utf-8")
                # Disambiguate when the same seed is reused within a combo.
                idx = counts.get(key, 0)
                item.id = f"{item.id}-{idx:03d}"
                handles[key].write(item.model_dump_json() + "\n")
                handles[key].flush()
                counts[key] = idx + 1
                preview = item.prompt[:50].replace("\n", " ")
                print(f"[{done}/{total}] ✓ {lang}/{task.value} {item.id} — {preview}",
                      file=sys.stderr)
    finally:
        for fh in handles.values():
            fh.close()

    written = sum(counts.values())

    print(f"\nWrote {written} items ({errors} failed) under {out_root}")
    print("Per (language x task):")
    for key in sorted(counts):
        print(f"  {key[0]:4s} {key[1]:14s} {counts[key]}")
    return 0


def _resolve_generated(spec: str) -> list[Path]:
    """A generated-items spec is either a single JSONL file or a dir to recurse."""
    p = Path(spec)
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(p.rglob("*.jsonl"))
    return []


def cmd_judge_score(args: argparse.Namespace) -> int:
    from .filters.llm_judge import aggregate_scores
    from .gold import load_items
    from .judge import JudgeTarget, run_judge_panel
    from .seeds import load_seeds

    paths = _resolve_generated(args.generated)
    if not paths:
        print(f"No generated JSONL found at {args.generated}", file=sys.stderr)
        return 1
    items = load_items(paths)
    seeds_by_id = {s.id: s for s in load_seeds(args.seeds)}

    targets: list[JudgeTarget] = []
    missing = 0
    for item in items:
        seed = seeds_by_id.get(item.seed_id)
        if seed is None:
            missing += 1
            continue
        targets.append(JudgeTarget(id=item.id, label="real", seed=seed, item=item))
    if not targets:
        print("No items with a matching seed to judge.", file=sys.stderr)
        return 1

    judges = [m.strip() for m in args.judges.split(",") if m.strip()]
    if not judges:
        print("No judges given to --judges.", file=sys.stderr)
        return 1
    print(
        f"Scoring {len(targets)} items with {len(judges)} judge(s) "
        f"({missing} skipped for missing seed)...", file=sys.stderr,
    )
    results = run_judge_panel(
        targets, judges, max_tokens=args.max_tokens,
        request_timeout=args.timeout, max_workers=args.workers,
        calls_per_minute=args.calls_per_minute,
    )

    ensemble_lines: list[str] = []
    per_judge_lines: list[str] = []
    scored = failed = 0
    for t in targets:
        cells = results[t.id]
        good = [c.score for c in cells.values() if c.score is not None]
        per_judge_lines.extend(c.score.model_dump_json() for c in cells.values() if c.score)
        if not good:
            failed += 1
            continue
        ensemble_lines.append(aggregate_scores(good, args.aggregate).model_dump_json())
        scored += 1

    out_path = Path(args.out) if args.out else (
        GOLD_DIR / f"scores_{datetime.now():%Y%m%dT%H%M%S}.jsonl"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(ensemble_lines) + "\n", encoding="utf-8")
    pj_path = out_path.parent / (out_path.stem + ".per_judge.jsonl")
    pj_path.write_text("\n".join(per_judge_lines) + "\n", encoding="utf-8")

    print(f"Scored {scored} items ({failed} had no usable judge output).")
    print(f"Ensemble scores -> {out_path}")
    print(f"Per-judge scores -> {pj_path}")
    return 0


def _combo_existing_count(out_root: Path, lang: str, task_value: str) -> int:
    """Count distinct item ids already on disk for a (language, task) combo."""
    import json

    combo_dir = out_root / lang / task_value
    if not combo_dir.exists():
        return 0
    ids: set[str] = set()
    for f in combo_dir.glob("*.jsonl"):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return len(ids)


def cmd_generate_drip(args: argparse.Namespace) -> int:
    import time

    languages = [c.strip() for c in args.languages.split(",") if c.strip()]
    tasks = _resolve_tasks(args.tasks)
    all_seeds = load_seeds(args.seeds)
    out_root = Path(args.out_dir)
    backoffs = [float(x) for x in args.backoffs.split(",") if x.strip()] or [60.0, 300.0, 900.0]
    # Fail-fast client: our loop owns retries/backoff, so disable the inner hammer
    # (max_retries=1) that otherwise keeps pounding a throttled endpoint.
    client = build_client(args.teacher, max_retries=1, calls_per_minute=args.calls_per_minute)
    teacher_slug = _model_slug(args.teacher)

    # Per-combo target seeds + how many already exist (for resumable fill).
    combos = []
    for task in tasks:
        task_seeds = filter_by_task(all_seeds, task)
        if not task_seeds:
            print(f"  no seeds for task '{task.value}', skipping", file=sys.stderr)
            continue
        chosen = list(islice(cycle(task_seeds), args.per_combo))
        template_name = default_template_for(task)
        for lang in languages:
            existing = _combo_existing_count(out_root, lang, task.value)
            combos.append((lang, task, chosen, template_name, existing))

    # Duplicate guard: never regenerate a (seed, language, task) already on disk,
    # and never let the seed pool's `cycle` schedule the same seed twice in one run
    # (which is how temperature near-duplicates crept in). `--allow-dups` opts out.
    seen = set() if args.allow_dups else generated_seed_keys(out_root)
    dup_skipped = 0

    # Index-major job list: fill position 0 across all combos, then 1, ... so even a
    # partial drip yields balanced coverage; skip positions already on disk.
    jobs = []
    for idx in range(args.per_combo):
        for (lang, task, chosen, template_name, existing) in combos:
            if idx < existing:
                continue
            seed = chosen[idx]
            key = (seed.id, lang, task.value)
            if not args.allow_dups and key in seen:
                dup_skipped += 1
                continue
            seen.add(key)
            config = GenerationConfig(
                seed_id=seed.id, target_language=lang, teacher_model=args.teacher,
                temperature=args.temperature, max_tokens=args.max_tokens,
                prompt_template_name=template_name,
            )
            jobs.append((lang, task, idx, seed, config))

    if dup_skipped:
        print(f"Duplicate guard: skipped {dup_skipped} already-generated "
              f"(seed, language, task) item(s). Use --allow-dups to override.",
              file=sys.stderr)

    if not jobs:
        print("Pool already at target — nothing to drip.")
        return 0

    total = len(jobs)
    print(
        f"Drip: filling {total} items (per_combo={args.per_combo}), serial with "
        f"escalating backoff {backoffs}s (last repeats), max {args.max_attempts} "
        f"attempts/item.", file=sys.stderr,
    )

    handles: dict[tuple[str, str], object] = {}

    def _handle(lang: str, task_value: str):
        key = (lang, task_value)
        if key not in handles:
            p = out_root / lang / task_value / f"drip_{teacher_slug}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            handles[key] = p.open("a", encoding="utf-8")  # append: resumable across runs
        return handles[key]

    done = success = skipped = 0
    try:
        for (lang, task, idx, seed, config) in jobs:
            done += 1
            attempt = 0
            while True:
                try:
                    item = generate(seed, config, client)
                    item.id = f"{item.id}-{idx:03d}"
                    fh = _handle(lang, task.value)
                    fh.write(item.model_dump_json() + "\n")
                    fh.flush()
                    success += 1
                    preview = item.prompt[:45].replace("\n", " ")
                    print(f"[{done}/{total}] ✓ {lang}/{task.value} #{idx} — {preview}",
                          file=sys.stderr, flush=True)
                    break
                except Exception as err:  # noqa: BLE001 — back off and retry the same item
                    attempt += 1
                    if attempt >= args.max_attempts:
                        skipped += 1
                        print(f"[{done}/{total}] ✗ {lang}/{task.value} #{idx} — gave up "
                              f"after {args.max_attempts} attempts ({err})",
                              file=sys.stderr, flush=True)
                        break
                    wait = backoffs[min(attempt - 1, len(backoffs) - 1)]
                    print(f"[{done}/{total}] … {lang}/{task.value} #{idx} attempt {attempt} "
                          f"failed; waiting {wait:.0f}s", file=sys.stderr, flush=True)
                    time.sleep(wait)
    finally:
        for fh in handles.values():
            fh.close()

    print(f"\nDrip complete: {success} generated, {skipped} skipped, of {total} targeted "
          f"under {out_root}")
    return 0


def cmd_export_gold(args: argparse.Namespace) -> int:
    import random

    from .gold import (
        build_bundle, build_manifest, load_items, load_scores, select_gold_set, write_json,
    )
    from .seeds import load_seeds

    paths = _resolve_generated(args.generated)
    if not paths:
        print(f"No generated JSONL found at {args.generated}", file=sys.stderr)
        return 1
    items = load_items(paths)
    scores = load_scores(Path(args.scores))
    seeds_by_id = {s.id: s for s in load_seeds(args.seeds)}

    rng = random.Random(args.rng_seed)
    selected = select_gold_set(
        items, scores, per_language=args.per_language,
        normal_frac=args.normal_frac, rng=rng,
    )
    if not selected:
        print("No scored items to sample (is --scores aligned with --generated?).",
              file=sys.stderr)
        return 1

    bundle_id = args.bundle_id or f"gold-{datetime.now():%Y%m%d}-all"
    bundle = build_bundle(selected, seeds_by_id, bundle_id=bundle_id)
    manifest = build_manifest(
        selected, scores, bundle_id=bundle_id,
        raters_per_language=args.raters_per_language, overlap_frac=args.overlap, rng=rng,
    )

    out_dir = Path(args.out_dir)
    write_json(bundle, out_dir / "rater_bundle.json")
    write_json(manifest, out_dir / "assignment_manifest.json")

    total = sum(len(v) for v in selected.values())
    print(f"Bundle '{bundle_id}': {total} items across {len(selected)} language(s)")
    for lang in sorted(selected):
        strata = [s for _, s in selected[lang]]
        n_overlap = sum(
            1 for a in manifest["assignments"]
            if a["overlap"] and a["task_id"] in {i.id for i, _ in selected[lang]}
        )
        print(f"  {lang}: {len(strata)} items "
              f"({strata.count('normal')} normal, {strata.count('borderline')} borderline; "
              f"{n_overlap} double-rated)")
    print(f"Wrote {out_dir / 'rater_bundle.json'} (blind) and "
          f"{out_dir / 'assignment_manifest.json'} (private)")
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    from .filters import (
        FilterChain, LanguageIDFilter, LLMJudgeFilter, StructuralFilter,
        render_markdown, summarize,
    )
    from .gold import load_items
    from .seeds import load_seeds

    paths = _resolve_generated(args.generated)
    if not paths:
        print(f"No generated JSONL found at {args.generated}", file=sys.stderr)
        return 1
    items = load_items(paths)
    seeds_by_id = {s.id: s for s in load_seeds(args.seeds)}

    # Deterministic gates first (free, no API); judge last (score-only, opt-in).
    filters = [StructuralFilter(), LanguageIDFilter(threshold=args.lang_threshold)]
    judges = [m.strip() for m in (args.judges or "").split(",") if m.strip()]
    if judges:
        clients = None
        if args.calls_per_minute is not None:
            clients = {
                j: build_client(j, calls_per_minute=args.calls_per_minute) for j in judges
            }
        filters.append(
            LLMJudgeFilter(
                judges, seeds_by_id, clients=clients,
                aggregate=args.aggregate, max_tokens=args.max_tokens,
            )
        )
    if args.back_translate:
        from .filters.back_translation import (
            DEFAULT_SBERT_MODEL, BackTranslationFilter, SbertEmbedder,
        )

        # SbertEmbedder raises an actionable ImportError if the extra is missing.
        try:
            embedder = SbertEmbedder(args.sbert_model or DEFAULT_SBERT_MODEL)
        except ImportError as err:
            print(err, file=sys.stderr)
            return 1
        bt_client = (
            build_client(args.back_translate, calls_per_minute=args.calls_per_minute)
            if args.calls_per_minute is not None else None
        )
        filters.append(
            BackTranslationFilter(
                args.back_translate, seeds_by_id, embedder,
                client=bt_client, max_tokens=args.max_tokens,
            )
        )
    chain = FilterChain(filters)

    filter_label = ", ".join(f.name for f in filters)
    print(
        f"Filtering {len(items)} items from {len(paths)} file(s) "
        f"through: {filter_label}", file=sys.stderr,
    )

    pairs = []
    missing_seed = 0
    for item in items:
        if item.seed_id not in seeds_by_id and judges:
            # The judge needs the seed; deterministic gates do not. Skip judge for
            # orphans by recording it, but still run the free gates.
            missing_seed += 1
        verdict = chain.evaluate(item)
        pairs.append((item, verdict))
    if missing_seed:
        print(f"  ({missing_seed} items had no matching seed; judge may be degraded for those)",
              file=sys.stderr)

    # Per-item verdicts JSONL (audit trail of every filter's call on every item).
    verdicts_path = Path(args.verdicts) if args.verdicts else (
        FILTER_DIR / f"verdicts_{datetime.now():%Y%m%dT%H%M%S}.jsonl"
    )
    verdicts_path.parent.mkdir(parents=True, exist_ok=True)
    with verdicts_path.open("w", encoding="utf-8") as fh:
        for item, verdict in pairs:
            fh.write(json.dumps({
                "item_id": item.id,
                "language": item.target_language,
                "task": item.task_family.value,
                "would_pass": verdict.would_pass,
                "failed": verdict.failed_filters(),
                "results": [
                    {"filter": r.filter_name, "passed": r.passed,
                     "score": round(r.score, 4), "reason": r.reason}
                    for r in verdict.results
                ],
            }, ensure_ascii=False) + "\n")

    # Retention report (the Week 4 exit artifact).
    report = summarize(pairs)
    report_path = Path(args.report) if args.report else (
        DOCS_DIR / f"filter_retention_{datetime.now():%Y%m%dT%H%M%S}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report), encoding="utf-8")

    # Console summary.
    o = report.overall
    print(f"\nChain retention: {o.chain.passed}/{o.chain.total} ({o.chain.rate:.0%}) survived all gates")
    for name in report.filter_names:
        st = o.per_filter[name]
        print(f"  {name:<12} {st.rate:5.0%} pass ({st.passed}/{st.total})")
    print("By language:")
    for lang in sorted(report.by_language):
        g = report.by_language[lang]
        print(f"  {lang}: {g.chain.rate:.0%} chain ({g.chain.passed}/{g.chain.total})")
    print(f"\nVerdicts -> {verdicts_path}")
    print(f"Retention report -> {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Load NVIDIA_API_KEY (and friends) from a local .env if present.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    args = _build_parser().parse_args(argv)
    if args.command == "generate":
        return cmd_generate(args)
    if args.command == "compare":
        return cmd_compare(args)
    if args.command == "judge-compare":
        return cmd_judge_compare(args)
    if args.command == "bootstrap-seeds":
        return cmd_bootstrap_seeds(args)
    if args.command == "generate-batch":
        return cmd_generate_batch(args)
    if args.command == "judge-score":
        return cmd_judge_score(args)
    if args.command == "export-gold":
        return cmd_export_gold(args)
    if args.command == "generate-drip":
        return cmd_generate_drip(args)
    if args.command == "filter":
        return cmd_filter(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
