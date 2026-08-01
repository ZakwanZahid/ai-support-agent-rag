from app.core.config import Settings, settings
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.provider import EmbeddingProvider


class UnsupportedEmbeddingProviderError(Exception):
    pass


def get_embedding_provider(
    app_settings: Settings = settings,
) -> EmbeddingProvider:
    if app_settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(app_settings)

    # Add Gemini, Voyage, Cohere, or local sentence-transformer adapters here.
    raise UnsupportedEmbeddingProviderError(
        f"Unsupported embedding provider: {app_settings.embedding_provider}"
    )
