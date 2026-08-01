from typing import Protocol


class EmbeddingConfigurationError(Exception):
    pass


class EmbeddingDimensionError(Exception):
    pass


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed document text while preserving input order."""

    def embed_query(self, query: str) -> list[float]:
        """Embed one semantic-search query."""
