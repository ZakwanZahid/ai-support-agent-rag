import uuid

from sqlalchemy.orm import Session

from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository


class IndexingDocumentNotFoundError(Exception):
    pass


class DocumentNotReadyForIndexingError(Exception):
    pass


class DocumentAlreadyIndexedError(Exception):
    pass


class IndexingService:
    def __init__(self, db: Session) -> None:
        self.documents = DocumentRepository(db)
        self.chunks = DocumentChunkRepository(db)

    def prepare(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        force: bool,
    ) -> None:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise IndexingDocumentNotFoundError
        if document.status not in {"processed", "indexed"}:
            raise DocumentNotReadyForIndexingError(document.status)

        chunk_count = self.chunks.count_for_document(
            organization_id=organization_id,
            document_id=document_id,
        )
        if chunk_count == 0:
            raise DocumentNotReadyForIndexingError(document.status)

        missing_count = self.chunks.count_without_embeddings(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document.status == "indexed" and missing_count == 0 and not force:
            raise DocumentAlreadyIndexedError
