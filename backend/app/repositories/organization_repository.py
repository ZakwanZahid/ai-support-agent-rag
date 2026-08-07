import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationMember


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def delete(self, organization: Organization) -> None:
        """Core DELETE, so the database's own cascades apply. See
        DocumentRepository.delete for why the ORM is the wrong tool here."""
        self.db.execute(
            sa_delete(Organization).where(Organization.id == organization.id),
            execution_options={"synchronize_session": False},
        )
        self.db.expire_all()

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.slug == slug))

    def create(self, *, name: str, slug: str) -> Organization:
        organization = Organization(name=name, slug=slug)
        self.db.add(organization)
        self.db.flush()
        return organization

    def add_member(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> OrganizationMember:
        membership = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_membership(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationMember | None:
        statement = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        return self.db.scalar(statement)

    def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        statement = (
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.name, Organization.id)
        )
        return list(self.db.scalars(statement).all())
