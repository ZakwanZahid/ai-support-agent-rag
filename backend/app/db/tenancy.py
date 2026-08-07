"""Carries the current organization from the request into the database session.

Postgres row-level security decides what a query may see by reading a session
variable, `app.current_organization_id`. Something has to put the right value
there before any tenant query runs, and keep putting it there for the lifetime
of the request.

Two details drive the design:

* The value has to be in place *before* the first query, not merely before the
  tenant queries. A dependency cannot guarantee that, because FastAPI is free
  to resolve another dependency that queries first. A context variable set by
  middleware is in place before any dependency runs at all.

* SQLAlchemy returns the connection to the pool on commit, and a fresh
  connection has none of the previous one's settings. So the scope is applied
  on `after_begin` — every transaction, not once per session — and set with
  `is_local=true` so it dies with its transaction rather than leaking to the
  next request that borrows the same connection.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

SETTING_NAME = "app.current_organization_id"

# Empty string, not None, when unscoped: Postgres session variables are text,
# and the policies turn an empty string back into NULL, which matches no row.
_current_organization: ContextVar[str] = ContextVar("current_organization", default="")


def set_current_organization(organization_id: str | None) -> object:
    """Scope everything that follows to one organization. Returns a reset token."""
    return _current_organization.set(str(organization_id) if organization_id else "")


def reset_current_organization(token: object) -> None:
    _current_organization.reset(token)  # type: ignore[arg-type]


def get_current_organization() -> str:
    return _current_organization.get()


@contextmanager
def organization_scope(organization_id: str | None) -> Iterator[None]:
    """Run a block of work inside one organization's scope.

    Used by background jobs and by the stale-preparation sweep, which have no
    request to inherit a scope from.
    """
    token = set_current_organization(organization_id)
    try:
        yield
    finally:
        reset_current_organization(token)


def warn_if_row_level_security_is_bypassed(engine) -> bool:
    """Say loudly when the connected role makes the policies decorative.

    Superusers and roles with BYPASSRLS ignore row-level security entirely, so
    a deployment that still connects as `postgres` has the policies installed
    and none of the protection. That failure is completely silent — every
    query works, every test that uses the same connection passes — which makes
    it exactly the kind of thing worth a startup log line.

    Returns True when the role is subject to the policies.
    """
    from sqlalchemy import text

    if engine.dialect.name != "postgresql":
        return False

    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT rolsuper, rolbypassrls FROM pg_roles "
                    "WHERE rolname = current_user"
                )
            ).one_or_none()
    except Exception:
        logger.warning("Could not check row-level security status", exc_info=True)
        return False

    if row is None:
        return False

    is_superuser, bypasses = row
    if is_superuser or bypasses:
        logger.warning(
            "Connected as a role that bypasses row-level security; tenant "
            "isolation is enforced by application checks only. Point "
            "DATABASE_URL at the application role and keep the owner for "
            "MIGRATION_DATABASE_URL.",
            extra={"superuser": bool(is_superuser), "bypassrls": bool(bypasses)},
        )
        return False
    return True


@event.listens_for(Session, "after_begin")
def _apply_organization_scope(session: Session, transaction, connection) -> None:
    if connection.dialect.name != "postgresql":
        # SQLite, used by the test suite, has no row-level security and no
        # session variables. Nothing to apply, and nothing enforced either —
        # which is why RLS has its own Postgres-backed tests.
        return

    connection.exec_driver_sql(
        f"SELECT set_config('{SETTING_NAME}', %s, true)",
        (_current_organization.get(),),
    )
