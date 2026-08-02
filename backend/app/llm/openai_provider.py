from openai import OpenAI, OpenAIError

from app.core.config import Settings
from app.llm.provider import ChatProviderConfigurationError, ChatProviderError


class OpenAIChatProvider:
    def __init__(self, settings: Settings) -> None:
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise ChatProviderConfigurationError(
                "OPENAI_API_KEY is required when CHAT_PROVIDER=openai"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = settings.chat_model
        self.temperature = settings.chat_temperature

    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except OpenAIError as exc:
            raise ChatProviderError("OpenAI chat generation failed") from exc

        if not completion.choices:
            raise ChatProviderError("OpenAI returned no chat completion choices")
        answer = completion.choices[0].message.content
        if not answer or not answer.strip():
            raise ChatProviderError("OpenAI returned an empty chat response")
        return answer.strip()
