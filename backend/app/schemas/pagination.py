"""Keyset pagination: the page envelope and the cursor it carries.

Offset pagination is the obvious choice and the wrong one for these two
collections. `LIMIT 20 OFFSET 200` asks the database to walk and discard two
hundred rows before returning anything, so the cost of a page grows with how
deep it is. Worse for correctness: both of these lists are actively mutated
while someone reads them. Delete a document while a user is on page two and
every later row shifts up one — they skip a row and never know. Upload one and
they see the same row twice.

A keyset cursor asks a different question: "the rows after this one", where
"this one" is a position in the sort order rather than a count of rows. Pages
stay stable under inserts and deletes, and every page costs the same because
the index seeks straight to the key.

What it gives up is jumping to page seven, and knowing how many pages there
are. Neither list needs either: documents are searched and filtered rather
than paged through, and nobody navigates a chat thread by page number.
"""

import base64
import binascii
import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel


ItemT = TypeVar("ItemT")

# The sort key is (created_at, id). The timestamp alone is not unique — two
# documents uploaded in the same millisecond would make the cursor ambiguous,
# and an ambiguous cursor either repeats a row or skips one.
CursorPosition = tuple[datetime, uuid.UUID]


class InvalidCursorError(ValueError):
    """The cursor is not one we issued, or has been mangled in transit."""


def encode_cursor(created_at: datetime, item_id: uuid.UUID) -> str:
    """Opaque by intent.

    Base64 rather than two plain query parameters, so the shape of the sort
    key stays an implementation detail. Clients that build their own cursors
    become clients that break when the ordering changes.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    raw = f"{created_at.isoformat()}|{item_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> CursorPosition:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding).decode()
        timestamp, _, identifier = raw.partition("|")
        parsed = datetime.fromisoformat(timestamp)
        item_id = uuid.UUID(identifier)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(str(exc)) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, item_id


class Page(BaseModel, Generic[ItemT]):
    """One page of results, plus how to ask for the next.

    `has_more` is a separate field rather than `next_cursor is not None`
    because the two answer different questions once filters are involved, and
    a client should not have to infer one from the other.
    """

    items: list[ItemT]
    next_cursor: str | None = None
    has_more: bool = False
