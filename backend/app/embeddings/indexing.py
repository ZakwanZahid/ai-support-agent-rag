import logging
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.embeddings.factory import get_embedding_provider
from app.embeddings.provider import EmbeddingProvider
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository


logger = logging.getLogger(__name__)


class IndexingError(Exception):
    pass


def index_document(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    force: bool = False,
    session_factory: Callable[[], Session] = SessionLocal,
    provider_factory: Callable[[], EmbeddingProvider] = get_embedding_provider,
) -> None:
    db = session_factory()
    documents = DocumentRepository(db)
    chunks = DocumentChunkRepository(db)

    try:
        document = documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if document is None:
            return
        if document.status not in {"processed", "indexed"}:
            raise IndexingError(
                f"Document must be processed before indexing; current status is {document.status}"
            )

        all_chunks = chunks.list_for_indexing(
            organization_id=organization_id,
            document_id=document_id,
            include_embedded=True,
        )
        if not all_chunks:
            raise IndexingError("Document has no chunks to index")

        target_chunks = (
            all_chunks
            if force
            else [chunk for chunk in all_chunks if chunk.embedding is None]
        )
        if target_chunks:
            provider = provider_factory()
            for batch_start in range(0, len(target_chunks), settings.index_batch_size):
                batch = target_chunks[
                    batch_start : batch_start + settings.index_batch_size
                ]
                embeddings = provider.embed_texts([chunk.content for chunk in batch])
                if len(embeddings) != len(batch):
                    raise IndexingError(
                        "Embedding provider returned a different number of vectors than chunks"
                    )
                for chunk, embedding in zip(batch, embeddings):
                    if len(embedding) != settings.embedding_dimensions:
                        raise IndexingError(
                            f"Expected {settings.embedding_dimensions} embedding dimensions, "
                            f"received {len(embedding)}"
                        )
                    chunk.embedding = embedding

        db.flush()
        missing_count = chunks.count_without_embeddings(
            organization_id=organization_id,
            document_id=document_id,
        )
        if missing_count:
            raise IndexingError(
                f"Document still has {missing_count} chunks without embeddings"
            )

        document.status = "indexed"
        document.error_message = None
        db.commit()
    except Exception as exc:
        logger.exception(
            "Document indexing failed",
            extra={
                "document_id": str(document_id),
                "organization_id": str(organization_id),
            },
        )
        db.rollback()
        failed_document = documents.get_by_id(
            organization_id=organization_id,
            document_id=document_id,
        )
        if failed_document is not None:
            failed_document.status = "failed"
            failed_document.error_message = str(exc)[:4000]
            db.commit()
    finally:
        db.close()
