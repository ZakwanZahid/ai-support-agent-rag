"""add conversation knowledge base

Revision ID: 20260802_0003
Revises: 20260730_0002
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260802_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "knowledge_base_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        op.f("fk_conversations_knowledge_base_id_knowledge_bases"),
        "conversations",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_conversations_knowledge_base_id"),
        "conversations",
        ["knowledge_base_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_conversations_knowledge_base_id"),
        table_name="conversations",
    )
    op.drop_constraint(
        op.f("fk_conversations_knowledge_base_id_knowledge_bases"),
        "conversations",
        type_="foreignkey",
    )
    op.drop_column("conversations", "knowledge_base_id")
