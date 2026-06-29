"""Back-translation filter: logic exercised with a fake embedder + fake client (no torch)."""
from __future__ import annotations

import string

import pytest

from syndata.data_structures import SeedItem, TaskFamily
from syndata.filters.back_translation import BackTranslationFilter, SbertEmbedder, cosine


class CharFreqEmbedder:
    """Deterministic stand-in for SBERT: a-z frequency vector.

    Identical strings embed identically (cosine 1.0); strings sharing letters score
    high, disjoint-letter strings score low. Enough to test the wiring + cosine math
    without a real model.
    """

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            t = t.lower()
            out.append([float(t.count(c)) for c in string.ascii_lowercase])
        return out


class FakeClient:
    """ChatClient stub: returns a preset string, or raises if configured to."""

    def __init__(self, response: str = "", *, raises: bool = False) -> None:
        self.response = response
        self.raises = raises
        self.calls = 0

    def complete(self, *, model, system, user, temperature, max_tokens) -> str:
        self.calls += 1
        if self.raises:
            raise RuntimeError("translator boom")
        return self.response


def _seed(prompt="List three causes of the French Revolution.", expected=None):
    return SeedItem(id="seed-1", task_family=TaskFamily.INSTRUCTION, prompt=prompt, expected=expected)


# --- cosine helper -----------------------------------------------------------

def test_cosine_identical_is_one():
    assert cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_zero_vector_is_zero():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_length_mismatch_raises():
    with pytest.raises(ValueError):
        cosine([1.0], [1.0, 2.0])


# --- filter behavior ---------------------------------------------------------

def test_faithful_back_translation_scores_high(make_item):
    seed = _seed()
    # Teacher back-translates to (nearly) the seed text -> high cosine.
    client = FakeClient(response="List three causes of the French Revolution.")
    f = BackTranslationFilter("mock", {seed.id: seed}, CharFreqEmbedder(), client=client)
    result = f.evaluate(make_item(seed_id=seed.id, prompt="<hindi text>"))
    assert result.passed  # score-only, never rejects
    assert result.score > 0.95
    assert client.calls == 1


def test_drifted_back_translation_scores_low(make_item):
    seed = _seed(prompt="zzz qqq")  # disjoint letters from the back-translation below
    client = FakeClient(response="aeiou bcdfg")
    f = BackTranslationFilter("mock", {seed.id: seed}, CharFreqEmbedder(), client=client)
    result = f.evaluate(make_item(seed_id=seed.id))
    assert result.passed
    assert result.score < 0.2


def test_is_non_rejecting_even_when_score_low(make_item):
    seed = _seed(prompt="zzz")
    f = BackTranslationFilter("mock", {seed.id: seed}, CharFreqEmbedder(),
                              client=FakeClient(response="aaa"))
    assert f.evaluate(make_item(seed_id=seed.id)).passed is True


def test_missing_seed_passes_with_zero_score(make_item):
    f = BackTranslationFilter("mock", {}, CharFreqEmbedder(), client=FakeClient("x"))
    result = f.evaluate(make_item(seed_id="absent"))
    assert result.passed
    assert result.score == 0.0
    assert "no seed" in result.reason


def test_translator_error_passes_with_zero_score(make_item):
    seed = _seed()
    f = BackTranslationFilter("mock", {seed.id: seed}, CharFreqEmbedder(),
                              client=FakeClient(raises=True))
    result = f.evaluate(make_item(seed_id=seed.id))
    assert result.passed
    assert result.score == 0.0
    assert "unavailable" in result.reason


def test_back_translate_sends_generated_text(make_item):
    seed = _seed()
    client = FakeClient(response="some english")
    f = BackTranslationFilter("mock", {seed.id: seed}, CharFreqEmbedder(), client=client)
    bt = f.back_translate(make_item(seed_id=seed.id, prompt="जनरेटेड", expected="उत्तर"))
    assert bt == "some english"
    assert client.calls == 1


# --- dependency boundary -----------------------------------------------------

def _have_sbert() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(_have_sbert(), reason="backtranslation extra is installed")
def test_sbert_embedder_requires_extra():
    # Without the optional extra, constructing the real embedder must fail loudly
    # with an actionable message — never a bare ModuleNotFoundError mid-pipeline.
    with pytest.raises(ImportError, match="backtranslation"):
        SbertEmbedder()


def test_importing_filters_does_not_import_torch():
    # The whole point of the dependency boundary: importing the package is light.
    import sys
    import syndata.filters  # noqa: F401
    assert "torch" not in sys.modules
