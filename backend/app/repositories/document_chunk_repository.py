import re
import uuid
from dataclasses import dataclass
from math import sqrt

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.ingestion.chunking import TextChunk
from app.models.document import Document, DocumentChunk
from app.rag.fusion import reciprocal_rank_fusion


_WORD = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True)
class ChunkSearchMatch:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    distance: float
    chunk_metadata: dict | None


class DocumentChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_for_document(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> int:
        statement = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.document_id == document_id,
        )
        return self.db.scalar(statement) or 0

    def delete_for_document(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        statement = delete(DocumentChunk).where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.document_id == document_id,
        )
        self.db.execute(statement)

    def create_many(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[TextChunk],
    ) -> list[DocumentChunk]:
        models = [
            DocumentChunk(
                organization_id=organization_id,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_metadata=chunk.metadata,
                embedding=None,
            )
            for chunk in chunks
        ]
        self.db.add_all(models)
        self.db.flush()
        return models

    def list_for_indexing(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        include_embedded: bool,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(
                DocumentChunk.organization_id == organization_id,
                DocumentChunk.document_id == document_id,
            )
            .order_by(DocumentChunk.chunk_index)
        )
        if not include_embedded:
            statement = statement.where(DocumentChunk.embedding.is_(None))
        return list(self.db.scalars(statement).all())

    def count_without_embeddings(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> int:
        statement = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.is_(None),
        )
        return self.db.scalar(statement) or 0

    def semantic_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        bind = self.db.get_bind()
        if bind.dialect.name == "postgresql":
            return self._postgres_semantic_search(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                query_embedding=query_embedding,
                top_k=top_k,
            )
        return self._in_memory_semantic_search(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

    def keyword_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        """Literal-term search over the same chunks.

        The vector distance is computed for these rows too, even though the
        ranking here is by text relevance. It costs almost nothing on a handful
        of rows and means every match carries the same kind of score, so fusing
        the two rankings does not produce results the rest of the pipeline
        cannot interpret.
        """
        bind = self.db.get_bind()
        if bind.dialect.name != "postgresql":
            return self._in_memory_keyword_search(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=top_k,
            )

        statement = text(
            """
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                d.title AS document_title,
                dc.content,
                dc.chunk_metadata,
                dc.embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE dc.organization_id = :organization_id
              AND d.organization_id = :organization_id
              AND d.knowledge_base_id = :knowledge_base_id
              AND dc.embedding IS NOT NULL
              AND dc.content_tsv @@ websearch_to_tsquery('english', :query_text)
            ORDER BY ts_rank(
                dc.content_tsv,
                websearch_to_tsquery('english', :query_text)
            ) DESC
            LIMIT :top_k
            """
        )
        rows = self.db.execute(
            statement,
            {
                "organization_id": organization_id,
                "knowledge_base_id": knowledge_base_id,
                "query_text": query_text,
                # websearch_to_tsquery accepts whatever a user types without
                # raising, unlike to_tsquery, which rejects unbalanced quotes
                # and stray operators — i.e. ordinary questions.
                "query_embedding": _vector_literal(query_embedding),
                "top_k": top_k,
            },
        ).mappings()
        return [_to_match(row) for row in rows]

    def hybrid_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        candidate_multiplier: int = 2,
    ) -> list[ChunkSearchMatch]:
        """Vector and keyword results, fused by rank.

        Each retriever is asked for more than `top_k` so fusion has something
        to work with: if both were asked for exactly the final number, a chunk
        ranked just outside one list could never be promoted by agreement with
        the other, and fusion would only ever reorder what vector search
        already found.
        """
        candidates = max(top_k * candidate_multiplier, top_k)

        vector_matches = self.semantic_search(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            top_k=candidates,
        )
        keyword_matches = self.keyword_search(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=candidates,
        )

        by_id = {match.chunk_id: match for match in vector_matches}
        by_id.update({match.chunk_id: match for match in keyword_matches})

        fused = reciprocal_rank_fusion(
            [
                [match.chunk_id for match in vector_matches],
                [match.chunk_id for match in keyword_matches],
            ]
        )
        return [by_id[chunk_id] for chunk_id, _score in fused[:top_k]]

    def _in_memory_keyword_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        """SQLite has no tsvector, so the tests get term overlap instead.

        Not a reimplementation of Postgres ranking and not pretending to be:
        it exists so the hybrid code path is exercised by the suite, while the
        real ranking is measured by the eval harness against real Postgres.
        """
        terms = {term for term in _WORD.findall(query_text.lower()) if len(term) > 2}
        if not terms:
            return []

        statement = (
            select(DocumentChunk, Document.title)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.organization_id == organization_id,
                Document.organization_id == organization_id,
                Document.knowledge_base_id == knowledge_base_id,
                DocumentChunk.embedding.is_not(None),
            )
        )
        scored = []
        for chunk, document_title in self.db.execute(statement).all():
            content = chunk.content.lower()
            overlap = sum(1 for term in terms if term in content)
            if overlap:
                scored.append(
                    (
                        overlap,
                        ChunkSearchMatch(
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            document_title=document_title,
                            content=chunk.content,
                            distance=_cosine_distance(
                                query_embedding, chunk.embedding or []
                            ),
                            chunk_metadata=chunk.chunk_metadata,
                        ),
                    )
                )
        scored.sort(key=lambda entry: (-entry[0], entry[1].distance))
        return [match for _overlap, match in scored[:top_k]]

    def _postgres_semantic_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        statement = text(
            """
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                d.title AS document_title,
                dc.content,
                dc.chunk_metadata,
                dc.embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE dc.organization_id = :organization_id
              AND d.organization_id = :organization_id
              AND d.knowledge_base_id = :knowledge_base_id
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
            """
        )
        rows = self.db.execute(
            statement,
            {
                "organization_id": organization_id,
                "knowledge_base_id": knowledge_base_id,
                "query_embedding": _vector_literal(query_embedding),
                "top_k": top_k,
            },
        ).mappings()
        return [_to_match(row) for row in rows]

    def _in_memory_semantic_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        statement = (
            select(DocumentChunk, Document.title)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.organization_id == organization_id,
                Document.organization_id == organization_id,
                Document.knowledge_base_id == knowledge_base_id,
                DocumentChunk.embedding.is_not(None),
            )
        )
        matches = [
            ChunkSearchMatch(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=document_title,
                content=chunk.content,
                distance=_cosine_distance(query_embedding, chunk.embedding or []),
                chunk_metadata=chunk.chunk_metadata,
            )
            for chunk, document_title in self.db.execute(statement).all()
        ]
        return sorted(matches, key=lambda match: match.distance)[:top_k]


def _vector_literal(embedding: list[float]) -> str:
    """pgvector's text input form. Bound as a parameter, then cast in SQL."""
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def _to_match(row) -> ChunkSearchMatch:
    return ChunkSearchMatch(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        document_title=row["document_title"],
        content=row["content"],
        distance=float(row["distance"]),
        chunk_metadata=row["chunk_metadata"],
    )


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare embeddings with different dimensions")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    similarity = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return 1.0 - similarity
