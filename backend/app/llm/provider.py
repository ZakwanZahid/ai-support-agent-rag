from typing import Protocol


class ChatProviderConfigurationError(Exception):
    """Raised when a configured chat provider cannot be initialized."""


class ChatProviderError(Exception):
    """Raised when a chat provider fails to generate a usable answer."""


class ChatProvider(Protocol):
    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        """Generate one non-streaming grounded answer."""
