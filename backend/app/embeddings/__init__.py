"""Embedding provider abstractions and indexing orchestration."""

from app.embeddings.factory import get_embedding_provider
from app.embeddings.provider import EmbeddingProvider

__all__ = ["EmbeddingProvider", "get_embedding_provider"]
