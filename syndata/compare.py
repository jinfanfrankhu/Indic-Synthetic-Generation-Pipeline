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

from dataclasses import dataclass
from pathlib import Path

from .client import build_client
from .data_structures import GenerationConfig, SeedItem, SyntheticItem
from .generator import generate
from .templates import default_template_for, language_name


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
) -> dict[str, dict[str, Cell]]:
    """Generate every ``seed`` with every ``model``.

    Returns ``{seed_id: {model: Cell}}``. Clients are built once per model;
    a build failure (e.g. missing key) is recorded against every cell for that
    model rather than aborting the run.
    """
    clients: dict[str, object] = {}
    build_errors: dict[str, str] = {}
    for model in models:
        try:
            clients[model] = build_client(model)
        except Exception as err:  # noqa: BLE001 — surface, don't abort
            build_errors[model] = f"client init failed: {err}"

    results: dict[str, dict[str, Cell]] = {}
    for seed in seeds:
        row: dict[str, Cell] = {}
        tmpl = template or default_template_for(seed.task_family)
        for model in models:
            if model in build_errors:
                row[model] = Cell(item=None, error=build_errors[model])
                continue
            config = GenerationConfig(
                seed_id=seed.id,
                target_language=language,
                teacher_model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_template_name=tmpl,
            )
            try:
                item = generate(seed, config, clients[model])  # type: ignore[arg-type]
                row[model] = Cell(item=item, error=None)
            except Exception as err:  # noqa: BLE001
                row[model] = Cell(item=None, error=str(err))
        results[seed.id] = row
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
