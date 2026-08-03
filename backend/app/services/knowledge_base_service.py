import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.repositories.document_repository import DocumentCounts, DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse


class KnowledgeBaseAlreadyExistsError(Exception):
    pass


class KnowledgeBaseNotFoundError(Exception):
    pass


NO_DOCUMENTS = DocumentCounts(total=0, ready=0)


def _to_response(
    knowledge_base: KnowledgeBase,
    counts: DocumentCounts = NO_DOCUMENTS,
) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse.model_validate(knowledge_base).model_copy(
        update={
            "document_count": counts.total,
            "ready_document_count": counts.ready,
        },
    )


class KnowledgeBaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.knowledge_bases = KnowledgeBaseRepository(db)
        self.documents = DocumentRepository(db)

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBaseResponse:
        existing = self.knowledge_bases.get_by_name(
            organization_id=organization_id,
            name=data.name,
        )
        if existing is not None:
            raise KnowledgeBaseAlreadyExistsError

        try:
            knowledge_base = self.knowledge_bases.create(
                organization_id=organization_id,
                name=data.name,
                description=data.description,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise KnowledgeBaseAlreadyExistsError from exc
        self.db.refresh(knowledge_base)
        # A knowledge base is always empty at creation.
        return _to_response(knowledge_base)

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
    ) -> list[KnowledgeBaseResponse]:
        knowledge_bases = self.knowledge_bases.list_for_organization(organization_id)
        counts = self.documents.counts_by_knowledge_base(organization_id)
        return [
            _to_response(knowledge_base, counts.get(knowledge_base.id, NO_DOCUMENTS))
            for knowledge_base in knowledge_bases
        ]

    def get(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> KnowledgeBaseResponse:
        knowledge_base = self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError

        counts = self.documents.counts_by_knowledge_base(organization_id)
        return _to_response(knowledge_base, counts.get(knowledge_base.id, NO_DOCUMENTS))
