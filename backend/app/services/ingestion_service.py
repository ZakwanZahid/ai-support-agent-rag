import uuid

from sqlalchemy.orm import Session

from app.core.storage import resolve_storage_path
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository


class IngestionDocumentNotFoundError(Exception):
    pass


class IngestionFileNotFoundError(Exception):
    pass


class DocumentAlreadyIngestedError(Exception):
    pass


class DocumentIngestionInProgressError(Exception):
    pass


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)

    def prepare(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        force: bool,
    ) -> Document:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise IngestionDocumentNotFoundError
        if not document.file_path or not resolve_storage_path(document.file_path).is_file():
            raise IngestionFileNotFoundError
        if document.status == "processing":
            raise DocumentIngestionInProgressError
        if document.status in {"processed", "indexed"} and not force:
            raise DocumentAlreadyIngestedError

        document.status = "processing"
        document.error_message = None
        self.db.commit()
        self.db.refresh(document)
        return document
