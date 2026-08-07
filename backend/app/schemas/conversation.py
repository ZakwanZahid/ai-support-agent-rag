import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    knowledge_base_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID
    quote: str
    score: float
    chunk_metadata: dict[str, Any] | None


class MessageResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    citations: list[CitationResponse] = Field(default_factory=list)


MESSAGE_PREVIEW_MAX_CHARS = 160


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    knowledge_base_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime
    # Included so a conversation list can show a preview without loading every
    # message in every thread.
    message_count: int = 0
    last_message_preview: str | None = None


class ConversationDetailResponse(ConversationResponse):
    """A thread with its most recent messages, not necessarily all of them.

    Opening a thread should cost the same whether it holds ten messages or a
    thousand, so this carries one page — the newest — and says whether older
    ones exist. `next_message_cursor` walks backwards through them via
    `GET /conversations/{id}/messages`.
    """

    messages: list[MessageResponse]
    has_more_messages: bool = False
    next_message_cursor: str | None = None


class ChatMessageRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    knowledge_base_id: uuid.UUID
    top_k: int = Field(default=settings.rag_top_k, ge=1, le=50)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank")
        return value


class ChatMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    answer: str
    citations: list[CitationResponse]
