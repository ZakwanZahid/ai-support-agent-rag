import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.orm import Session

from app.models.usage import OrganizationUsageDay


def today_utc() -> date:
    """The day a cap resets on.

    UTC rather than a local timezone: a per-tenant local midnight means the cap
    resets at a different moment for every tenant, and a tenant that moves
    country gets a free or a short day.
    """
    return datetime.now(timezone.utc).date()


class UsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def tokens_used_today(
        self,
        *,
        organization_id: uuid.UUID,
        on: date | None = None,
    ) -> int:
        row = self.get_day(organization_id=organization_id, on=on)
        return row.total_tokens if row is not None else 0

    def get_day(
        self,
        *,
        organization_id: uuid.UUID,
        on: date | None = None,
    ) -> OrganizationUsageDay | None:
        statement = select(OrganizationUsageDay).where(
            OrganizationUsageDay.organization_id == organization_id,
            OrganizationUsageDay.usage_date == (on or today_utc()),
        )
        return self.db.scalar(statement)

    def list_recent(
        self,
        *,
        organization_id: uuid.UUID,
        days: int = 30,
    ) -> list[OrganizationUsageDay]:
        statement = (
            select(OrganizationUsageDay)
            .where(OrganizationUsageDay.organization_id == organization_id)
            .order_by(OrganizationUsageDay.usage_date.desc())
            .limit(days)
        )
        return list(self.db.scalars(statement).all())

    def add(
        self,
        *,
        organization_id: uuid.UUID,
        embedding_tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        embedding_calls: int = 0,
        chat_calls: int = 0,
        estimated_cost_usd: Decimal = Decimal(0),
        on: date | None = None,
    ) -> None:
        """Accumulate onto today's row, creating it if this is the first spend.

        An upsert that adds to the stored values in SQL, rather than reading
        the row and writing back a sum. Two requests finishing at the same
        moment would both read the same starting figure and one would overwrite
        the other's addition — losing spend, which is the one direction an
        accounting error must not go.
        """
        usage_date = on or today_utc()
        values = {
            "id": uuid.uuid4(),
            "organization_id": organization_id,
            "usage_date": usage_date,
            "embedding_tokens": embedding_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "embedding_calls": embedding_calls,
            "chat_calls": chat_calls,
            "estimated_cost_usd": estimated_cost_usd,
        }

        if self.db.get_bind().dialect.name == "postgresql":
            table = OrganizationUsageDay.__table__
            statement = postgres_insert(table).values(**values)
            self.db.execute(
                statement.on_conflict_do_update(
                    constraint="uq_organization_usage_days_organization_id_usage_date",
                    set_={
                        "embedding_tokens": table.c.embedding_tokens
                        + statement.excluded.embedding_tokens,
                        "prompt_tokens": table.c.prompt_tokens
                        + statement.excluded.prompt_tokens,
                        "completion_tokens": table.c.completion_tokens
                        + statement.excluded.completion_tokens,
                        "embedding_calls": table.c.embedding_calls
                        + statement.excluded.embedding_calls,
                        "chat_calls": table.c.chat_calls
                        + statement.excluded.chat_calls,
                        "estimated_cost_usd": table.c.estimated_cost_usd
                        + statement.excluded.estimated_cost_usd,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )
            )
            return

        # SQLite, for the test suite. Read-modify-write, which is racy in a way
        # the Postgres path is not — acceptable only because the suite is
        # single-threaded and the concurrency this guards against cannot occur.
        existing = self.get_day(organization_id=organization_id, on=usage_date)
        if existing is None:
            self.db.add(OrganizationUsageDay(**values))
            return
        existing.embedding_tokens += embedding_tokens
        existing.prompt_tokens += prompt_tokens
        existing.completion_tokens += completion_tokens
        existing.embedding_calls += embedding_calls
        existing.chat_calls += chat_calls
        existing.estimated_cost_usd = (
            Decimal(existing.estimated_cost_usd) + estimated_cost_usd
        )
