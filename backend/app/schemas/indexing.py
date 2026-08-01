import uuid

from pydantic import BaseModel


class IndexingResponse(BaseModel):
    document_id: uuid.UUID
    status: str = "scheduled"
    message: str = "Document indexing scheduled"
