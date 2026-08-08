"""The daily spending cap, and the recording that feeds it.

This is the other half of the rate limiting in ADR-037. A per-minute limit
bounds a burst; it does not bound a day. Twenty chat messages a minute is
nearly thirty thousand a day, which is a bill nobody intended. The rate limit
stops a loop from running away in seconds; this stops it from running away
overnight.

Two properties differ from the rate limiter on purpose:

* It counts **tokens reported by the provider**, not requests. Requests are a
  poor proxy for spend — one question against a large context costs many times
  another.
* It is stored in Postgres and **fails closed**. The rate limiter allows
  requests through when Redis is unreachable, because a limiter outage should
  not be a login outage. Here the store is the same database the request needs
  anyway, so there is no partial-availability case to trade against, and an
  uncountable request is one that should not be made.
"""

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.observability.pricing import estimate_cost_usd, is_priced
from app.observability.usage import Usage
from app.repositories.usage_repository import UsageRepository


logger = logging.getLogger(__name__)


class DailyBudgetExceededError(Exception):
    def __init__(self, used: int, limit: int) -> None:
        super().__init__(f"Daily token budget exhausted: {used} of {limit}")
        self.used = used
        self.limit = limit


@dataclass(frozen=True)
class BudgetStatus:
    used_tokens: int
    limit_tokens: int
    estimated_cost_usd: Decimal

    @property
    def remaining_tokens(self) -> int:
        return max(self.limit_tokens - self.used_tokens, 0)

    @property
    def exhausted(self) -> bool:
        return self.limit_tokens > 0 and self.used_tokens >= self.limit_tokens


class UsageService:
    def __init__(
        self,
        db: Session,
        app_settings: Settings = default_settings,
    ) -> None:
        self.db = db
        self.usage = UsageRepository(db)
        self.settings = app_settings

    def status(self, organization_id: uuid.UUID) -> BudgetStatus:
        day = self.usage.get_day(organization_id=organization_id)
        return BudgetStatus(
            used_tokens=day.total_tokens if day else 0,
            limit_tokens=self.settings.daily_token_budget,
            estimated_cost_usd=(
                Decimal(day.estimated_cost_usd) if day else Decimal(0)
            ),
        )

    def check(self, organization_id: uuid.UUID) -> BudgetStatus:
        """Refuse the request if today's budget is already spent.

        Checked before the call, against what has already been committed. A
        request that starts just under the limit is allowed to finish and can
        take the total past it — the same overshoot a fixed rate-limit window
        has, and for the same reason: the alternative is reserving tokens
        before knowing how many the call will use, which means estimating, and
        an estimate is what this design avoids everywhere else.
        """
        status = self.status(organization_id)
        if not self.settings.daily_budget_enabled or self.settings.daily_token_budget <= 0:
            return status
        if status.exhausted:
            raise DailyBudgetExceededError(status.used_tokens, status.limit_tokens)
        return status

    def record(self, organization_id: uuid.UUID, usage: Usage) -> None:
        """Persist what a request spent. Never raises into the caller's path.

        The work has already happened and the user already has their answer; a
        failure to write the meter must not turn a successful request into an
        error. It is logged loudly instead, because silently uncounted spend is
        how a cap stops working without anyone noticing.
        """
        if usage.total_tokens == 0:
            return

        cost = Decimal(0)
        for model, _tokens in usage.models.items():
            if not is_priced(model):
                logger.warning(
                    "No price for model; spend will be under-reported",
                    extra={"model": model},
                )

        # Costed per role rather than per model total, because input and output
        # tokens are priced differently and the split matters more than the sum.
        chat_models = [
            model for model in usage.models if not model.startswith("text-embedding")
        ]
        embedding_models = [
            model for model in usage.models if model.startswith("text-embedding")
        ]
        for model in embedding_models:
            cost += estimate_cost_usd(model=model, input_tokens=usage.embedding_tokens)
        for model in chat_models:
            cost += estimate_cost_usd(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )

        try:
            self.usage.add(
                organization_id=organization_id,
                embedding_tokens=usage.embedding_tokens,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                embedding_calls=usage.embedding_calls,
                chat_calls=usage.chat_calls,
                estimated_cost_usd=cost,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.error(
                "Could not record model usage; this spend is not counted",
                exc_info=True,
                extra={
                    "organization_id": str(organization_id),
                    **usage.as_log_fields(),
                },
            )
            return

        logger.info(
            "Model usage recorded",
            extra={
                "organization_id": str(organization_id),
                "estimated_cost_usd": str(cost),
                **usage.as_log_fields(),
            },
        )
