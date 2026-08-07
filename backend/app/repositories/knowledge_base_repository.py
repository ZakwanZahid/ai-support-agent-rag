import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            organization_id=organization_id,
            name=name,
            description=description,
        )
        self.db.add(knowledge_base)
        self.db.flush()
        return knowledge_base

    def get_by_id(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> KnowledgeBase | None:
        statement = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.organization_id == organization_id,
        )
        return self.db.scalar(statement)

    def get_by_name(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
    ) -> KnowledgeBase | None:
        statement = select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.name == name,
        )
        return self.db.scalar(statement)

    def delete(self, knowledge_base: KnowledgeBase) -> None:
        """Core DELETE, so the database's own cascades apply. See
        DocumentRepository.delete for why the ORM is the wrong tool here."""
        self.db.execute(
            sa_delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base.id),
            execution_options={"synchronize_session": False},
        )
        self.db.expire_all()

    def list_for_organization(self, organization_id: uuid.UUID) -> list[KnowledgeBase]:
        statement = (
            select(KnowledgeBase)
            .where(KnowledgeBase.organization_id == organization_id)
            .order_by(KnowledgeBase.name, KnowledgeBase.id)
        )
        return list(self.db.scalars(statement).all())
