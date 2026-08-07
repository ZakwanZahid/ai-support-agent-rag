"""add a full-text index to document chunks

Vector search matches on meaning, which is what makes it good at paraphrases
and bad at rare literal tokens: an order number, a product code, a price, a
word the embedding model has largely never seen. Those are exactly the terms a
support question is most likely to hinge on.

The column is `GENERATED ALWAYS AS ... STORED`, so Postgres maintains it. A
trigger or an application-side write would be one more thing to forget on an
update path, and the tsvector would silently drift from the content.

`english` rather than `simple`: stemming is the point. It is also a limitation
worth naming — a non-English corpus would need a different configuration, and
that decision belongs with whoever has one.

Revision ID: 20260807_0006
Revises: 20260806_0005
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260807_0006"
down_revision: str | None = "20260806_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED
        """
    )
    # GIN is the right index for tsvector: slower to build than GiST, faster to
    # search, and chunks are written once and read many times.
    op.execute(
        "CREATE INDEX ix_document_chunks_content_tsv "
        "ON document_chunks USING gin (content_tsv)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")
