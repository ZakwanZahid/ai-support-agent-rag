"""Indexes the eval corpus and runs the question set against real retrieval.

Deliberately drives the production code — `chunk_text`, the real embedding
provider, `DocumentChunkRepository.semantic_search` — rather than a
reimplementation. An eval that measures its own copy of the pipeline measures
nothing.

It does skip the HTTP layer and file upload. Those are covered by the test
suite and they are not what varies between runs; putting them in the loop would
only add ways for the harness to fail for reasons unrelated to retrieval.

Everything is created inside a throwaway organization and deleted afterwards,
so running this against a real database leaves nothing behind.
"""

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.tenancy import organization_scope
from app.ingestion.chunking import chunk_text
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.organization_repository import OrganizationRepository
from eval.scoring import QuestionResult


CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.json"


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    expected_documents: list[str]
    expected_phrases: list[str]
    kind: str


def load_questions(path: Path = QUESTIONS_PATH) -> list[Question]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        Question(
            id=entry["id"],
            question=entry["question"],
            expected_documents=entry["expected_documents"],
            expected_phrases=entry.get("expected_phrases", []),
            kind=entry.get("kind", "direct"),
        )
        for entry in payload["questions"]
    ]


def load_corpus(directory: Path = CORPUS_DIR) -> dict[str, str]:
    """Corpus documents keyed by slug, which is what the questions refer to."""
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(directory.glob("*.md"))
    }


@dataclass
class IndexedCorpus:
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    chunk_count: int
    chunks_per_document: dict[str, int]


def index_corpus(
    db: Session,
    *,
    embed_texts: Callable[[list[str]], list[list[float]]],
    corpus: dict[str, str] | None = None,
    chunker: Callable[..., list] = chunk_text,
) -> IndexedCorpus:
    """Create a scratch workspace and index the corpus into it.

    `chunker` is injected so a chunking change can be measured by passing a
    different function, without editing the harness.
    """
    documents = corpus if corpus is not None else load_corpus()

    organization = Organization(
        name="Retrieval eval",
        slug=f"retrieval-eval-{uuid.uuid4().hex[:12]}",
    )
    db.add(organization)
    db.flush()
    # Read before the commit, and never touched afterwards. The tenant scope is
    # applied when a transaction *begins*, so anything that opens one before
    # the scope is entered runs unscoped — and `expire_on_commit` means merely
    # reading `organization.id` after committing would do exactly that, with a
    # refresh query nobody wrote.
    organization_id = organization.id
    db.commit()

    try:
        return _index_into(
            db,
            organization_id=organization_id,
            documents=documents,
            embed_texts=embed_texts,
            chunker=chunker,
        )
    except Exception:
        # The organization is committed before the corpus is indexed, so a
        # failure part-way through would otherwise leave a scratch workspace
        # behind in a real database. Found by leaving one there.
        db.rollback()
        teardown(db, organization_id)
        raise


def _index_into(
    db: Session,
    *,
    organization_id: uuid.UUID,
    documents: dict[str, str],
    embed_texts: Callable[[list[str]], list[list[float]]],
    chunker: Callable[..., list],
) -> IndexedCorpus:
    with organization_scope(str(organization_id)):
        knowledge_base = KnowledgeBase(
            organization_id=organization_id,
            name="Support handbook",
        )
        db.add(knowledge_base)
        db.flush()
        knowledge_base_id = knowledge_base.id

        chunk_repository = DocumentChunkRepository(db)
        chunks_per_document: dict[str, int] = {}
        total = 0

        for slug, text in documents.items():
            document = Document(
                organization_id=organization_id,
                knowledge_base_id=knowledge_base_id,
                title=slug,
                source_type="manual",
                status="indexed",
            )
            db.add(document)
            db.flush()

            pieces = chunker(
                text,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                metadata={"source": slug},
            )
            stored = chunk_repository.create_many(
                organization_id=organization_id,
                document_id=document.id,
                chunks=pieces,
            )
            vectors = embed_texts([chunk.content for chunk in pieces])
            for model, vector in zip(stored, vectors):
                model.embedding = vector

            chunks_per_document[slug] = len(pieces)
            total += len(pieces)

        db.commit()

    return IndexedCorpus(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        chunk_count=total,
        chunks_per_document=chunks_per_document,
    )


def run_questions(
    db: Session,
    indexed: IndexedCorpus,
    questions: list[Question],
    *,
    embed_query: Callable[[str], list[float]],
    top_k: int,
    search: Callable[..., list] | None = None,
    answerer: Callable[[str, list], str] | None = None,
) -> list[QuestionResult]:
    """Ask every question and record which documents came back, in order."""
    repository = DocumentChunkRepository(db)

    def vector_only(*, query_text: str, **kwargs):
        # The question text is passed to every retriever so the harness has one
        # calling convention; a vector search simply has no use for it.
        return repository.semantic_search(**kwargs)

    retrieve = search or vector_only
    results: list[QuestionResult] = []

    with organization_scope(str(indexed.organization_id)):
        for question in questions:
            matches = retrieve(
                organization_id=indexed.organization_id,
                knowledge_base_id=indexed.knowledge_base_id,
                query_embedding=embed_query(question.question),
                query_text=question.question,
                top_k=top_k,
            )
            # Document titles are the corpus slugs, which is what the question
            # set names.
            retrieved = [match.document_title for match in matches]
            top_score = 1.0 - matches[0].distance if matches else None

            answer = None
            missing: list[str] = []
            if answerer is not None:
                answer = answerer(question.question, matches)
                lowered = answer.lower()
                missing = [
                    phrase
                    for phrase in question.expected_phrases
                    if phrase.lower() not in lowered
                ]

            results.append(
                QuestionResult(
                    question_id=question.id,
                    kind=question.kind,
                    expected_documents=question.expected_documents,
                    retrieved_documents=retrieved,
                    top_score=top_score,
                    answer=answer,
                    missing_phrases=missing,
                )
            )

    return results


def teardown(db: Session, organization_id: uuid.UUID) -> None:
    """Remove the scratch workspace, cascades and all."""
    organization = db.get(Organization, organization_id)
    if organization is not None:
        OrganizationRepository(db).delete(organization)
        db.commit()
