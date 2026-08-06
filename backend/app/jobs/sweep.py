import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document


logger = logging.getLogger(__name__)


def sweep_stale_preparations(
    session_factory: Callable[[], Session] = SessionLocal,
    requeue: Callable[[str, str, bool], object] | None = None,
) -> list[str]:
    """Recover documents whose worker died mid-preparation.

    A worker killed between claiming a document and finishing it leaves that
    document in `processing` forever: the queue has no job for it, and the API
    will not start another because the status looks busy. Nothing in the system
    notices, and the user watches a progress timeline that will never move.

    This finds documents that have been claimed for longer than any real
    preparation should take and either requeues them or fails them, depending
    on how many attempts they have already had. Returns the document ids acted
    on, so a caller can log or report the count.

    Deliberately conservative: the threshold has to exceed the slowest genuine
    preparation, because failing a document that is merely slow is worse than
    recovering it a few minutes later.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.preparation_stale_after_seconds
    )

    db = session_factory()
    acted_on: list[str] = []
    try:
        # Two different ways a document ends up abandoned, and the sweep has to
        # catch both:
        #
        #   1. A worker claimed it and then died. `preparation_started_at` is
        #      set and has stopped advancing.
        #   2. The API marked it processing and enqueued a job that never ran —
        #      Redis was flushed, or the worker died before claiming. There is
        #      no claim at all, so the only timestamp available is `updated_at`.
        #
        # Comparing against whichever timestamp exists covers both without
        # needing a separate query.
        reference = func.coalesce(
            Document.preparation_started_at,
            Document.updated_at,
        )
        stale = db.scalars(
            select(Document).where(
                Document.status == "processing",
                reference < cutoff,
            )
        ).all()

        for document in stale:
            document_id = str(document.id)
            organization_id = str(document.organization_id)
            exhausted = document.preparation_attempts >= settings.preparation_max_attempts

            if exhausted or requeue is None:
                document.status = "failed"
                document.error_message = (
                    "Preparation stopped unexpectedly and did not recover. "
                    "Try preparing this document again."
                )
                document.preparation_job_id = None
                document.preparation_started_at = None
                logger.error(
                    "Failing stale preparation",
                    extra={
                        "document_id": document_id,
                        "attempts": document.preparation_attempts,
                    },
                )
            else:
                # Clearing the claim is what lets the requeued job take it: the
                # claim check treats an unowned document as available.
                document.preparation_job_id = None
                document.preparation_started_at = None
                document.status = "pending"
                logger.warning(
                    "Requeueing stale preparation",
                    extra={
                        "document_id": document_id,
                        "attempts": document.preparation_attempts,
                    },
                )

            acted_on.append(document_id)

        db.commit()

        if requeue is not None:
            for document in stale:
                if document.status == "pending":
                    requeue(str(document.id), str(document.organization_id), False)
    finally:
        db.close()

    return acted_on
