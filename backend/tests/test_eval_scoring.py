"""The eval's arithmetic.

The harness itself needs Postgres and a paid API key, so it is run
deliberately rather than in CI. Its scoring does not: these are pure functions
over "what was expected" and "what came back", and they are the part that must
not be wrong. A metric that quietly miscounts turns the whole harness into a
confident source of false conclusions — worse than having no harness, because
the numbers get believed.
"""

import json
from pathlib import Path

import pytest

from eval.harness import CORPUS_DIR, load_corpus, load_questions
from eval.scoring import (
    QuestionResult,
    compare,
    precision,
    recall,
    reciprocal_rank,
    score,
)


def result(
    expected: list[str],
    retrieved: list[str],
    *,
    question_id: str = "q",
    kind: str = "direct",
    missing_phrases: list[str] | None = None,
    top_score: float | None = None,
) -> QuestionResult:
    return QuestionResult(
        question_id=question_id,
        kind=kind,
        expected_documents=expected,
        retrieved_documents=retrieved,
        top_score=top_score,
        missing_phrases=missing_phrases or [],
    )


def test_recall_is_the_share_of_expected_documents_found():
    assert recall(result(["refunds"], ["refunds", "shipping"])) == 1.0
    assert recall(result(["refunds", "warranty"], ["refunds", "shipping"])) == 0.5
    assert recall(result(["refunds"], ["shipping", "warranty"])) == 0.0


def test_recall_ignores_where_in_the_results_the_document_appeared():
    """Everything retrieved is fed to the model, so rank four still answers.

    Rank is measured by MRR instead. Conflating the two would hide a change
    that reorders results without changing what they contain.
    """
    early = result(["refunds"], ["refunds", "a", "b", "c"])
    late = result(["refunds"], ["a", "b", "c", "refunds"])

    assert recall(early) == recall(late) == 1.0
    assert reciprocal_rank(early) > reciprocal_rank(late)


def test_reciprocal_rank_uses_the_first_correct_position():
    assert reciprocal_rank(result(["refunds"], ["refunds", "shipping"])) == 1.0
    assert reciprocal_rank(result(["refunds"], ["shipping", "refunds"])) == 0.5
    assert reciprocal_rank(result(["refunds"], ["a", "b", "c", "refunds"])) == 0.25
    assert reciprocal_rank(result(["refunds"], ["shipping"])) == 0.0


def test_a_duplicate_document_does_not_inflate_recall():
    """Two chunks from one document are one document.

    Chunking changes how many chunks a document yields, so counting chunks
    would make a smaller chunk size look like better retrieval.
    """
    assert recall(result(["refunds"], ["refunds", "refunds", "refunds"])) == 1.0


def test_precision_counts_chunks_rather_than_documents():
    # Here the denominator *should* be chunks: precision is about how much of
    # the context window was spent on the right material.
    assert precision(result(["refunds"], ["refunds", "refunds", "shipping"])) == pytest.approx(2 / 3)
    assert precision(result(["refunds"], [])) == 0.0


def test_metrics_refuse_a_question_with_no_expected_source():
    """An unanswerable question has no correct document, so recall is undefined.

    Returning 0 would drag the average down for behaviour that is correct, and
    returning 1 would reward retrieving anything at all.
    """
    unanswerable = result([], ["shipping"])

    with pytest.raises(ValueError):
        recall(unanswerable)
    with pytest.raises(ValueError):
        reciprocal_rank(unanswerable)


def test_score_separates_unanswerable_questions_from_the_averages():
    report = score(
        [
            result(["refunds"], ["refunds"], question_id="a"),
            result(["shipping"], ["shipping"], question_id="b"),
            result([], ["refunds"], question_id="c", top_score=0.31),
        ]
    )

    assert report.answerable == 2
    assert report.unanswerable == 1
    assert report.recall_at_k == 1.0
    assert report.unanswerable_top_scores == [0.31]


def test_score_reports_which_questions_retrieved_nothing_relevant():
    report = score(
        [
            result(["refunds"], ["refunds"], question_id="found"),
            result(["warranty"], ["shipping"], question_id="lost"),
        ]
    )

    assert report.failures == ["lost"]
    assert report.hit_rate == 0.5


def test_score_breaks_recall_down_by_question_kind():
    """Averages hide the interesting part.

    A change that helps direct lookups and hurts paraphrases can leave the
    overall number flat, which is exactly the case worth catching.
    """
    report = score(
        [
            result(["a"], ["a"], question_id="1", kind="direct"),
            result(["b"], ["b"], question_id="2", kind="direct"),
            result(["c"], ["x"], question_id="3", kind="paraphrase"),
        ]
    )

    assert report.by_kind == {"direct": 1.0, "paraphrase": 0.0}


def test_score_collects_answers_that_lost_an_expected_fact():
    report = score(
        [
            result(["a"], ["a"], question_id="kept"),
            result(["b"], ["b"], question_id="dropped", missing_phrases=["30 days"]),
        ]
    )

    assert report.phrase_failures == ["dropped"]


def test_score_needs_something_to_average():
    with pytest.raises(ValueError):
        score([result([], ["anything"])])


def test_compare_names_what_improved_and_what_regressed():
    baseline = {"recall_at_k": 0.80, "mrr": 0.70, "failures": ["a", "b"]}
    current = {"recall_at_k": 0.90, "mrr": 0.65, "failures": ["b", "c"]}

    lines = compare(baseline, current)
    joined = "\n".join(lines)

    assert "recall_at_k" in joined and "+0.1000" in joined
    assert "-0.0500" in joined
    assert "now passing: a" in joined
    assert "newly failing: c" in joined


def test_the_question_set_and_corpus_agree_with_each_other():
    """A typo in a slug would silently score as "retrieved nothing"."""
    corpus = load_corpus()
    questions = load_questions()

    assert corpus, "the eval corpus is empty"
    for question in questions:
        for slug in question.expected_documents:
            assert slug in corpus, f"{question.id} expects unknown document {slug!r}"


def test_the_question_set_covers_more_than_direct_lookups():
    """Direct questions are the easy case and would flatter any retriever."""
    kinds = {question.kind for question in load_questions()}

    assert {"paraphrase", "inference", "cross-document", "unanswerable"} <= kinds


def test_question_ids_are_unique():
    ids = [question.id for question in load_questions()]

    assert len(ids) == len(set(ids))


def test_stored_results_stay_readable():
    """Result files are the record a later change is compared against."""
    for path in (Path(__file__).resolve().parents[1] / "eval" / "results").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "summary" in payload, f"{path.name} has no summary to compare against"
        assert "config" in payload, f"{path.name} does not say how it was produced"
