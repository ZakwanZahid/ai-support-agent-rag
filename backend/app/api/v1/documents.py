import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import (
    IngestionRunner,
    get_db,
    get_ingestion_runner,
    require_organization_member,
    require_role,
)
from app.core.config import settings
from app.models.document import Document
from app.models.organization import OrganizationMember
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    InvalidUploadError,
    KnowledgeBaseNotFoundError,
    UnsupportedDocumentTypeError,
    UploadTooLargeError,
)


router = APIRouter(prefix="/organizations/{organization_id}", tags=["documents"])
owner_or_admin = require_role(["owner", "admin"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[OrganizationMember, Depends(owner_or_admin)],
    ingestion_runner: Annotated[IngestionRunner, Depends(get_ingestion_runner)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> Document:
    try:
        document = await DocumentService(db).upload(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            file=file,
            title=title,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    except UnsupportedDocumentTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document type",
        )
    except InvalidUploadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file or title is invalid",
        )
    except UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the configured size limit",
        )
    except DocumentStorageError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store the uploaded document",
        )
    if settings.auto_ingest_on_upload:
        background_tasks.add_task(
            ingestion_runner,
            document.id,
            organization_id,
            False,
        )
    return document


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    organization_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    knowledge_base_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[Document]:
    return DocumentService(db).list_for_organization(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> Document:
    try:
        return DocumentService(db).get(
            organization_id=organization_id,
            document_id=document_id,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
