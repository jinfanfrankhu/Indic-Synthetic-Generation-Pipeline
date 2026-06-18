"""
Model bake-off.

Run the same seeds through several teacher models and emit a side-by-side
Markdown report so output quality (script naturality, JSON adherence, answer
localization) can be eyeballed directly. Used to pick the teacher model from
evidence rather than model-card claims.

Each (seed, model) generation is isolated: if one model errors (bad key, wrong
id, timeout), its cell records the error and the rest of the report still
renders.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .client import build_client
from .data_structures import GenerationConfig, SeedItem, SyntheticItem
from .generator import generate
from .templates import default_template_for, language_name


def _log(msg: str, verbose: bool) -> None:
    """Progress to stderr (keeps stdout clean for the report path)."""
    if verbose:
        print(msg, file=sys.stderr, flush=True)


@dataclass
class Cell:
    """One model's result for one seed — either an item or an error string."""
    item: SyntheticItem | None
    error: str | None


def run_comparison(
    seeds: list[SeedItem],
    models: list[str],
    language: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    template: str | None = None,
    verbose: bool = True,
    max_workers: int = 8,
    request_timeout: float | None = None,
) -> dict[str, dict[str, Cell]]:
    """Generate every ``seed`` with every ``model``, concurrently.

    Returns ``{seed_id: {model: Cell}}``. Clients are built once per model;
    a build failure (e.g. missing key) is recorded against every cell for that
    model rather than aborting the run. The (seed × model) calls are I/O-bound,
    so they run in a thread pool (``max_workers``); set ``max_workers=1`` to
    serialize (e.g. to stay under a tight rate limit). With ``verbose``
    (default), each call's outcome and elapsed time is logged to stderr as it
    completes — order is non-deterministic under concurrency.
    """
    clients: dict[str, object] = {}
    build_errors: dict[str, str] = {}
    client_kwargs = {} if request_timeout is None else {"timeout": request_timeout}
    for model in models:
        try:
            clients[model] = build_client(model, **client_kwargs)
            _log(f"[client] ready: {model}", verbose)
        except Exception as err:  # noqa: BLE001 — surface, don't abort
            build_errors[model] = f"client init failed: {err}"
            _log(f"[client] FAILED: {model} -> {err}", verbose)

    results: dict[str, dict[str, Cell]] = {seed.id: {} for seed in seeds}

    # Build the work list, recording build-failed models up front.
    tasks: list[tuple[SeedItem, str, GenerationConfig]] = []
    for seed in seeds:
        tmpl = template or default_template_for(seed.task_family)
        for model in models:
            if model in build_errors:
                results[seed.id][model] = Cell(item=None, error=build_errors[model])
                continue
            tasks.append((seed, model, GenerationConfig(
                seed_id=seed.id,
                target_language=language,
                teacher_model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_template_name=tmpl,
            )))

    if not tasks:
        return results

    def _call(seed: SeedItem, model: str, config: GenerationConfig) -> tuple[SyntheticItem, float]:
        start = time.monotonic()
        item = generate(seed, config, clients[model])  # type: ignore[arg-type]
        return item, time.monotonic() - start

    total = len(tasks)
    workers = max(1, min(max_workers, total))
    _log(f"dispatching {total} calls across {workers} workers...", verbose)

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_call, s, m, c): (s.id, m) for (s, m, c) in tasks}
        for fut in as_completed(futures):  # main thread — no lock needed for `done`
            seed_id, model = futures[fut]
            done += 1
            try:
                item, elapsed = fut.result()
                results[seed_id][model] = Cell(item=item, error=None)
                preview = item.prompt[:60].replace("\n", " ")
                _log(f"[{done}/{total}] ✓ {model} on {seed_id} in {elapsed:.1f}s — {preview}", verbose)
            except Exception as err:  # noqa: BLE001
                results[seed_id][model] = Cell(item=None, error=str(err))
                _log(f"[{done}/{total}] ✗ {model} on {seed_id} failed — {err}", verbose)
    return results


def render_markdown(
    seeds: list[SeedItem],
    models: list[str],
    results: dict[str, dict[str, Cell]],
    language: str,
) -> str:
    """Render the comparison as a Markdown document."""
    lang = language_name(language)
    lines = [
        f"# Teacher bake-off — {lang} (`{language}`)",
        "",
        f"Models compared: {', '.join(f'`{m}`' for m in models)}",
        "",
    ]
    for seed in seeds:
        lines.append(f"## {seed.id} — {seed.task_family.value}")
        lines.append("")
        lines.append(f"**English seed:** {seed.prompt}")
        if seed.expected:
            lines.append(f"  ")
            lines.append(f"**Reference answer:** {seed.expected}")
        lines.append("")
        for model in models:
            cell = results[seed.id][model]
            lines.append(f"### `{model}`")
            if cell.error:
                lines.append(f"> ⚠️ ERROR: {cell.error}")
            elif cell.item:
                lines.append(f"- **prompt:** {cell.item.prompt}")
                lines.append(f"- **expected:** {cell.item.expected}")
            lines.append("")
    return "\n".join(lines)


def write_report(content: str, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path
