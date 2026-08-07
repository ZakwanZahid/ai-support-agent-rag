"""Structure-aware chunking, rank fusion, and source deduplication.

The eval harness says whether these help; these tests say whether they do what
they claim. Both are needed — a metric that improved for the wrong reason is
still a change nobody can explain.
"""

import uuid

import pytest

from app.ingestion.chunking import (
    MINIMUM_SECTION_CHARS,
    chunk_document,
    chunk_text,
    split_sections,
)
from app.rag.citation_builder import build_citations
from app.rag.fusion import reciprocal_rank_fusion
from app.repositories.document_chunk_repository import ChunkSearchMatch


DOCUMENT = """# Shipping and delivery

## Delivery times

Standard delivery arrives in three to five business days. Express delivery
arrives the next business day when ordered before 2pm on a weekday, and orders
placed at the weekend are dispatched on the following Monday morning instead.

## Shipping costs

Standard delivery is free on orders over forty pounds. Below that threshold it
costs three pounds ninety-five. Express delivery costs seven pounds ninety-five
regardless of the value of the order being placed.
"""


def test_sections_carry_the_headings_above_them():
    sections = split_sections(DOCUMENT)

    assert [section.heading_path for section in sections] == [
        ["Shipping and delivery", "Delivery times"],
        ["Shipping and delivery", "Shipping costs"],
    ]


def test_a_deeper_heading_nests_and_a_sibling_replaces():
    text = "# A\n\ntop\n\n## B\n\nunder b\n\n## C\n\nunder c\n\n# D\n\nunder d\n"

    paths = [section.heading_path for section in split_sections(text)]

    assert paths == [["A"], ["A", "B"], ["A", "C"], ["D"]]


def test_text_with_no_headings_is_one_section():
    """PDFs and plain text have no markdown structure to find."""
    sections = split_sections("Just a paragraph with no headings at all.")

    assert len(sections) == 1
    assert sections[0].heading_path == []


def test_each_section_becomes_its_own_chunk():
    """The point of the change: one document is no longer one embedding."""
    chunks = chunk_document(DOCUMENT, chunk_size=1200, chunk_overlap=200)

    assert len(chunks) == 2
    assert "three to five business days" in chunks[0].content
    assert "seven pounds" in chunks[1].content


def test_a_chunk_is_prefixed_with_its_heading_path():
    """A retrieved passage has to say what it is a passage of.

    "Free on orders over forty pounds" is ambiguous alone and unambiguous
    under "Shipping and delivery › Shipping costs" — and the prefix is
    embedded, so it steers retrieval as well as being shown to the reader.
    """
    chunks = chunk_document(DOCUMENT, chunk_size=1200, chunk_overlap=200)

    assert chunks[1].content.startswith("Shipping and delivery › Shipping costs")
    assert chunks[1].metadata["heading"] == "Shipping and delivery › Shipping costs"
    assert chunks[1].metadata["heading_path"] == ["Shipping and delivery", "Shipping costs"]


def test_metadata_from_the_caller_survives():
    chunks = chunk_document(
        DOCUMENT,
        chunk_size=1200,
        chunk_overlap=200,
        metadata={"source": "shipping.md"},
    )

    assert all(chunk.metadata["source"] == "shipping.md" for chunk in chunks)


def test_a_section_too_long_for_one_chunk_falls_back_to_windows():
    long_section = "# Title\n\n## Long\n\n" + ("sentence about refunds. " * 200)

    chunks = chunk_document(long_section, chunk_size=400, chunk_overlap=50)

    assert len(chunks) > 1
    # No chunk exceeds the budget, and every piece keeps the heading context.
    assert all(len(chunk.content) <= 400 for chunk in chunks)
    assert all(chunk.content.startswith("Title › Long") for chunk in chunks)


def test_chunk_indexes_are_sequential_across_sections():
    chunks = chunk_document(DOCUMENT, chunk_size=1200, chunk_overlap=200)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_a_very_short_section_is_merged_rather_than_left_alone():
    """A two-line section embeds to a vector that is mostly about being short."""
    text = "# Policy\n\n## Note\n\nSee below.\n\n## Detail\n\n" + ("x" * 400)

    chunks = chunk_document(text, chunk_size=1200, chunk_overlap=200)

    assert len(chunks) == 1
    assert "See below." in chunks[0].content


def test_the_window_chunker_still_works_for_unstructured_text():
    """`chunk_text` is still the fallback and is still used directly."""
    chunks = chunk_text("a" * 1000, chunk_size=300, chunk_overlap=50)

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 300 for chunk in chunks)


def test_fusion_prefers_agreement_over_a_single_strong_rank():
    """The property that makes fusion worth having.

    Neither retriever's score is comparable to the other's, so all that is
    left is position — and being found by both is better evidence than being
    found first by one.
    """
    vector = ["only-vector", "agreed"]
    keyword = ["only-keyword", "agreed"]

    fused = [item for item, _score in reciprocal_rank_fusion([vector, keyword])]

    assert fused[0] == "agreed"


def test_fusion_keeps_items_only_one_retriever_found():
    fused = dict(reciprocal_rank_fusion([["a"], ["b"]]))

    assert set(fused) == {"a", "b"}


def test_fusion_tolerates_an_empty_ranking():
    """Keyword search returns nothing when no term matches, which is normal."""
    fused = [item for item, _ in reciprocal_rank_fusion([["a", "b"], []])]

    assert fused == ["a", "b"]


def test_fusion_is_deterministic_for_tied_scores():
    first = reciprocal_rank_fusion([["a", "b"], ["b", "a"]])
    second = reciprocal_rank_fusion([["a", "b"], ["b", "a"]])

    assert first == second


def test_fusion_rejects_a_weight_per_ranking_mismatch():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])


def match(document_id: uuid.UUID, title: str, distance: float) -> ChunkSearchMatch:
    return ChunkSearchMatch(
        chunk_id=uuid.uuid4(),
        document_id=document_id,
        document_title=title,
        content=f"passage from {title}",
        distance=distance,
        chunk_metadata=None,
    )


def test_citations_show_one_entry_per_document():
    """Section chunking made several chunks of one document a common result.

    Listing them separately shows "Refund policy" three times, which reads as
    three sources and is one.
    """
    refunds = uuid.uuid4()
    shipping = uuid.uuid4()
    matches = [
        match(refunds, "Refund policy", 0.10),
        match(refunds, "Refund policy", 0.15),
        match(shipping, "Shipping", 0.20),
    ]

    citations = build_citations(matches)

    assert [citation.document_title for citation in citations] == [
        "Refund policy",
        "Shipping",
    ]


def test_deduplication_keeps_the_best_ranked_chunk():
    refunds = uuid.uuid4()
    best = match(refunds, "Refund policy", 0.10)
    worse = match(refunds, "Refund policy", 0.40)

    citations = build_citations([best, worse])

    assert len(citations) == 1
    assert citations[0].chunk_id == best.chunk_id


def test_deduplication_can_be_turned_off():
    """Only the display is deduplicated; the context keeps every chunk."""
    refunds = uuid.uuid4()
    matches = [match(refunds, "Refund policy", 0.1), match(refunds, "Refund policy", 0.2)]

    assert len(build_citations(matches, one_per_document=False)) == 2


def test_minimum_section_size_is_a_named_constant():
    """It is a tuning decision, so it should be findable and changeable."""
    assert MINIMUM_SECTION_CHARS > 0
