"""add document preparation job tracking

Adds the columns the queue needs to make preparation recoverable: which job
currently owns a document, when that attempt began, and how many attempts have
been made. `preparation_started_at` is what lets a sweep tell a document that
is genuinely working from one whose worker died mid-job.

Revision ID: 20260805_0004
Revises: 20260802_0003
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260805_0004"
down_revision: str | None = "20260802_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("preparation_job_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "preparation_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "preparation_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # The sweep queries documents that are processing and started long ago, so
    # the index is on both columns rather than either alone.
    op.create_index(
        "ix_documents_preparation_sweep",
        "documents",
        ["status", "preparation_started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_preparation_sweep", table_name="documents")
    op.drop_column("documents", "preparation_attempts")
    op.drop_column("documents", "preparation_started_at")
    op.drop_column("documents", "preparation_job_id")
