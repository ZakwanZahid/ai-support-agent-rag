"""Combining two rankings into one.

Vector search and keyword search return scores that are not comparable:
a cosine distance and a `ts_rank` are different units on different scales, and
`ts_rank` is not even bounded. Normalising them onto a shared scale means
inventing a conversion, and the conversion would be the thing quietly deciding
the results.

Reciprocal rank fusion sidesteps that by throwing the scores away and keeping
only the positions. A document ranked second by both retrievers beats one
ranked first by a single retriever and missing from the other — which is the
behaviour worth having, because agreement between two different methods is
better evidence than a strong score from one.
"""

from collections.abc import Hashable, Sequence
from typing import TypeVar


ItemT = TypeVar("ItemT", bound=Hashable)

# The constant damps the difference between the top few positions, so rank one
# does not dominate every fused result. 60 is the value from the original
# paper and the usual default; nothing here is tuned to it, and the eval is
# how a different value would be justified.
RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[ItemT]],
    *,
    k: int = RRF_K,
    weights: Sequence[float] | None = None,
) -> list[tuple[ItemT, float]]:
    """Fuse ranked lists into one, best first.

    Each list contributes `weight / (k + rank)` for every item it contains.
    Items absent from a list simply score nothing from it, which is what makes
    this tolerant of one retriever returning fewer results — or none.

    Ties are broken by first appearance, so the result is deterministic rather
    than dependent on dictionary ordering across runs.
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights must have one entry per ranking")

    scores: dict[ItemT, float] = {}
    first_seen: dict[ItemT, int] = {}
    order = 0

    for ranking, weight in zip(rankings, weights):
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + weight / (k + rank)
            if item not in first_seen:
                first_seen[item] = order
                order += 1

    return sorted(
        scores.items(),
        key=lambda entry: (-entry[1], first_seen[entry[0]]),
    )
