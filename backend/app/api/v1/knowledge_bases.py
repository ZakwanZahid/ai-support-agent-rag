import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_organization_member, require_role
from app.models.organization import OrganizationMember
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse
from app.services.knowledge_base_service import (
    KnowledgeBaseAlreadyExistsError,
    KnowledgeBaseBusyError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseService,
)


router = APIRouter(
    prefix="/organizations/{organization_id}/knowledge-bases",
    tags=["knowledge bases"],
)
owner_or_admin = require_role(["owner", "admin"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    organization_id: uuid.UUID,
    data: KnowledgeBaseCreate,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
) -> KnowledgeBaseResponse:
    try:
        return KnowledgeBaseService(db).create(
            organization_id=organization_id,
            data=data,
        )
    except KnowledgeBaseAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge base name already exists in this organization",
        )


@router.get("", response_model=list[KnowledgeBaseResponse])
def list_knowledge_bases(
    organization_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> list[KnowledgeBaseResponse]:
    return KnowledgeBaseService(db).list_for_organization(organization_id)


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> KnowledgeBaseResponse:
    try:
        return KnowledgeBaseService(db).get(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
) -> None:
    try:
        KnowledgeBaseService(db).delete(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    except KnowledgeBaseBusyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A document in this knowledge base is being prepared right now. "
                "Wait for it to finish, then delete it."
            ),
        )
