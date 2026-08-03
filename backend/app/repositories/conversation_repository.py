import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message, MessageCitation


@dataclass(frozen=True)
class ConversationSummary:
    conversation: Conversation
    message_count: int
    last_message: str | None


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

    def list_summaries_for_user(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ConversationSummary]:
        """Conversations with their message count and latest message.

        Both aggregates are correlated subqueries so the whole list costs one
        query rather than two per conversation.
        """
        message_count = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        last_message = (
            select(Message.content)
            .where(Message.conversation_id == Conversation.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )

        statement = (
            select(Conversation, message_count, last_message)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.updated_at.desc(), Conversation.id)
        )
        return [
            ConversationSummary(
                conversation=conversation,
                message_count=count,
                last_message=content,
            )
            for conversation, count, content in self.db.execute(statement).all()
        ]

    @staticmethod
    def touch(conversation: Conversation) -> None:
        conversation.updated_at = datetime.now(timezone.utc)
