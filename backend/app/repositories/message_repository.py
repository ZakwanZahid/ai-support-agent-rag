import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Message, MessageCitation
from app.schemas.pagination import CursorPosition


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _next_timestamp(self, conversation_id: uuid.UUID) -> datetime:
        """A creation time strictly later than every message already in the thread.

        Messages are ordered by `created_at`, and the only tiebreak is the
        primary key, which is a random UUID. A question and its answer are
        written milliseconds apart, inside the resolution of the system clock on
        some platforms, so the two can share a timestamp and then sort
        arbitrarily: an answer can appear above the question that produced it.
        Nudging each new message past the last keeps the order stable without
        adding a sequence column.
        """
        now = datetime.now(timezone.utc)
        latest = self.db.scalar(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == conversation_id
            )
        )
        if latest is None:
            return now

        # SQLite hands back naive datetimes; Postgres hands back aware ones.
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)

        return now if now > latest else latest + timedelta(microseconds=1)

    def list_page(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int,
        before: CursorPosition | None = None,
    ) -> tuple[list[Message], bool]:
        """The newest messages in a thread, oldest-first, plus whether older remain.

        A chat thread pages backwards, not forwards: opening it should show
        the end of the conversation, and "load earlier" walks towards the
        start. So the query sorts descending to take the most recent `limit`,
        and the result is reversed before returning, because that is the order
        the thread is read in.
        """
        statement = select(Message).where(
            Message.organization_id == organization_id,
            Message.conversation_id == conversation_id,
        )
        if before is not None:
            created_at, message_id = before
            statement = statement.where(
                tuple_(Message.created_at, Message.id)
                < tuple_(literal(created_at), literal(message_id))
            )
        statement = (
            statement.options(
                # Citations are rendered with every assistant message, so
                # loading them per row would be one query per message.
                selectinload(Message.citations).selectinload(MessageCitation.document),
                selectinload(Message.citations).selectinload(MessageCitation.chunk),
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit + 1)
        )

        rows = list(self.db.scalars(statement).all())
        has_more = len(rows) > limit
        return list(reversed(rows[:limit])), has_more

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            organization_id=organization_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=self._next_timestamp(conversation_id),
        )
        self.db.add(message)
        self.db.flush()
        return message
