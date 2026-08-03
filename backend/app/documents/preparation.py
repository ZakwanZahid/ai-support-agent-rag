import logging
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.embeddings.indexing import index_document
from app.ingestion.pipeline import ingest_document
from app.repositories.document_repository import DocumentRepository


logger = logging.getLogger(__name__)

# Statuses meaning the text has been extracted and chunks exist.
EXTRACTED_STATUSES = frozenset({"processed", "indexed"})


def _current_status(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    session_factory: Callable[[], Session],
) -> str | None:
    db = session_factory()
    try:
        document = DocumentRepository(db).get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        return document.status if document is not None else None
    finally:
        db.close()


def prepare_document(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    force: bool = False,
    session_factory: Callable[[], Session] = SessionLocal,
    ingest: Callable[..., None] = ingest_document,
    index: Callable[..., None] = index_document,
) -> None:
    """Take a document from uploaded to searchable in one background task.

    Ingestion and indexing remain separate operations with their own error
    handling; this runs them in order and stops if the first does not produce
    chunks. Clients get a single action to call and a single status to poll,
    rather than having to sequence two endpoints and guess when the first has
    finished.
    """
    status = _current_status(document_id, organization_id, session_factory)
    if status is None:
        return

    # Skip re-chunking a document that has already been extracted, unless the
    # caller is explicitly replacing its content.
    if force or status not in EXTRACTED_STATUSES:
        ingest(document_id, organization_id, force, session_factory)

    status = _current_status(document_id, organization_id, session_factory)
    if status not in EXTRACTED_STATUSES:
        # Ingestion failed and has already recorded the reason on the document.
        logger.info(
            "Skipping indexing because ingestion did not complete",
            extra={
                "document_id": str(document_id),
                "organization_id": str(organization_id),
                "status": status,
            },
        )
        return

    index(document_id, organization_id, force, session_factory)
