import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import resolve_storage_path
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository


SUPPORTED_FILE_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "text/markdown": {".md", ".markdown"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}
UPLOAD_CHUNK_SIZE = 1024 * 1024


class DocumentNotFoundError(Exception):
    pass


class KnowledgeBaseNotFoundError(Exception):
    pass


class UnsupportedDocumentTypeError(Exception):
    pass


class InvalidUploadError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


class DocumentStorageError(Exception):
    pass


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.knowledge_bases = KnowledgeBaseRepository(db)

    async def upload(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        file: UploadFile,
        title: str | None,
    ) -> Document:
        if self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        ) is None:
            raise KnowledgeBaseNotFoundError

        original_name, extension, mime_type = self._validate_file(file)
        document_title = self._normalize_title(title, original_name)
        stored_name = f"{uuid.uuid4().hex}{extension}"
        upload_root = Path(settings.upload_dir)
        configured_path = (
            upload_root
            / str(organization_id)
            / str(knowledge_base_id)
            / stored_name
        )
        stored_path = resolve_storage_path(configured_path)

        try:
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            await self._write_file(file, stored_path)
        except (InvalidUploadError, UploadTooLargeError):
            stored_path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            stored_path.unlink(missing_ok=True)
            raise DocumentStorageError from exc
        finally:
            await file.close()

        try:
            document = self.documents.create_upload(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                title=document_title,
                file_name=original_name,
                file_path=configured_path.as_posix(),
                mime_type=mime_type,
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            stored_path.unlink(missing_ok=True)
            raise
        self.db.refresh(document)
        return document

    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> list[Document]:
        return self.documents.list_for_organization(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )

    def get(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        document = self.documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError
        return document

    @staticmethod
    def _validate_file(file: UploadFile) -> tuple[str, str, str]:
        original_name = Path(file.filename or "").name
        if not original_name or len(original_name) > 255:
            raise InvalidUploadError

        mime_type = file.content_type or ""
        allowed_extensions = SUPPORTED_FILE_EXTENSIONS.get(mime_type)
        extension = Path(original_name).suffix.lower()
        if allowed_extensions is None or extension not in allowed_extensions:
            raise UnsupportedDocumentTypeError
        return original_name, extension, mime_type

    @staticmethod
    def _normalize_title(title: str | None, original_name: str) -> str:
        normalized = title.strip() if title is not None else Path(original_name).stem.strip()
        if not normalized or len(normalized) > 255:
            raise InvalidUploadError
        return normalized

    @staticmethod
    async def _write_file(file: UploadFile, stored_path: Path) -> None:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        bytes_written = 0
        with stored_path.open("xb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise UploadTooLargeError
                destination.write(chunk)
        if bytes_written == 0:
            raise InvalidUploadError
