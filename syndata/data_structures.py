"""
Synthetic data generation pipeline — data structures.

These Pydantic v2 models define the contract between pipeline stages.
Serialize them to JSONL for storage; deserialize them when chaining stages
or when publishing to HuggingFace.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Task taxonomy
# ---------------------------------------------------------------------------

class TaskFamily(str, Enum):
    INSTRUCTION = "instruction"            # open-ended instruction-following
    QA = "qa"                              # short-answer question answering
    CLASSIFICATION = "classification"      # pick a label from a fixed set
    SUMMARIZATION = "summarization"        # condense longer text
    TRANSLATION = "translation"            # bidirectional translation seeds
    REASONING = "reasoning"                # multi-step reasoning chains


# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------

class LanguageConfig(BaseModel):
    """One target language for generation."""
    iso_code: str             # e.g. "sw" (Swahili), "tl" (Tagalog), "qu" (Quechua)
    native_name: str          # how speakers refer to it: "Kiswahili", "Tagalog", "Runa Simi"
    english_name: str
    script: str               # "Latin", "Devanagari", etc.
    teacher_model: str        # NVIDIA Build model ID used as generator
    judge_model: str          # different model used as quality judge
    # Free-form notes — corpora available, known LLM weaknesses, etc.
    notes: str = ""


# ---------------------------------------------------------------------------
# Seed and synthetic items
# ---------------------------------------------------------------------------

class SeedItem(BaseModel):
    """One English seed task that drives generation in target languages."""
    id: str
    task_family: TaskFamily
    prompt: str
    expected: Optional[str] = None     # for QA / classification, the answer in English
    metadata: dict[str, Any] = Field(default_factory=dict)
    # If task is classification, the label set.
    labels: Optional[list[str]] = None


class GenerationConfig(BaseModel):
    """Parameters for one generation pass."""
    seed_id: str
    target_language: str               # ISO code
    teacher_model: str
    temperature: float = 0.7
    max_tokens: int = 1024
    prompt_template_name: str          # e.g. "direct_translate", "adapt_and_localize"


class SyntheticItem(BaseModel):
    """One generated item in a target language, with full provenance."""
    id: str
    seed_id: str                       # provenance back to the English seed
    task_family: TaskFamily
    target_language: str               # ISO code
    prompt: str                        # the prompt in the target language
    expected: Optional[str] = None     # answer in target language (for QA/classification)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Full provenance — what model, what params, when
    generation: GenerationConfig
    generated_at: datetime
    # Raw LLM response (kept for audit)
    raw_response: str


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

class QualityAxis(str, Enum):
    # Human raters score the same fluency/faithfulness/bias axes on a 1-4 ordinal
    # scale; see docs/gold_standard_protocol.md for the rater rubric and the
    # judge-vs-human agreement analysis these keys join on.
    FLUENCY = "fluency"                # is it natural-sounding in the target language?
    FAITHFULNESS = "faithfulness"      # does it preserve the seed's meaning/intent?
    FORMAT = "format"                  # does it follow the task format (e.g. valid label)?
    BIAS = "bias"                      # is it free of unwanted English-source cultural bias?
    CORRECTNESS = "correctness"        # for QA: is the answer correct?


class QualityScore(BaseModel):
    """Multi-axis quality assessment of one synthetic item."""
    item_id: str
    scores: dict[QualityAxis, float]   # 0.0 to 1.0 per axis
    judge_model: str                   # which model produced this score
    judge_rationale: Optional[str] = None
    overall: float                     # aggregate (mean, weighted, or worst — your call, document it)
    timestamp: datetime


class QualityFilterResult(BaseModel):
    """Outcome of running an item through a filter pass."""
    item_id: str
    filter_name: str                   # e.g. "llm_judge", "back_translation", "structural"
    passed: bool
    score: float                       # filter-specific score
    reason: Optional[str] = None       # why it failed (if applicable)
    timestamp: datetime


# ---------------------------------------------------------------------------
# Run-level metadata (audit + reproducibility)
# ---------------------------------------------------------------------------

class GenerationRun(BaseModel):
    """One end-to-end pipeline run."""
    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    target_languages: list[str]
    task_families: list[TaskFamily]
    teacher_model: str
    judge_model: str
    n_seeds: int
    n_generated: int
    n_passed_quality: int
    config_hash: str                   # hash of full config — for reproducibility
    notes: str = ""


# ---------------------------------------------------------------------------
# Dataset publication (HuggingFace dataset card metadata)
# ---------------------------------------------------------------------------

class DatasetMetadata(BaseModel):
    """Goes in the HuggingFace dataset card."""
    name: str
    description: str
    languages: list[str]
    task_families: list[TaskFamily]
    n_items: int
    license: str                       # e.g. "cc-by-sa-4.0"
    teacher_models: list[str]
    judge_models: list[str]
    quality_filters: list[str]
    known_limitations: list[str]
    citation: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Filter protocol (for documentation; implement in filters/)
# ---------------------------------------------------------------------------

class QualityFilter:
    """
    Abstract filter. Concrete filters live in `syndata.filters`.

    Implementations to ship:
      - LLMJudgeFilter — strong model rates fluency + faithfulness + format
      - BackTranslationFilter — translate back to English, score similarity
      - StructuralFilter — task-specific format checks (label set membership,
                          length bounds, presence of expected fields)
      - HeuristicFilter — language-detection (langdetect / fastText),
                          script validity, repetition detection

    Filters compose via AND (item must pass all enabled filters) — but
    document the per-filter pass rate so users can see what's filtering what.
    """

    name: str

    def evaluate(self, item: SyntheticItem) -> QualityFilterResult:
        raise NotImplementedError
