import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.embeddings.provider import EmbeddingProvider
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchResult


class SearchKnowledgeBaseNotFoundError(Exception):
    pass


class SearchService:
    def __init__(
        self,
        *,
        db: Session,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.knowledge_bases = KnowledgeBaseRepository(db)
        self.chunks = DocumentChunkRepository(db)
        self.embedding_provider = embedding_provider

    def search(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        data: SearchRequest,
    ) -> SearchResponse:
        knowledge_base = self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )
        if knowledge_base is None:
            raise SearchKnowledgeBaseNotFoundError

        query_embedding = self.embedding_provider.embed_query(data.query)
        if len(query_embedding) != settings.embedding_dimensions:
            raise ValueError(
                f"Expected {settings.embedding_dimensions} query dimensions, "
                f"received {len(query_embedding)}"
            )

        matches = self.chunks.semantic_search(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            top_k=data.top_k,
        )
        return SearchResponse(
            query=data.query,
            results=[
                SearchResult(
                    chunk_id=match.chunk_id,
                    document_id=match.document_id,
                    document_title=match.document_title,
                    content=match.content,
                    score=1.0 - match.distance,
                    distance=match.distance,
                    chunk_metadata=match.chunk_metadata,
                )
                for match in matches
            ],
        )
