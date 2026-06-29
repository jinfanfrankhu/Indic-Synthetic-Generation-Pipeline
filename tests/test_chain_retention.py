"""FilterChain composition + retention aggregation, no API."""
from __future__ import annotations

from syndata.filters import (
    FilterChain,
    LanguageIDFilter,
    StructuralFilter,
    render_markdown,
    summarize,
)


def _chain():
    return FilterChain([StructuralFilter(), LanguageIDFilter()])


def test_chain_runs_every_filter_and_ands_verdicts(make_item):
    verdict = _chain().evaluate(make_item())
    assert [r.filter_name for r in verdict.results] == ["structural", "language_id"]
    assert verdict.would_pass
    assert verdict.failed_filters() == []


def test_chain_would_pass_false_if_any_filter_fails(make_item):
    # English output: structural passes, language_id fails -> chain fails.
    item = make_item(prompt="What is the capital of India?", expected="New Delhi")
    verdict = _chain().evaluate(item)
    assert not verdict.would_pass
    assert verdict.failed_filters() == ["language_id"]


def test_short_circuit_stops_at_first_failure(make_item):
    item = make_item(prompt="   ")  # structural fails first
    verdict = FilterChain(
        [StructuralFilter(), LanguageIDFilter()], short_circuit=True
    ).evaluate(item)
    assert [r.filter_name for r in verdict.results] == ["structural"]


def test_summarize_groups_by_language_and_task(make_item):
    chain = _chain()
    items = [
        make_item(id="a", target_language="hi", task_family="qa"),
        make_item(id="b", target_language="hi", task_family="qa",
                  prompt="What is 2+2?", expected="four"),  # language_id fails
        make_item(id="c", target_language="ta", task_family="qa",
                  prompt="கேள்வி: தலைநகர்?", expected="சென்னை"),
    ]
    pairs = [(it, chain.evaluate(it)) for it in items]
    report = summarize(pairs)

    assert report.overall.n_items == 3
    assert report.overall.chain.passed == 2  # a and c pass, b fails
    assert report.by_language["hi"].chain.passed == 1
    assert report.by_language["hi"].chain.total == 2
    assert report.by_language["ta"].chain.rate == 1.0
    # structural passed on all three; language_id passed on two.
    assert report.overall.per_filter["structural"].passed == 3
    assert report.overall.per_filter["language_id"].passed == 2


def test_render_markdown_has_rows_and_headline(make_item):
    chain = _chain()
    pairs = [(make_item(), chain.evaluate(make_item()))]
    md = render_markdown(summarize(pairs))
    assert "# Filter Retention Report" in md
    assert "| Group | N | structural | language_id | Chain |" in md
    assert "## By language" in md
    assert "## By language × task" in md


def test_filter_column_order_follows_chain_order(make_item):
    report = summarize([(make_item(), _chain().evaluate(make_item()))])
    assert report.filter_names == ["structural", "language_id"]
