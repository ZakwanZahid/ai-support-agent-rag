import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_upload(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        title: str,
        file_name: str,
        file_path: str,
        mime_type: str,
    ) -> Document:
        document = Document(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
            source_type="upload",
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
            status="pending",
        )
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_id(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        return self.db.scalar(statement)

    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> list[Document]:
        statement = select(Document).where(Document.organization_id == organization_id)
        if knowledge_base_id is not None:
            statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        statement = statement.order_by(Document.created_at.desc(), Document.id)
        return list(self.db.scalars(statement).all())
