from app.core.config import Settings, settings
from app.llm.openai_provider import OpenAIChatProvider
from app.llm.provider import ChatProvider


class UnsupportedChatProviderError(Exception):
    pass


def get_chat_provider(app_settings: Settings = settings) -> ChatProvider:
    if app_settings.chat_provider == "openai":
        return OpenAIChatProvider(app_settings)

    # Add Gemini, Anthropic, or local-model adapters here without changing RAG.
    raise UnsupportedChatProviderError(
        f"Unsupported chat provider: {app_settings.chat_provider}"
    )
