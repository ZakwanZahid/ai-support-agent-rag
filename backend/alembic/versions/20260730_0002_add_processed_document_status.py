"""add processed document status

Revision ID: 20260730_0002
Revises: 20260722_0001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260730_0002"
down_revision: str | None = "20260722_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_documents_document_status"),
        "documents",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_documents_document_status"),
        "documents",
        "status IN ('pending', 'processing', 'processed', 'indexed', 'failed')",
    )


def downgrade() -> None:
    op.execute("UPDATE documents SET status = 'pending' WHERE status = 'processed'")
    op.drop_constraint(
        op.f("ck_documents_document_status"),
        "documents",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_documents_document_status"),
        "documents",
        "status IN ('pending', 'processing', 'indexed', 'failed')",
    )
