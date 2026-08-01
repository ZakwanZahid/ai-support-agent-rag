import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import IndexingRunner, get_db, get_indexing_runner, require_role
from app.models.organization import OrganizationMember
from app.schemas.indexing import IndexingResponse
from app.services.indexing_service import (
    DocumentAlreadyIndexedError,
    DocumentNotReadyForIndexingError,
    IndexingDocumentNotFoundError,
    IndexingService,
)


router = APIRouter(prefix="/organizations/{organization_id}", tags=["indexing"])
owner_or_admin = require_role(["owner", "admin"])


@router.post(
    "/documents/{document_id}/index",
    response_model=IndexingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_document_indexing(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
    indexing_runner: Annotated[IndexingRunner, Depends(get_indexing_runner)],
    force: Annotated[bool, Query()] = False,
) -> IndexingResponse:
    try:
        IndexingService(db).prepare(
            organization_id=organization_id,
            document_id=document_id,
            force=force,
        )
    except IndexingDocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    except DocumentNotReadyForIndexingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not ready for indexing (status: {exc})",
        )
    except DocumentAlreadyIndexedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already indexed; use force=true to re-index it",
        )

    background_tasks.add_task(
        indexing_runner,
        document_id,
        organization_id,
        force,
    )
    return IndexingResponse(document_id=document_id)
