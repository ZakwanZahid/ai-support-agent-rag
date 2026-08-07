"""Retrieval metrics.

Pure functions over "what was expected" and "what came back", with no database
and no provider, so the arithmetic is unit-tested in the normal suite while the
harness that produces the inputs needs a real Postgres and a paid API key.

The metrics are deliberately about *documents*, not chunks. Which chunk a fact
landed in is a consequence of chunk size, and chunk size is one of the things
being tuned — scoring on chunk identity would make every chunking change look
like a retrieval change.
"""

from dataclasses import dataclass, field
from statistics import mean


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    kind: str
    expected_documents: list[str]
    # Retrieved document slugs, best first, one entry per retrieved chunk.
    retrieved_documents: list[str]
    top_score: float | None = None
    answer: str | None = None
    missing_phrases: list[str] = field(default_factory=list)

    @property
    def is_unanswerable(self) -> bool:
        return not self.expected_documents


def recall(result: QuestionResult) -> float:
    """Did the right document appear anywhere in the results?

    For a support assistant this is the metric that matters most: the answer is
    generated from everything retrieved, so a source at rank four still ends up
    in the context. Rank matters, but being absent is the failure that produces
    a confidently wrong answer.
    """
    if result.is_unanswerable:
        raise ValueError("recall is undefined for a question with no expected source")
    found = set(result.retrieved_documents) & set(result.expected_documents)
    return len(found) / len(set(result.expected_documents))


def reciprocal_rank(result: QuestionResult) -> float:
    """1/rank of the first correct document, or 0 if none was retrieved.

    Averaged across questions this is MRR. It is the metric that moves when a
    change reorders results without changing what is retrieved — which is
    exactly what re-ranking and hybrid scoring do.
    """
    if result.is_unanswerable:
        raise ValueError("rank is undefined for a question with no expected source")
    expected = set(result.expected_documents)
    for position, document in enumerate(result.retrieved_documents, start=1):
        if document in expected:
            return 1.0 / position
    return 0.0


def precision(result: QuestionResult) -> float:
    """Fraction of retrieved chunks that came from an expected document.

    Low precision is not automatically bad — retrieving five chunks when one
    document holds the answer caps this at well under 1.0 — so it is read as a
    trend across runs rather than against an absolute target. It is the metric
    that catches a change which improves recall by retrieving indiscriminately.
    """
    if not result.retrieved_documents:
        return 0.0
    expected = set(result.expected_documents)
    hits = sum(1 for document in result.retrieved_documents if document in expected)
    return hits / len(result.retrieved_documents)


@dataclass(frozen=True)
class Report:
    answerable: int
    unanswerable: int
    recall_at_k: float
    mrr: float
    precision_at_k: float
    hit_rate: float
    by_kind: dict[str, float]
    failures: list[str]
    unanswerable_top_scores: list[float]
    phrase_failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "answerable": self.answerable,
            "unanswerable": self.unanswerable,
            "recall_at_k": round(self.recall_at_k, 4),
            "mrr": round(self.mrr, 4),
            "precision_at_k": round(self.precision_at_k, 4),
            "hit_rate": round(self.hit_rate, 4),
            "by_kind": {kind: round(value, 4) for kind, value in self.by_kind.items()},
            "failures": self.failures,
            "phrase_failures": self.phrase_failures,
            "unanswerable_top_scores": [
                round(score, 4) for score in self.unanswerable_top_scores
            ],
        }


def score(results: list[QuestionResult]) -> Report:
    answerable = [result for result in results if not result.is_unanswerable]
    unanswerable = [result for result in results if result.is_unanswerable]

    if not answerable:
        raise ValueError("no answerable questions to score")

    recalls = [recall(result) for result in answerable]
    ranks = [reciprocal_rank(result) for result in answerable]

    by_kind: dict[str, float] = {}
    for kind in sorted({result.kind for result in answerable}):
        of_kind = [result for result in answerable if result.kind == kind]
        by_kind[kind] = mean(recall(result) for result in of_kind)

    return Report(
        answerable=len(answerable),
        unanswerable=len(unanswerable),
        recall_at_k=mean(recalls),
        mrr=mean(ranks),
        precision_at_k=mean(precision(result) for result in answerable),
        # Fraction of questions where at least one expected document appeared
        # at all. Blunter than recall and easier to reason about at a glance.
        hit_rate=mean(1.0 if value > 0 else 0.0 for value in recalls),
        by_kind=by_kind,
        failures=[
            result.question_id
            for result, value in zip(answerable, recalls)
            if value == 0
        ],
        phrase_failures=[
            result.question_id for result in results if result.missing_phrases
        ],
        # Not scored pass/fail. There is no threshold yet at which a top score
        # means "nothing relevant"; recording the numbers is what makes it
        # possible to choose one later from evidence.
        unanswerable_top_scores=[
            result.top_score for result in unanswerable if result.top_score is not None
        ],
    )


def compare(baseline: dict, current: dict) -> list[str]:
    """Human-readable deltas between two runs' summaries."""
    lines = []
    for metric in ("recall_at_k", "mrr", "precision_at_k", "hit_rate"):
        before = baseline.get(metric)
        after = current.get(metric)
        if before is None or after is None:
            continue
        delta = after - before
        arrow = "→" if abs(delta) < 1e-9 else ("↑" if delta > 0 else "↓")
        lines.append(f"{metric:<16} {before:.4f} {arrow} {after:.4f}  ({delta:+.4f})")

    fixed = sorted(set(baseline.get("failures", [])) - set(current.get("failures", [])))
    broken = sorted(set(current.get("failures", [])) - set(baseline.get("failures", [])))
    if fixed:
        lines.append(f"now passing: {', '.join(fixed)}")
    if broken:
        lines.append(f"newly failing: {', '.join(broken)}")
    return lines
