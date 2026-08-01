import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ingestion.chunking import TextChunk
from app.models.document import DocumentChunk


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
