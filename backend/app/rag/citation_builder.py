import uuid
from dataclasses import dataclass
from typing import Any

from app.repositories.document_chunk_repository import ChunkSearchMatch


@dataclass(frozen=True)
class CitationData:
    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID
    quote: str
    score: float
    chunk_metadata: dict[str, Any] | None


def build_citations(
    matches: list[ChunkSearchMatch],
    *,
    max_quote_chars: int = 500,
    one_per_document: bool = True,
) -> list[CitationData]:
    """Turn retrieved chunks into the sources shown under an answer.

    By default only the best-ranked chunk from each document becomes a
    citation. Structure-aware chunking made it common for two or three
    sections of the same document to be retrieved together, and listing them
    separately shows the reader "Refund policy, Refund policy, Refund policy"
    — three entries that look like three sources and are one.

    Only the display is deduplicated. Every retrieved chunk still goes into the
    context the model answers from, because they are genuinely different text
    and dropping them would lose information the answer needs.
    """
    citations: list[CitationData] = []
    seen_documents: set[uuid.UUID] = set()

    for match in matches:
        if one_per_document:
            if match.document_id in seen_documents:
                continue
            seen_documents.add(match.document_id)
        quote = " ".join(match.content.split())
        if len(quote) > max_quote_chars:
            quote = f"{quote[: max_quote_chars - 1].rstrip()}…"
        citations.append(
            CitationData(
                document_id=match.document_id,
                document_title=match.document_title,
                chunk_id=match.chunk_id,
                quote=quote,
                score=1.0 - match.distance,
                chunk_metadata=match.chunk_metadata,
            )
        )
    return citations
