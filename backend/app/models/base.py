import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    metadata = metadata


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Creation and update times, set by the application and by the database.

    Both defaults are present on purpose. `server_default` covers rows written
    outside the ORM — migrations, and anything a maintenance script inserts.
    The Python-side `default` covers ORM inserts, and is what makes
    `created_at` usable as a sort key.

    The distinction is not cosmetic. `func.now()` renders as the backend's own
    timestamp function, and its resolution is the backend's business: Postgres
    gives microseconds, SQLite's `CURRENT_TIMESTAMP` gives whole seconds and
    stores them as text. Whole seconds mean every row written in the same
    second ties, and text storage means a stored `...:32` compares against a
    bound `...:32.000000` as a shorter string rather than as an equal instant.
    Keyset pagination compares exactly that value, so the cursor matched every
    row and pages repeated forever. Setting the value here makes stored and
    compared representations the same one.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        server_default=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

