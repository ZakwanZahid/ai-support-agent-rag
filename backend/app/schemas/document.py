import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
