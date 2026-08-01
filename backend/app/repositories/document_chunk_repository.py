import uuid
from dataclasses import dataclass
from math import sqrt

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.ingestion.chunking import TextChunk
from app.models.document import Document, DocumentChunk


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

    def _postgres_semantic_search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[ChunkSearchMatch]:
        query_vector = "[" + ",".join(str(float(value)) for value in query_embedding) + "]"
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
                "query_embedding": query_vector,
                "top_k": top_k,
            },
        ).mappings()
        return [
            ChunkSearchMatch(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=row["document_title"],
                content=row["content"],
                distance=float(row["distance"]),
                chunk_metadata=row["chunk_metadata"],
            )
            for row in rows
        ]

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


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare embeddings with different dimensions")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    similarity = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return 1.0 - similarity
