import uuid

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.organization import OrganizationMember
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.conversation import (
    MESSAGE_PREVIEW_MAX_CHARS,
    CitationResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)


def _preview(content: str | None) -> str | None:
    """Collapse a message to a single line short enough for a list row."""
    if not content:
        return None
    collapsed = " ".join(content.split())
    if len(collapsed) <= MESSAGE_PREVIEW_MAX_CHARS:
        return collapsed
    return f"{collapsed[:MESSAGE_PREVIEW_MAX_CHARS].rstrip()}…"


class ConversationNotFoundError(Exception):
    pass


class ConversationAccessDeniedError(Exception):
    pass


class ConversationKnowledgeBaseNotFoundError(Exception):
    pass


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.knowledge_bases = KnowledgeBaseRepository(db)

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        user: User,
        data: ConversationCreate,
    ) -> Conversation:
        if data.knowledge_base_id is not None:
            knowledge_base = self.knowledge_bases.get_by_id(
                organization_id=organization_id,
                knowledge_base_id=data.knowledge_base_id,
            )
            if knowledge_base is None:
                raise ConversationKnowledgeBaseNotFoundError

        conversation = self.conversations.create(
            organization_id=organization_id,
            user_id=user.id,
            title=data.title,
            knowledge_base_id=data.knowledge_base_id,
        )
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_for_user(
        self,
        *,
        organization_id: uuid.UUID,
        user: User,
    ) -> list[ConversationResponse]:
        summaries = self.conversations.list_summaries_for_user(
            organization_id=organization_id,
            user_id=user.id,
        )
        return [
            ConversationResponse.model_validate(summary.conversation).model_copy(
                update={
                    "message_count": summary.message_count,
                    "last_message_preview": _preview(summary.last_message),
                },
            )
            for summary in summaries
        ]

    def get_detail(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user: User,
        membership: OrganizationMember,
    ) -> ConversationDetailResponse:
        conversation = self.conversations.get_by_id(
            organization_id=organization_id,
            conversation_id=conversation_id,
            with_messages=True,
        )
        if conversation is None:
            raise ConversationNotFoundError
        self.ensure_access(
            conversation=conversation,
            user=user,
            membership=membership,
        )
        return ConversationDetailResponse(
            id=conversation.id,
            organization_id=conversation.organization_id,
            user_id=conversation.user_id,
            knowledge_base_id=conversation.knowledge_base_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                MessageResponse(
                    id=message.id,
                    organization_id=message.organization_id,
                    conversation_id=message.conversation_id,
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                    citations=[
                        CitationResponse(
                            document_id=citation.document_id,
                            document_title=citation.document.title,
                            chunk_id=citation.chunk_id,
                            quote=citation.quote or "",
                            score=(
                                citation.score
                                if citation.score is not None
                                else 0.0
                            ),
                            chunk_metadata=citation.chunk.chunk_metadata,
                        )
                        for citation in message.citations
                    ],
                )
                for message in conversation.messages
            ],
        )

    @staticmethod
    def ensure_access(
        *,
        conversation: Conversation,
        user: User,
        membership: OrganizationMember,
    ) -> None:
        if conversation.user_id == user.id:
            return
        if membership.role in {"owner", "admin"}:
            return
        raise ConversationAccessDeniedError
