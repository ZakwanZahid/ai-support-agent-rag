import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate


class KnowledgeBaseAlreadyExistsError(Exception):
    pass


class KnowledgeBaseNotFoundError(Exception):
    pass


class KnowledgeBaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.knowledge_bases = KnowledgeBaseRepository(db)

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
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
        return knowledge_base

    def list_for_organization(self, organization_id: uuid.UUID) -> list[KnowledgeBase]:
        return self.knowledge_bases.list_for_organization(organization_id)

    def get(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> KnowledgeBase:
        knowledge_base = self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError
        return knowledge_base
