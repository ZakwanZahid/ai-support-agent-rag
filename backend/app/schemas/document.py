import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import Page


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    title: str
    source_type: str
    file_name: str | None
    file_path: str | None
    mime_type: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentPage(Page[DocumentResponse]):
    """A page of documents, plus the numbers on the filter controls.

    The counts ride along rather than living behind their own endpoint: they
    describe the same filtered set the page came from, and fetching them
    separately would let the two drift apart between requests.
    """

    status_counts: dict[str, int] = Field(default_factory=dict)


class IngestionScheduledResponse(BaseModel):
    document_id: uuid.UUID
    status: str = "processing"
    message: str = "Document ingestion scheduled"


class PreparationScheduledResponse(BaseModel):
    document_id: uuid.UUID
    status: str = "processing"
    message: str = "Document is being prepared for chat"
