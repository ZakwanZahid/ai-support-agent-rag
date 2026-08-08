from openai import OpenAI, OpenAIError

from app.core.config import Settings
from app.llm.provider import ChatProviderConfigurationError, ChatProviderError
from app.observability.usage import record_chat_usage


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

        # Recorded from the response, before the answer is validated: the
        # tokens were spent whether or not the content turns out to be usable,
        # and a cap that only counts successful calls is a cap a failing model
        # can walk straight through.
        usage = getattr(completion, "usage", None)
        if usage is not None:
            record_chat_usage(
                model=getattr(completion, "model", self.model),
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )

        if not completion.choices:
            raise ChatProviderError("OpenAI returned no chat completion choices")
        answer = completion.choices[0].message.content
        if not answer or not answer.strip():
            raise ChatProviderError("OpenAI returned an empty chat response")
        return answer.strip()
