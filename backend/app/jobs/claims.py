import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document


def _stale_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        seconds=settings.preparation_stale_after_seconds
    )


def claim_document(
    db: Session,
    *,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    job_id: str,
) -> bool:
    """Take ownership of a document for preparation. Returns whether we got it.

    This is the concurrency half of idempotency. The effects of preparation are
    already safe to repeat — extraction replaces chunks wholesale, and indexing
    only embeds chunks that have no vector yet — but two workers running at the
    same time would still race each other's writes and could double-charge for
    embeddings on chunks neither has committed yet.

    The claim is a single conditional UPDATE, so the database decides the
    winner. Checking first and then writing would leave a window between the
    two statements where both workers believe they are clear to proceed.

    A claim is granted when the document is not already owned, when the
    previous owner has gone quiet for longer than the stale threshold (its
    worker died), or when the caller already owns it, which is what lets a
    retry of the same job continue its own work.
    """
    statement = (
        update(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == organization_id,
            (
                (Document.preparation_started_at.is_(None))
                | (Document.preparation_started_at < _stale_cutoff())
                | (Document.preparation_job_id == job_id)
                | (Document.status != "processing")
            ),
        )
        .values(
            status="processing",
            error_message=None,
            preparation_job_id=job_id,
            preparation_started_at=datetime.now(timezone.utc),
            preparation_attempts=Document.preparation_attempts + 1,
        )
        # Evaluate the condition in the database rather than in Python. The
        # ORM's in-session evaluation cannot compare a stored naive timestamp
        # against an aware one, and pushing the whole statement down is what
        # makes the claim atomic in the first place.
        .execution_options(synchronize_session=False)
    )
    result = db.execute(statement)
    db.commit()
    return result.rowcount > 0


def release_document(
    db: Session,
    *,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Clear ownership once a document has settled.

    Leaving a stale job id behind would make a later sweep think the document
    is mid-flight, so this runs whether the outcome was success or failure.
    """
    db.execute(
        update(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .values(preparation_job_id=None, preparation_started_at=None)
    )
    db.commit()


def mark_failed(
    db: Session,
    *,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    reason: str,
) -> None:
    """Record a terminal failure and release the claim."""
    db.execute(
        update(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .values(
            status="failed",
            error_message=reason[:4000],
            preparation_job_id=None,
            preparation_started_at=None,
        )
    )
    db.commit()
