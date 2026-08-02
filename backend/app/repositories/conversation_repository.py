import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message, MessageCitation


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None,
        knowledge_base_id: uuid.UUID | None,
    ) -> Conversation:
        conversation = Conversation(
            organization_id=organization_id,
            user_id=user_id,
            title=title,
            knowledge_base_id=knowledge_base_id,
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get_by_id(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        with_messages: bool = False,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
        if with_messages:
            statement = statement.options(
                selectinload(Conversation.messages)
                .selectinload(Message.citations)
                .selectinload(MessageCitation.document),
                selectinload(Conversation.messages)
                .selectinload(Message.citations)
                .selectinload(MessageCitation.chunk),
            )
        return self.db.scalar(statement)

    def list_for_user(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.updated_at.desc(), Conversation.id)
        )
        return list(self.db.scalars(statement).all())

    @staticmethod
    def touch(conversation: Conversation) -> None:
        conversation.updated_at = datetime.now(timezone.utc)
