"""
Back-translation consistency filter (API-backed; score-only).

The idea (SPEC.md, R1.3): a faithful generation, translated *back* to English,
should land close in meaning to the English seed it came from. We back-translate
the generated target-language text with the teacher, embed both the seed and the
back-translation in a shared multilingual space, and score their cosine similarity.
A low score means meaning drifted in generation — a reject signal.

Like the LLM judge, this is a **subjective** score with no defensible cutoff until
calibrated against the human gold set, so ``evaluate`` is **non-rejecting**
(``passed=True``) and carries the cosine in ``score``. See DESIGN.md Q3/Q5 and
``docs/gold_standard_protocol.md`` ("two kinds of filter").

**Dependency boundary.** The similarity model (SBERT / PyTorch) is *heavy* and
*optional*. This module imports nothing from ``sentence_transformers`` at import
time: the filter takes an injectable :class:`Embedder`, so its logic is testable
with a tiny fake and the base package stays light. The real model lives in
:class:`SbertEmbedder`, which imports ``sentence_transformers`` lazily (only when
instantiated) and ships behind the ``backtranslation`` optional extra
(``pip install -e .[backtranslation]``). Why embedding cosine over BERTScore or
spBLEU/ChrF: back-translation paraphrases heavily, so surface n-gram overlap punishes
valid paraphrase; meaning-level cosine is the right granularity (``docs/lit_review.md``).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from ..client import ChatClient
from ..data_structures import QualityFilter, QualityFilterResult, SeedItem, SyntheticItem

# Default multilingual checkpoint: distilled to place a sentence and its translation
# in a shared space, covers all four target scripts, fast. Pinned for reproducibility.
DEFAULT_SBERT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@runtime_checkable
class Embedder(Protocol):
    """Anything that maps texts to fixed-length vectors. Keeps SBERT injectable."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 if either is degenerate."""
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class SbertEmbedder:
    """Real :class:`Embedder` backed by sentence-transformers (lazy, optional dep).

    Importing this module does **not** import torch; only constructing this class
    does. Requires the ``backtranslation`` extra.
    """

    def __init__(self, model_name: str = DEFAULT_SBERT_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as err:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "SbertEmbedder needs the 'backtranslation' extra: "
                "pip install -e .[backtranslation]"
            ) from err
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=False)
        return [list(map(float, v)) for v in vecs]


def _back_translation_prompt(item: SyntheticItem) -> tuple[str, str]:
    """(system, user) asking the teacher to render the generated text back into English."""
    system = (
        "You are a precise translator. Translate the text the user gives you into "
        "natural English. Preserve meaning exactly; do not answer, explain, or add "
        "anything. Output only the English translation."
    )
    text = item.prompt or ""
    if item.expected:
        text = f"{text}\n{item.expected}"
    return system, text


class BackTranslationFilter(QualityFilter):
    name = "back_translation"

    def __init__(
        self,
        translator_model: str,
        seed_lookup: dict[str, SeedItem],
        embedder: Embedder,
        *,
        client: ChatClient | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> None:
        self.translator_model = translator_model
        self.seed_lookup = seed_lookup
        self.embedder = embedder
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Lazy client build keeps the package importable without `openai`; reused so
        # the shared rate limiter paces back-translation calls under the account cap.
        if client is None:
            from ..client import build_client

            client = build_client(translator_model)
        self.client = client

    def back_translate(self, item: SyntheticItem) -> str:
        """Translate the generated target-language text back to English."""
        system, user = _back_translation_prompt(item)
        return self.client.complete(
            model=self.translator_model, system=system, user=user,
            temperature=self.temperature, max_tokens=self.max_tokens,
        ).strip()

    def similarity(self, item: SyntheticItem, seed: SeedItem) -> tuple[float, str]:
        """Back-translate ``item`` and return (cosine vs seed, the back-translation)."""
        bt = self.back_translate(item)
        seed_text = seed.prompt + (f"\n{seed.expected}" if seed.expected else "")
        seed_vec, bt_vec = self.embedder.encode([seed_text, bt])
        return cosine(seed_vec, bt_vec), bt

    def evaluate(self, item: SyntheticItem) -> QualityFilterResult:
        """Scalar, non-rejecting verdict for :class:`FilterChain` composition.

        Always ``passed=True`` (score-only): no defensible cosine cutoff exists until
        calibrated against the gold set. On a missing seed or a translator error we
        still pass (score 0.0) with a reason, so a flaky API can't silently drop items.
        """
        seed = self.seed_lookup.get(item.seed_id)
        if seed is None:
            return QualityFilterResult(
                item_id=item.id, filter_name=self.name, passed=True, score=0.0,
                reason=f"no seed {item.seed_id!r} for item", timestamp=datetime.now(timezone.utc),
            )
        try:
            cos, bt = self.similarity(item, seed)
        except Exception as err:  # noqa: BLE001 — isolate a translator/embedder failure
            return QualityFilterResult(
                item_id=item.id, filter_name=self.name, passed=True, score=0.0,
                reason=f"back-translation unavailable: {err}",
                timestamp=datetime.now(timezone.utc),
            )
        return QualityFilterResult(
            item_id=item.id, filter_name=self.name, passed=True, score=cos,
            reason=f"score-only (cos={cos:.2f} vs seed); not enforced",
            timestamp=datetime.now(timezone.utc),
        )
