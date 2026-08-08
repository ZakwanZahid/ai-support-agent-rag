from openai import OpenAI

from app.core.config import Settings
from app.embeddings.provider import (
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
)
from app.observability.usage import record_embedding_usage


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise EmbeddingConfigurationError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai"
            )
        self.client = OpenAI(api_key=api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_embedding_usage(
                model=getattr(response, "model", self.model),
                tokens=usage.total_tokens or 0,
            )

        ordered = sorted(response.data, key=lambda item: item.index)
        embeddings = [item.embedding for item in ordered]
        if len(embeddings) != len(texts):
            raise EmbeddingDimensionError(
                "Embedding provider returned a different number of vectors than inputs"
            )
        for embedding in embeddings:
            self._validate_dimensions(embedding)
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        embeddings = self.embed_texts([query])
        return embeddings[0]

    def _validate_dimensions(self, embedding: list[float]) -> None:
        if len(embedding) != self.dimensions:
            raise EmbeddingDimensionError(
                f"Expected {self.dimensions} embedding dimensions, "
                f"received {len(embedding)}"
            )
