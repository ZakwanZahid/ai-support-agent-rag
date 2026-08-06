import logging

from rq import Retry

from app.core.config import settings
from app.jobs.preparation_job import prepare_document_job
from app.jobs.queue import get_preparation_queue


logger = logging.getLogger(__name__)


def enqueue_preparation(
    document_id: str,
    organization_id: str,
    force: bool = False,
) -> str:
    """Queue a document for preparation and return the job id.

    Retries are configured here rather than inside the job because RQ owns the
    scheduling. The job decides whether a given failure *deserves* a retry; the
    queue decides when the retry happens.
    """
    job = get_preparation_queue().enqueue(
        prepare_document_job,
        str(document_id),
        str(organization_id),
        force,
        retry=Retry(
            max=settings.preparation_max_attempts,
            interval=settings.preparation_retry_intervals,
        ),
        job_timeout=settings.preparation_job_timeout_seconds,
        # Keeping finished jobs briefly makes it possible to inspect an
        # outcome after the fact without a full job history store.
        result_ttl=3600,
        failure_ttl=86400,
        description=f"prepare document {document_id}",
    )
    logger.info(
        "Queued document preparation",
        extra={"document_id": str(document_id), "job_id": job.id},
    )
    return job.id
