"""Queue behaviour: claims, idempotency, retry classification, and the sweep.

These exercise the job layer directly against the in-memory test database
rather than through a real Redis, so the suite stays free of infrastructure.
What they cover is the logic that decides *whether* work runs and *whether* a
failure is worth repeating — which is where the bugs live. RQ's own scheduling
is the library's responsibility, not ours.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingestion.loaders import TextExtractionError
from app.jobs.claims import claim_document, mark_failed, release_document
from app.jobs.preparation_job import (
    PermanentPreparationError,
    _is_retryable,
    prepare_document_job,
)
from app.jobs.sweep import sweep_stale_preparations
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization



def make_document(db: Session, *, status: str = "pending", **kwargs) -> Document:
    organization = Organization(name=f"Org {uuid.uuid4().hex[:6]}", slug=f"o-{uuid.uuid4().hex[:8]}")
    db.add(organization)
    db.flush()
    knowledge_base = KnowledgeBase(organization_id=organization.id, name="KB", description=None)
    db.add(knowledge_base)
    db.flush()
    document = Document(
        organization_id=organization.id,
        knowledge_base_id=knowledge_base.id,
        title="Policy",
        source_type="upload",
        file_name="policy.txt",
        file_path="storage/uploads/policy.txt",
        mime_type="text/plain",
        status=status,
        **kwargs,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


class TestClaims:
    def test_an_unclaimed_document_can_be_claimed(self, db: Session, session_factory) -> None:
        document = make_document(db)

        granted = claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )

        db.refresh(document)
        assert granted is True
        assert document.status == "processing"
        assert document.preparation_job_id == "job-1"
        assert document.preparation_attempts == 1

    def test_a_second_worker_is_refused_while_the_first_is_live(self, db: Session, session_factory) -> None:
        document = make_document(db)
        assert claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )

        # This is the case that matters: without it two workers would both
        # embed the same chunks and bill twice for the same document.
        granted = claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-2",
        )

        db.refresh(document)
        assert granted is False
        assert document.preparation_job_id == "job-1"
        assert document.preparation_attempts == 1

    def test_the_same_job_can_reclaim_for_its_own_retry(self, db: Session, session_factory) -> None:
        document = make_document(db)
        claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )

        granted = claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )

        db.refresh(document)
        assert granted is True
        assert document.preparation_attempts == 2

    def test_a_claim_from_a_dead_worker_can_be_taken_over(self, db: Session, session_factory) -> None:
        stale = datetime.now(timezone.utc) - timedelta(
            seconds=settings.preparation_stale_after_seconds + 60
        )
        document = make_document(
            db,
            status="processing",
            preparation_job_id="dead-worker",
            preparation_started_at=stale,
        )

        granted = claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-2",
        )

        db.refresh(document)
        assert granted is True
        assert document.preparation_job_id == "job-2"

    def test_releasing_clears_ownership_without_touching_status(self, db: Session, session_factory) -> None:
        document = make_document(db)
        claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )
        document.status = "indexed"
        db.commit()

        release_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
        )

        db.refresh(document)
        assert document.status == "indexed"
        assert document.preparation_job_id is None
        assert document.preparation_started_at is None

    def test_marking_failed_records_the_reason_and_releases(self, db: Session, session_factory) -> None:
        document = make_document(db)
        claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="job-1",
        )

        mark_failed(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            reason="Provider unavailable",
        )

        db.refresh(document)
        assert document.status == "failed"
        assert document.error_message == "Provider unavailable"
        assert document.preparation_job_id is None


class TestRetryClassification:
    def test_bad_input_is_not_retried(self) -> None:
        # These fail identically every time; repeating them spends time and
        # embedding credit to reach the same answer.
        assert _is_retryable(TextExtractionError("no text found")) is False
        assert _is_retryable(PermanentPreparationError("unsupported")) is False

    def test_environment_failures_are_retried(self) -> None:
        assert _is_retryable(TimeoutError("provider timed out")) is True
        assert _is_retryable(ConnectionError("connection reset")) is True

    def test_unrecognized_failures_are_retried(self) -> None:
        # A needless retry is cheaper than a document stuck failed because of
        # a transient error nobody anticipated.
        assert _is_retryable(RuntimeError("something unexpected")) is True


class TestPreparationJob:
    def test_a_claimed_document_is_not_processed_twice(self, db: Session, session_factory) -> None:
        document = make_document(db)
        claim_document(
            db,
            document_id=document.id,
            organization_id=document.organization_id,
            job_id="live-worker",
        )

        calls: list[tuple] = []

        result = prepare_document_job(
            str(document.id),
            str(document.organization_id),
            session_factory=session_factory,
            prepare=lambda *a, **k: calls.append((a, k)),
        )

        assert result == "skipped: already claimed"
        assert calls == []

    def test_a_successful_run_releases_the_claim(self, db: Session, session_factory) -> None:
        document = make_document(db)

        def fake_prepare(document_id, organization_id, force, factory, **kwargs):
            session = factory()
            try:
                doc = session.get(Document, document_id)
                doc.status = "indexed"
                session.commit()
            finally:
                session.close()

        result = prepare_document_job(
            str(document.id),
            str(document.organization_id),
            session_factory=session_factory,
            prepare=fake_prepare,
        )

        db.refresh(document)
        assert result == "completed: indexed"
        assert document.status == "indexed"
        assert document.preparation_job_id is None

    def test_permanent_failures_are_recorded_without_retrying(self, db: Session, session_factory) -> None:
        document = make_document(db)

        def fail_permanently(*args, **kwargs):
            raise TextExtractionError("Document produced no non-empty chunks")

        # Returning rather than raising is what tells the queue not to retry.
        result = prepare_document_job(
            str(document.id),
            str(document.organization_id),
            session_factory=session_factory,
            prepare=fail_permanently,
        )

        db.refresh(document)
        assert result == "failed"
        assert document.status == "failed"
        assert "no non-empty chunks" in document.error_message
        assert document.preparation_job_id is None

    def test_a_transient_failure_is_raised_so_the_queue_retries(self, db: Session, session_factory) -> None:
        document = make_document(db)

        def fail_transiently(*args, **kwargs):
            raise ConnectionError("embedding provider unavailable")

        with pytest.raises(ConnectionError):
            prepare_document_job(
                str(document.id),
                str(document.organization_id),
                session_factory=session_factory,
                prepare=fail_transiently,
            )

        db.refresh(document)
        # The claim is deliberately left in place so the retry of this same job
        # can reclaim the document and continue.
        assert document.preparation_job_id is not None

    def test_a_transient_failure_stops_once_attempts_are_exhausted(self, db: Session, session_factory) -> None:
        document = make_document(db, preparation_attempts=settings.preparation_max_attempts)

        def fail_transiently(*args, **kwargs):
            raise ConnectionError("embedding provider unavailable")

        # Without this ceiling a provider outage would retry forever, and the
        # user would watch a timeline that never settles.
        result = prepare_document_job(
            str(document.id),
            str(document.organization_id),
            session_factory=session_factory,
            prepare=fail_transiently,
        )

        db.refresh(document)
        assert result == "failed"
        assert document.status == "failed"
        assert "after" in document.error_message


class TestStaleSweep:
    def test_a_document_still_working_is_left_alone(self, db: Session, session_factory) -> None:
        document = make_document(
            db,
            status="processing",
            preparation_job_id="live",
            preparation_started_at=datetime.now(timezone.utc),
        )

        acted_on = sweep_stale_preparations(session_factory=session_factory)

        db.refresh(document)
        assert acted_on == []
        assert document.status == "processing"

    def test_an_abandoned_document_is_requeued(self, db: Session, session_factory) -> None:
        stale = datetime.now(timezone.utc) - timedelta(
            seconds=settings.preparation_stale_after_seconds + 60
        )
        document = make_document(
            db,
            status="processing",
            preparation_job_id="dead",
            preparation_started_at=stale,
            preparation_attempts=1,
        )
        requeued: list[tuple] = []

        acted_on = sweep_stale_preparations(
            session_factory=session_factory,
            requeue=lambda d, o, f: requeued.append((d, o, f)),
        )

        db.refresh(document)
        assert acted_on == [str(document.id)]
        assert document.status == "pending"
        assert document.preparation_job_id is None
        assert requeued == [(str(document.id), str(document.organization_id), False)]

    def test_a_document_enqueued_but_never_claimed_is_recovered(
        self, db: Session, session_factory
    ) -> None:
        """The job was lost before any worker touched it.

        The API marks a document processing when it enqueues, so a job that
        never runs — Redis flushed, worker died before claiming — leaves a
        document processing with no claim at all. Sweeping only on the claim
        timestamp would miss it entirely, and it would stay stuck forever.
        """
        document = make_document(db, status="processing")
        assert document.preparation_started_at is None

        # Push updated_at back past the threshold, since that is the only
        # timestamp this document has.
        db.query(Document).filter(Document.id == document.id).update(
            {
                "updated_at": datetime.now(timezone.utc)
                - timedelta(seconds=settings.preparation_stale_after_seconds + 60)
            }
        )
        db.commit()

        requeued: list[tuple] = []
        acted_on = sweep_stale_preparations(
            session_factory=session_factory,
            requeue=lambda d, o, f: requeued.append((d, o, f)),
        )

        db.refresh(document)
        assert acted_on == [str(document.id)]
        assert document.status == "pending"
        assert len(requeued) == 1

    def test_an_abandoned_document_that_has_used_its_attempts_is_failed(self, db: Session, session_factory) -> None:
        stale = datetime.now(timezone.utc) - timedelta(
            seconds=settings.preparation_stale_after_seconds + 60
        )
        document = make_document(
            db,
            status="processing",
            preparation_job_id="dead",
            preparation_started_at=stale,
            preparation_attempts=settings.preparation_max_attempts,
        )
        requeued: list[tuple] = []

        sweep_stale_preparations(
            session_factory=session_factory,
            requeue=lambda d, o, f: requeued.append((d, o, f)),
        )

        db.refresh(document)
        assert document.status == "failed"
        assert "did not recover" in document.error_message
        assert requeued == []


class TestRetryPolicy:
    def test_backoff_provides_one_interval_per_retry(self) -> None:
        intervals = settings.preparation_retry_intervals
        assert len(intervals) == settings.preparation_max_attempts - 1

    def test_backoff_increases(self) -> None:
        # Constant retries against a provider that is down are just a faster
        # way to exhaust the attempt budget.
        intervals = settings.preparation_retry_intervals
        assert intervals == sorted(intervals)
