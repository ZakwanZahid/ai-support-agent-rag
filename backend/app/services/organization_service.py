import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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

    @staticmethod
    def _generate_slug(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            slug = "organization"
        return f"{slug[:111].rstrip('-')}-{uuid.uuid4().hex[:8]}"
