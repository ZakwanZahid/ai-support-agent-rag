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
) -> list[CitationData]:
    citations: list[CitationData] = []
    for match in matches:
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
