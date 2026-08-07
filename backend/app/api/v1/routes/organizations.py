import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_organization,
    get_current_user,
    get_db,
    require_role,
)
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_service import (
    OrganizationNotFoundError,
    OrganizationService,
    OrganizationSlugAlreadyExistsError,
)


router = APIRouter(prefix="/organizations", tags=["organizations"])
owner_or_admin = require_role(["owner", "admin"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    try:
        return OrganizationService(db).create(data, current_user)
    except OrganizationSlugAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug is already in use",
        )


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Organization]:
    return OrganizationService(db).list_for_user(current_user)


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: uuid.UUID,
    organization: Annotated[Organization, Depends(get_current_organization)],
) -> Organization:
    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: uuid.UUID,
    data: OrganizationUpdate,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
) -> Organization:
    try:
        return OrganizationService(db).update(
            organization_id=organization_id,
            data=data,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )


owner_only = require_role(["owner"])


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_only)],
) -> None:
    """Delete a workspace and everything in it.

    Owner only, not owner-or-admin. Every other destructive action in the API
    is recoverable by re-uploading; this one takes the whole tenant, including
    other members' chat history, so it belongs to the one role that cannot be
    granted by a peer.
    """
    try:
        OrganizationService(db).delete(organization_id)
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
