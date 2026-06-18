"""
Command-line interface.

    syndata generate --language hi --task qa --n 50 \
        --teacher qwen/qwen3-5-122b --judge meta/llama-3.3-70b-instruct

Week 3 scope is generation only: load seeds, call the teacher, write valid
``SyntheticItem`` records to JSONL. The ``--judge`` model is accepted and
recorded for provenance but not yet invoked — quality filtering lands in Week 4.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from itertools import islice, cycle
from pathlib import Path

from .client import build_client
from .data_structures import GenerationConfig, TaskFamily
from .generator import generate
from .seeds import DEFAULT_SEED_PATH, filter_by_task, load_seeds
from .templates import default_template_for

DEFAULT_OUTPUT_DIR = Path("data") / "generated"
DOCS_DIR = Path("docs")


def _model_slug(model: str) -> str:
    """Filesystem-safe model id, e.g. ``qwen/qwen3.5-122b-a10b`` -> ``qwen_qwen3.5-122b-a10b``."""
    return model.replace("/", "_")


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
    return parser


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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
