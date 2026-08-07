"""enable row-level security on tenant tables

Every organization-scoped table gets a policy that only admits rows matching
`app.current_organization_id`, the session variable set per transaction from
the request's organization. The application already filters by organization in
every repository; this is the second line of defence, so that a query which
forgets the filter returns nothing rather than another tenant's rows.

Two things are needed before a policy actually restricts anything:

* `FORCE ROW LEVEL SECURITY`, because Postgres exempts a table's owner from
  its own policies otherwise.
* A non-superuser role for the application to connect as. Superusers bypass
  row-level security outright, force or no force, so an application connecting
  as `postgres` would sail straight through every policy below and the whole
  feature would be decoration. This migration therefore creates a dedicated
  login role and grants it data access but no ownership. Migrations keep
  running as the owner via `MIGRATION_DATABASE_URL`.

Identity and membership tables are deliberately left out. `users`,
`organizations` and `organization_members` are what a request consults *to
decide* which organization it is in, so they cannot be gated on that decision
having already been made.

Revision ID: 20260806_0005
Revises: 20260805_0004
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import settings


revision: str = "20260806_0005"
down_revision: str | None = "20260805_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TENANT_TABLES = (
    "knowledge_bases",
    "documents",
    "document_chunks",
    "conversations",
    "messages",
    "message_citations",
)

POLICY_NAME = "tenant_isolation"

# An unset or empty setting becomes NULL, and `organization_id = NULL` is
# never true, so a query with no organization in scope sees nothing at all.
# Failing closed is the point: a missing scope is a bug, and a bug that
# returns no rows is far easier to notice than one that returns everyone's.
PREDICATE = (
    "organization_id = "
    "nullif(current_setting('app.current_organization_id', true), '')::uuid"
)


def _create_application_role() -> None:
    """A login role that policies actually apply to.

    Idempotent, because a migration has to survive being run against a
    database that already has the role — a rebuilt environment, or a rerun
    after a partial failure. The password is synchronised on every run so that
    rotating `APP_DB_PASSWORD` and re-running migrations is enough.
    """
    role = settings.app_db_role
    password = settings.app_db_password.replace("'", "''")

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOBYPASSRLS PASSWORD '{password}';
            ELSE
                ALTER ROLE {role} NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        f"TO {role}"
    )
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}")
    # So tables added by later migrations are reachable without another grant.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {role}"
    )


def upgrade() -> None:
    _create_application_role()

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # One policy for all four commands. WITH CHECK covers INSERT and
        # UPDATE, so a write cannot place a row into another tenant either.
        op.execute(
            f"CREATE POLICY {POLICY_NAME} ON {table} "
            f"USING ({PREDICATE}) WITH CHECK ({PREDICATE})"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # The role is left in place. Dropping it would break any connection still
    # using it, and a downgrade is a schema rollback, not a deprovisioning.
