import logging
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.tenancy import organization_scope
from app.observability.context import request_context, set_actor
from app.documents.preparation import prepare_document
from app.ingestion.loaders import TextExtractionError
from app.jobs.claims import claim_document, mark_failed, release_document
from app.models.document import Document


logger = logging.getLogger(__name__)


class PermanentPreparationError(Exception):
    """A failure that retrying cannot fix.

    A corrupt file, an unsupported type, or a document that yields no text will
    fail identically every time. Retrying spends time and, once embeddings are
    involved, money, to reach the same answer.
    """


def _is_retryable(error: BaseException) -> bool:
    """Whether another attempt could plausibly succeed.

    The distinction that matters is between the input and the environment. A
    document that produced no text is bad input and will produce no text again.
    A provider timeout or a 5xx is the environment, and the same document may
    well succeed in a minute.

    Anything unrecognized is treated as retryable, on the grounds that a
    needless retry is cheaper than a document stuck failed because of a
    transient error nobody anticipated.
    """
    if isinstance(error, (PermanentPreparationError, TextExtractionError)):
        return False
    return True


def prepare_document_job(
    document_id: str,
    organization_id: str,
    force: bool = False,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    prepare: Callable[..., None] = prepare_document,
) -> str:
    """Prepare a document for chat. The unit of work the queue retries.

    Returns a short outcome string, which RQ stores on the job and which the
    tests assert against.

    Identifiers arrive as strings because they travel through Redis as JSON.
    """
    from rq import get_current_job

    job = get_current_job()
    job_id = job.id if job is not None else f"direct-{uuid.uuid4().hex[:12]}"

    document_uuid = uuid.UUID(document_id)
    organization_uuid = uuid.UUID(organization_id)

    # A job has no request to inherit a tenant scope from, so it declares its
    # own. Without this every query it makes would be refused by the policies.
    # Same for the log context: the job id is what ties its lines together,
    # standing in for the request id an API call would have.
    with organization_scope(organization_id), request_context(job_id):
        set_actor(organization_id=organization_id, document_id=document_id)
        return _run(
            document_uuid,
            organization_uuid,
            force,
            job_id=job_id,
            session_factory=session_factory,
            prepare=prepare,
        )


def _run(
    document_uuid: uuid.UUID,
    organization_uuid: uuid.UUID,
    force: bool,
    *,
    job_id: str,
    session_factory: Callable[[], Session],
    prepare: Callable[..., None],
) -> str:
    document_id = str(document_uuid)
    organization_id = str(organization_uuid)

    db = session_factory()
    try:
        if not claim_document(
            db,
            document_id=document_uuid,
            organization_id=organization_uuid,
            job_id=job_id,
        ):
            # Another worker holds a live claim. Doing the work anyway would
            # duplicate its writes and its embedding spend.
            logger.info(
                "Skipping preparation; document is already claimed",
                extra={"document_id": document_id, "job_id": job_id},
            )
            return "skipped: already claimed"

        document = db.get(Document, document_uuid)
        if document is None:
            return "skipped: document no longer exists"
        attempts = document.preparation_attempts
    finally:
        db.close()

    try:
        prepare(
            document_uuid,
            organization_uuid,
            force,
            session_factory,
            raise_on_error=True,
        )
    except BaseException as error:  # noqa: BLE001 - classified and re-raised below
        retryable = _is_retryable(error)
        exhausted = attempts >= settings.preparation_max_attempts

        db = session_factory()
        try:
            if retryable and not exhausted:
                # Leave the claim in place so the retry of this same job can
                # reclaim it, and let the exception reach RQ so it schedules one.
                logger.warning(
                    "Preparation attempt failed; will retry",
                    extra={
                        "document_id": document_id,
                        "attempt": attempts,
                        "max_attempts": settings.preparation_max_attempts,
                        "error": str(error),
                    },
                )
                raise

            reason = (
                str(error)
                if not retryable
                else f"Preparation failed after {attempts} attempts: {error}"
            )
            mark_failed(
                db,
                document_id=document_uuid,
                organization_id=organization_uuid,
                reason=reason,
            )
            logger.error(
                "Preparation failed permanently",
                extra={
                    "document_id": document_id,
                    "retryable": retryable,
                    "attempts": attempts,
                },
            )
        finally:
            db.close()

        # Swallowed deliberately: the outcome is recorded on the document, and
        # re-raising would make RQ schedule a retry we have decided against.
        return "failed"

    db = session_factory()
    try:
        release_document(
            db,
            document_id=document_uuid,
            organization_id=organization_uuid,
        )
        document = db.get(Document, document_uuid)
        return f"completed: {document.status if document else 'unknown'}"
    finally:
        db.close()
