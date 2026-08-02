import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Message


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

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
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(message)
        self.db.flush()
        return message
