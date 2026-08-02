import uuid

from sqlalchemy.orm import Session

from app.models.conversation import MessageCitation
from app.rag.citation_builder import CitationData


class MessageCitationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(
        self,
        *,
        organization_id: uuid.UUID,
        message_id: uuid.UUID,
        citations: list[CitationData],
    ) -> list[MessageCitation]:
        models = [
            MessageCitation(
                organization_id=organization_id,
                message_id=message_id,
                document_id=citation.document_id,
                chunk_id=citation.chunk_id,
                quote=citation.quote,
                score=citation.score,
            )
            for citation in citations
        ]
        self.db.add_all(models)
        self.db.flush()
        return models
