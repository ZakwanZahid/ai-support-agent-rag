import uuid
from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db as session_get_db
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from session_get_db()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_organization_id(
    request: Request,
    organization_header: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> uuid.UUID:
    raw_id = request.path_params.get("organization_id") or organization_header
    if raw_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context is required",
        )
    try:
        return uuid.UUID(str(raw_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid organization ID",
        )


def require_organization_member(
    organization_id: Annotated[uuid.UUID, Depends(get_organization_id)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationMember:
    membership = OrganizationRepository(db).get_membership(
        organization_id=organization_id,
        user_id=current_user.id,
    )
    if membership is None:
        # Deliberately identical for missing organizations and non-members.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return membership


def get_current_organization(
    membership: Annotated[OrganizationMember, Depends(require_organization_member)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    organization = OrganizationRepository(db).get_by_id(membership.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


def require_role(allowed_roles: list[str]) -> Callable[..., OrganizationMember]:
    allowed = frozenset(allowed_roles)

    def role_dependency(
        membership: Annotated[OrganizationMember, Depends(require_organization_member)],
    ) -> OrganizationMember:
        if membership.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient organization role",
            )
        return membership

    return role_dependency
