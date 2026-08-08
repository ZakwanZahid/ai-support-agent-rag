import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationUsageDay(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One organization's model spend for one UTC day.

    A rolled-up row per day rather than a row per call. A ledger of individual
    calls answers more questions, and costs a write on the hottest path in the
    application to answer questions nobody is currently asking. The daily
    grain is what the cap is enforced against, so it is the grain stored.

    In Postgres, not Redis. The rate limiter counts bursts and may fail open
    (ADR-037); this counts money, and a spending record that evaporates when a
    cache restarts is not a spending record. It is also the row an invoice
    dispute would be settled from.
    """

    __tablename__ = "organization_usage_days"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "usage_date",
            name="uq_organization_usage_days_organization_id_usage_date",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # UTC, and named so nobody has to guess. A cap that resets at local
    # midnight resets at a different moment for every tenant.
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)

    embedding_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chat_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Stored as a fixed-point number rather than a float: it is money, and it
    # is summed. Six decimal places because a single small call costs less
    # than a hundredth of a cent.
    estimated_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 6),
        default=0,
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship()  # noqa: F821

    @property
    def total_tokens(self) -> int:
        return self.embedding_tokens + self.prompt_tokens + self.completion_tokens
