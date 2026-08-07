import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.documents.cleanup import remove_directory
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationSlugAlreadyExistsError(Exception):
    pass


class OrganizationNotFoundError(Exception):
    pass


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.organizations = OrganizationRepository(db)

    def create(self, data: OrganizationCreate, owner: User) -> Organization:
        slug = data.slug or self._generate_slug(data.name)
        if self.organizations.get_by_slug(slug) is not None:
            raise OrganizationSlugAlreadyExistsError

        try:
            organization = self.organizations.create(name=data.name, slug=slug)
            self.organizations.add_member(
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise OrganizationSlugAlreadyExistsError from exc
        self.db.refresh(organization)
        return organization

    def list_for_user(self, user: User) -> list[Organization]:
        return self.organizations.list_for_user(user.id)

    def update(
        self,
        *,
        organization_id: uuid.UUID,
        data: OrganizationUpdate,
    ) -> Organization:
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError

        organization.name = data.name
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def delete(self, organization_id: uuid.UUID) -> None:
        """Delete a workspace and every row that belongs to it.

        The cascades reach knowledge bases, documents, chunks, conversations,
        messages, citations and memberships — everything keyed on
        `organization_id`. The users themselves survive: a person is not owned
        by a workspace, and someone in two workspaces must keep their account
        when one goes.

        No busy check here. A workspace deletion is the one case where waiting
        for in-flight preparation is the wrong answer: the whole tenant is
        going, so a document part-way through indexing is not work anyone
        wants to preserve, and any job that survives finds its rows gone and
        exits.
        """
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError

        self.organizations.delete(organization)
        self.db.commit()
        remove_directory(str(organization_id))

    @staticmethod
    def _generate_slug(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            slug = "organization"
        return f"{slug[:111].rstrip('-')}-{uuid.uuid4().hex[:8]}"
