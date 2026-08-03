import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PreparationRunner, get_db, get_preparation_runner, require_role
from app.models.organization import OrganizationMember
from app.schemas.document import PreparationScheduledResponse
from app.services.preparation_service import (
    DocumentAlreadyPreparedError,
    DocumentPreparationInProgressError,
    PreparationDocumentNotFoundError,
    PreparationFileNotFoundError,
    PreparationService,
)


router = APIRouter(prefix="/organizations/{organization_id}", tags=["preparation"])
owner_or_admin = require_role(["owner", "admin"])


@router.post(
    "/documents/{document_id}/prepare",
    response_model=PreparationScheduledResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def prepare_document_for_chat(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
    preparation_runner: Annotated[PreparationRunner, Depends(get_preparation_runner)],
    force: Annotated[bool, Query()] = False,
) -> PreparationScheduledResponse:
    """Extract and index a document in one step.

    Clients poll the document until its status is `indexed` or `failed`.
    """
    try:
        document = PreparationService(db).start(
            organization_id=organization_id,
            document_id=document_id,
            force=force,
        )
    except PreparationDocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    except PreparationFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document file is missing from storage",
        )
    except DocumentPreparationInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document is already being prepared",
        )
    except DocumentAlreadyPreparedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already ready; use force=true to prepare it again",
        )

    background_tasks.add_task(
        preparation_runner,
        document_id,
        organization_id,
        force,
    )
    return PreparationScheduledResponse(
        document_id=document_id,
        status=document.status,
    )
