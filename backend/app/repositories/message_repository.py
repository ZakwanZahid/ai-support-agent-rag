import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Message


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
