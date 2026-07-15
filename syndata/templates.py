"""
Prompt templates.

Each template turns a :class:`SeedItem` into a (system, user) message pair for
the teacher LLM. Templates are registered by name; ``GenerationConfig.
prompt_template_name`` selects which one runs.

Two strategies ship, mirroring the Week 2 design decision:

  - ``direct_translate`` — top-down: faithfully render the English seed in the
    target language. Best for reasoning / culture-agnostic tasks where meaning
    must be preserved exactly.
  - ``adapt_and_localize`` — bottom-up: re-express the task naturally for a
    speaker of the target language, localizing entities, registers, and (for
    classification) the label set. Best for culturally-grounded tasks.

Every template asks for a strict JSON object so the generator can map the
response onto ``SyntheticItem`` uniformly; ``generator.parse_response`` salvages
malformed output. Templates also bake in the known failure modes from
``data/seeds/sample_data.json`` (no code-switching, no literal word-for-word
mistranslation, localized labels only).
"""
from __future__ import annotations

import re
from typing import Callable

from .data_structures import SeedItem, TaskFamily

# ISO code -> (english name, native name). Covers Buttery's four targets.
LANGUAGE_NAMES: dict[str, tuple[str, str]] = {
    "hi": ("Hindi", "हिन्दी"),
    "ur": ("Urdu", "اردو"),
    "ta": ("Tamil", "தமிழ்"),
    "ml": ("Malayalam", "മലയാളം"),
}

# A template maps (seed, target-language english name) -> (system, user).
PromptBuilder = Callable[[SeedItem, str], tuple[str, str]]

_REGISTRY: dict[str, PromptBuilder] = {}


def register(name: str) -> Callable[[PromptBuilder], PromptBuilder]:
    def deco(fn: PromptBuilder) -> PromptBuilder:
        _REGISTRY[name] = fn
        return fn
    return deco


def get_template(name: str) -> PromptBuilder:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown prompt template {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def language_name(iso_code: str) -> str:
    """English name for an ISO code, or the code itself if unknown."""
    return LANGUAGE_NAMES.get(iso_code, (iso_code, iso_code))[0]


# Default strategy per task family. Culture-agnostic / answer-bearing tasks
# translate top-down; open-ended and label tasks adapt-and-localize.
DEFAULT_TEMPLATE: dict[TaskFamily, str] = {
    TaskFamily.REASONING: "direct_translate",
    TaskFamily.QA: "direct_translate",
    TaskFamily.SUMMARIZATION: "direct_translate",
    TaskFamily.TRANSLATION: "translation_task",
    TaskFamily.INSTRUCTION: "adapt_and_localize",
    TaskFamily.CLASSIFICATION: "adapt_and_localize",
}


def default_template_for(task: TaskFamily) -> str:
    return DEFAULT_TEMPLATE.get(task, "direct_translate")


# Shared guardrails distilled from the bad-generation examples.
_GUARDRAILS = (
    "Hard rules:\n"
    "- Write ENTIRELY in {lang}. Do not leave any English words in the text "
    "(no code-switching).\n"
    "- Translate meaning, not words. Never produce a literal word-for-word "
    "rendering that loses the sense.\n"
    "- Output ONLY a single JSON object, no markdown fences, no commentary."
)


def _json_contract(include_expected: bool) -> str:
    if include_expected:
        return (
            'Return JSON: {{"prompt": "<the task, in {lang}>", '
            '"expected": "<the answer, in {lang}>"}}'
        )
    return 'Return JSON: {{"prompt": "<the task, in {lang}>", "expected": ""}}'


def _classification_label_rule(labels: list[str], lang: str) -> str:
    """Instruction forcing the localized option list *into the generated prompt*.

    A classification item whose prompt doesn't show its options is unanswerable:
    the label set lives only in metadata, so the model has nothing to choose from.
    That was the biggest format-failure bucket in the 2026-07-13 review
    (docs/error_taxonomy.md). Passing the labels to the teacher isn't enough — it
    inlined them only ~95% of the time — so make it an explicit hard rule.
    """
    return (
        f"\nLabel set: {labels}\n"
        f"Classification rules (all mandatory):\n"
        f"- Localize each label into {lang}.\n"
        f'- The "prompt" MUST end with the localized options listed inline, e.g. '
        f'"(...: <label1>, <label2>, ...)" — a reader seeing only "prompt" must know '
        f"every choice available.\n"
        f'- "expected" MUST be exactly one of those localized labels, copied '
        f"character-for-character as it appears in the list."
    )


@register("direct_translate")
def direct_translate(seed: SeedItem, lang: str) -> tuple[str, str]:
    """Top-down faithful translation of the seed into the target language."""
    has_answer = seed.expected is not None
    system = (
        f"You are an expert {lang} translator producing instruction-tuning data. "
        "Faithfully render the given English task in natural, fluent {lang}, "
        "preserving its exact meaning, difficulty, and any reasoning steps.\n"
        + _GUARDRAILS
    ).format(lang=lang)

    parts = [f"English task:\n{seed.prompt}"]
    if has_answer:
        parts.append(f"\nReference answer (English): {seed.expected}")
    if seed.task_family == TaskFamily.CLASSIFICATION and seed.labels:
        parts.append(_classification_label_rule(seed.labels, lang))
    parts.append("\n" + _json_contract(has_answer).format(lang=lang))
    return system, "\n".join(parts)


def _extract_source(seed_prompt: str) -> str:
    """Pull the English sentence out of a translation seed prompt.

    Translation seeds are shaped ``Translate to the target language: '<sentence>'``.
    Return the quoted sentence; fall back to whatever follows a leading
    ``Translate ...:`` instruction so a differently-worded seed still works.
    """
    m = re.search(r"['\"](.+)['\"]", seed_prompt, re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return re.sub(r"^\s*translate\b[^:]*:\s*", "", seed_prompt, flags=re.I).strip().strip("'\"")


@register("translation_task")
def translation_task(seed: SeedItem, lang: str) -> tuple[str, str]:
    """Build a genuine translation exercise from a translation seed.

    ``direct_translate`` is wrong for the translation family: asked to "render the
    English task in {lang}" when the task is *itself* "translate X into [target]",
    the teacher either translated the whole sentence into the prompt and obeyed the
    ``expected: ""`` contract (blank answer), or echoed it into both fields — ~36%
    of Week-5 translation items. Here the English source is kept verbatim in the
    prompt and the model must supply its {lang} translation as a non-empty answer.
    """
    source = _extract_source(seed.prompt)
    system = (
        "You are an expert English-to-{lang} translator creating instruction-tuning "
        "data. You are given one English sentence. Return a single JSON object:\n"
        '  {{"prompt": "<an instruction in {lang} telling the reader to translate the '
        "sentence into {lang}, keeping the English sentence EXACTLY as given inside "
        'single quotes>", "expected": "<your faithful, fluent {lang} translation>"}}\n'
        "Hard rules:\n"
        '- The English sentence must appear unchanged inside "prompt" (do not '
        "translate it there).\n"
        '- "expected" is the {lang} translation, written entirely in {lang}, and must '
        "not be empty.\n"
        '- "expected" must not equal "prompt".\n'
        "- Output ONLY the JSON object — no markdown fences, no commentary."
    ).format(lang=lang)
    user = "English sentence to translate into {lang}: '{source}'".format(lang=lang, source=source)
    return system, user


@register("adapt_and_localize")
def adapt_and_localize(seed: SeedItem, lang: str) -> tuple[str, str]:
    """Bottom-up: re-express the task naturally for a {lang} speaker."""
    has_answer = seed.expected is not None
    system = (
        f"You are a native {lang} writer creating instruction-tuning data. "
        "Re-express the English task as a {lang} speaker would naturally pose it: "
        "localize names, places, registers, and examples where appropriate, while "
        "keeping the task's intent and difficulty.\n" + _GUARDRAILS
    ).format(lang=lang)

    parts = [f"English task to adapt:\n{seed.prompt}"]
    if has_answer:
        parts.append(f"\nReference answer (English): {seed.expected}")
    if seed.task_family == TaskFamily.CLASSIFICATION and seed.labels:
        parts.append(_classification_label_rule(seed.labels, lang))
    parts.append("\n" + _json_contract(has_answer).format(lang=lang))
    return system, "\n".join(parts)
