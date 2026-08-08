"""Counting what the model providers actually charged for.

Token counts come from the provider's own response, not from a local
tokenizer. A tokenizer is an estimate, and an estimate of a bill is a second
source of truth that drifts from the real one — which is the worst possible
property for the number a spending cap is enforced against.

Providers report into a context-scoped accumulator rather than returning usage
alongside their result. Returning it would change the signature of every
provider, every fake in the test suite, and every caller, none of which has any
other interest in billing. Same mechanism and the same trade-off as the tenant
scope in `app/db/tenancy.py`: invisible at the call site, and free of plumbing
through code that does not care.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Usage:
    """Tokens spent during one request or one job."""

    embedding_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_calls: int = 0
    chat_calls: int = 0
    # Which models were involved, so a cost can be worked out later from the
    # price of the model actually used rather than the one now configured.
    models: dict[str, int] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.embedding_tokens + self.prompt_tokens + self.completion_tokens

    def record_embedding(self, *, model: str, tokens: int) -> None:
        self.embedding_tokens += tokens
        self.embedding_calls += 1
        self.models[model] = self.models.get(model, 0) + tokens

    def record_chat(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.chat_calls += 1
        total = prompt_tokens + completion_tokens
        self.models[model] = self.models.get(model, 0) + total

    def as_log_fields(self) -> dict[str, int]:
        return {
            "embedding_tokens": self.embedding_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


_current_usage: ContextVar[Usage | None] = ContextVar("current_usage", default=None)


def current_usage() -> Usage | None:
    return _current_usage.get()


def record_embedding_usage(*, model: str, tokens: int) -> None:
    """Called by a provider. Silently does nothing outside a tracked scope.

    Deliberately forgiving: a provider used from a script, a migration, or the
    eval harness should not fail because nothing is counting.
    """
    usage = _current_usage.get()
    if usage is not None:
        usage.record_embedding(model=model, tokens=tokens)


def record_chat_usage(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    usage = _current_usage.get()
    if usage is not None:
        usage.record_chat(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


@contextmanager
def track_usage() -> Iterator[Usage]:
    """Collect provider usage for the duration of this block."""
    usage = Usage()
    token = _current_usage.set(usage)
    try:
        yield usage
    finally:
        _current_usage.reset(token)
