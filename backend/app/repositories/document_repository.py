import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import (
    case,
    delete as sa_delete,
    func,
    literal,
    select,
    tuple_,
)
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.pagination import CursorPosition


@dataclass(frozen=True)
class DocumentCounts:
    total: int
    ready: int


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_upload(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        title: str,
        file_name: str,
        file_path: str,
        mime_type: str,
    ) -> Document:
        document = Document(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
            source_type="upload",
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
            status="pending",
        )
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_id(
        self,
        *,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        return self.db.scalar(statement)

    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> list[Document]:
        statement = self._filtered(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        ).order_by(Document.created_at.desc(), Document.id.desc())
        return list(self.db.scalars(statement).all())

    def _filtered(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
        search: str | None = None,
        statuses: Sequence[str] | None = None,
    ):
        """The `where` clause every document query shares.

        Kept in one place so the page query and the counts beside it can never
        disagree about what the user is looking at — a filter applied to the
        rows but not the counts is how a list ends up showing "7 ready" above
        four rows.
        """
        statement = select(Document).where(Document.organization_id == organization_id)
        if knowledge_base_id is not None:
            statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        if statuses:
            statement = statement.where(Document.status.in_(list(statuses)))
        if search:
            # Escaped so that a title containing % or _ searches for those
            # characters rather than turning into a wildcard.
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                Document.title.ilike(f"%{escaped}%", escape="\\")
            )
        return statement

    def list_page(
        self,
        *,
        organization_id: uuid.UUID,
        limit: int,
        knowledge_base_id: uuid.UUID | None = None,
        search: str | None = None,
        statuses: Sequence[str] | None = None,
        after: CursorPosition | None = None,
    ) -> tuple[list[Document], bool]:
        """One page of documents, newest first, plus whether more remain.

        Fetches `limit + 1` rows and returns at most `limit`. Asking for one
        extra is how you learn there is a next page without a second COUNT
        query over the whole filtered set.
        """
        statement = self._filtered(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            search=search,
            statuses=statuses,
        )
        if after is not None:
            created_at, document_id = after
            # Strictly after the cursor in (created_at DESC, id DESC) order.
            # The row comparison is what makes ties deterministic; comparing
            # created_at alone would drop rows sharing a timestamp.
            statement = statement.where(
                tuple_(Document.created_at, Document.id)
                < tuple_(literal(created_at), literal(document_id))
            )
        statement = statement.order_by(
            Document.created_at.desc(), Document.id.desc()
        ).limit(limit + 1)

        rows = list(self.db.scalars(statement).all())
        return rows[:limit], len(rows) > limit

    def status_counts(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> dict[str, int]:
        """How many documents each status holds under the current search.

        Deliberately ignores the status filter: these numbers sit on the
        filter controls themselves, and a count that only ever described the
        status already selected would read the same on every tab.
        """
        filtered = self._filtered(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            search=search,
        ).subquery()
        statement = select(filtered.c.status, func.count()).group_by(filtered.c.status)
        return {status: count for status, count in self.db.execute(statement).all()}

    def delete(self, document: Document) -> None:
        """Remove one document row, letting the database cascade the rest.

        A Core DELETE rather than `session.delete`, deliberately. The ORM
        would load every chunk and citation in order to null their foreign
        keys — which are `NOT NULL`, so it fails — and it would do it one
        collection at a time. The `ON DELETE CASCADE` already declared on
        those columns is both correct and a single statement.
        """
        self.db.execute(
            sa_delete(Document).where(Document.id == document.id),
            execution_options={"synchronize_session": False},
        )
        self.db.expire_all()

    def file_paths_for_knowledge_base(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> list[str]:
        """Stored paths of the uploads about to be orphaned.

        Read before the rows are deleted, because afterwards there is nothing
        left to say which files belonged to them.
        """
        statement = select(Document.file_path).where(
            Document.organization_id == organization_id,
            Document.file_path.is_not(None),
        )
        if knowledge_base_id is not None:
            statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        return [path for path in self.db.scalars(statement).all() if path]

    def count_preparing(
        self,
        *,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
    ) -> int:
        """How many documents a worker may currently be part-way through."""
        statement = select(func.count(Document.id)).where(
            Document.organization_id == organization_id,
            Document.status == "processing",
        )
        if knowledge_base_id is not None:
            statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        return self.db.scalar(statement) or 0

    def counts_by_knowledge_base(
        self,
        organization_id: uuid.UUID,
    ) -> dict[uuid.UUID, DocumentCounts]:
        """Total and ready document counts per knowledge base, in one query.

        Keeps the knowledge base list endpoint from issuing a count per row.
        Knowledge bases with no documents are absent from the result; callers
        treat a missing key as zero.
        """
        statement = (
            select(
                Document.knowledge_base_id,
                func.count(Document.id),
                # count() ignores NULLs, so the CASE yields only indexed rows.
                func.count(case((Document.status == "indexed", 1))),
            )
            .where(Document.organization_id == organization_id)
            .group_by(Document.knowledge_base_id)
        )
        return {
            knowledge_base_id: DocumentCounts(total=total, ready=ready)
            for knowledge_base_id, total, ready in self.db.execute(statement).all()
        }
