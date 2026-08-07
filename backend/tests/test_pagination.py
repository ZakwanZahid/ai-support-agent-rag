"""Keyset pagination, server-side search, and the ways both go wrong.

The interesting cases are not "page one has twenty rows". They are what
happens when the collection changes underneath a reader, and what a cursor
does when it is stale, forged, or points at a row that has been deleted —
which is exactly where offset pagination quietly misbehaves.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.pagination import decode_cursor, encode_cursor
from tests.test_knowledge_bases_documents import (
    auth_headers,
    create_knowledge_base,
    create_organization,
    create_user_and_token,
    upload_text_document,
)


def seed_documents(
    client: TestClient,
    db: Session,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
    titles: list[str],
    status: str = "pending",
) -> list[str]:
    """Upload documents in order, oldest first, and return their ids."""
    ids = []
    for title in titles:
        response = upload_text_document(
            client,
            token,
            organization_id,
            knowledge_base_id,
        )
        assert response.status_code == 201
        document_id = response.json()["id"]
        stored = db.get(Document, uuid.UUID(document_id))
        stored.title = title
        stored.status = status
        db.commit()
        ids.append(document_id)
    return ids


def fetch(client: TestClient, token: str, organization_id: str, **params):
    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents",
        headers=auth_headers(token),
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


def workspace(client: TestClient) -> tuple[str, dict, dict]:
    token = create_user_and_token(client, f"pager-{uuid.uuid4().hex[:8]}@example.com")
    organization = create_organization(client, token, slug=f"org-{uuid.uuid4().hex[:8]}")
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    return token, organization, knowledge_base


def test_a_cursor_round_trips():
    from datetime import datetime, timezone

    moment = datetime(2026, 8, 7, 12, 30, tzinfo=timezone.utc)
    identifier = uuid.uuid4()

    assert decode_cursor(encode_cursor(moment, identifier)) == (moment, identifier)


def test_a_naive_timestamp_is_read_back_as_utc():
    """SQLite hands back naive datetimes where Postgres hands back aware ones.

    A cursor that lost its timezone on one backend and kept it on the other
    would compare against a different instant, which is the kind of bug that
    only shows up in production.
    """
    from datetime import datetime, timezone

    moment = datetime(2026, 8, 7, 12, 30)
    decoded, _ = decode_cursor(encode_cursor(moment, uuid.uuid4()))

    assert decoded == moment.replace(tzinfo=timezone.utc)


def test_a_forged_cursor_is_rejected_rather_than_ignored(client: TestClient):
    token, organization, _ = workspace(client)

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/documents",
        headers=auth_headers(token),
        params={"cursor": "not-a-real-cursor"},
    )

    # Rejected, not silently treated as page one: a client that thinks it is
    # paging and is actually restarting would loop forever.
    assert response.status_code == 422


def test_pages_cover_the_collection_exactly_once(
    client: TestClient,
    db: Session,
):
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        [f"Doc {index}" for index in range(7)],
    )

    seen: list[str] = []
    cursor = None
    for _ in range(10):
        page = fetch(
            client,
            token,
            organization["id"],
            limit=3,
            **({"cursor": cursor} if cursor else {}),
        )
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if not page["has_more"]:
            break

    assert len(seen) == 7
    assert len(set(seen)) == 7, "a document appeared on two pages"


def test_the_last_page_reports_no_more(client: TestClient, db: Session):
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Only one"],
    )

    page = fetch(client, token, organization["id"], limit=10)

    assert page["has_more"] is False
    assert page["next_cursor"] is None


def test_deleting_a_row_does_not_make_the_reader_skip_one(
    client: TestClient,
    db: Session,
):
    """The failure offset pagination has and keyset does not.

    With OFFSET, deleting a row from page one shifts everything up, and the
    reader's next request skips whatever moved across the boundary. The cursor
    names a position in the sort order instead of a count, so the row after it
    is still the row after it.
    """
    token, organization, knowledge_base = workspace(client)
    ids = seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        [f"Doc {index}" for index in range(6)],
    )

    first = fetch(client, token, organization["id"], limit=3)
    seen = [item["id"] for item in first["items"]]

    # Delete one of the rows the reader has already passed.
    deleted = client.delete(
        f"/api/v1/organizations/{organization['id']}/documents/{seen[0]}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 204

    second = fetch(
        client,
        token,
        organization["id"],
        limit=3,
        cursor=first["next_cursor"],
    )
    seen.extend(item["id"] for item in second["items"])

    remaining = [document_id for document_id in ids if document_id != seen[0]]
    assert set(seen[1:]) == set(remaining)


def test_search_runs_in_the_query_not_the_browser(client: TestClient, db: Session):
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Refund policy", "Shipping terms", "Refunds FAQ"],
    )

    page = fetch(client, token, organization["id"], q="refund")

    titles = sorted(item["title"] for item in page["items"])
    assert titles == ["Refund policy", "Refunds FAQ"]


def test_search_treats_wildcards_as_literal_characters(
    client: TestClient,
    db: Session,
):
    """A title with `%` in it should be searchable, not a match-everything query."""
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["100% guarantee", "Shipping terms"],
    )

    page = fetch(client, token, organization["id"], q="100%")

    assert [item["title"] for item in page["items"]] == ["100% guarantee"]


def test_status_filter_accepts_several_statuses(client: TestClient, db: Session):
    """The UI's "Processing" chip covers more than one API status.

    Sending them as repeated parameters keeps the mapping in the frontend's
    vocabulary module, where the rest of the product's language already lives.
    """
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Being read"],
        status="processing",
    )
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Text extracted"],
        status="processed",
    )
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["All done"],
        status="indexed",
    )

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/documents",
        headers=auth_headers(token),
        params=[("status", "processing"), ("status", "processed")],
    )

    titles = sorted(item["title"] for item in response.json()["items"])
    assert titles == ["Being read", "Text extracted"]


def test_status_counts_describe_the_search_not_the_selected_status(
    client: TestClient,
    db: Session,
):
    """Counts sit on the filter controls, so they must survive being filtered.

    If they only ever counted the status already selected, every chip would
    read the same number and none of them would help.
    """
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Refund policy", "Refunds FAQ"],
        status="indexed",
    )
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Refund draft"],
        status="failed",
    )
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Shipping terms"],
        status="indexed",
    )

    page = fetch(client, token, organization["id"], q="refund", status="failed")

    assert [item["title"] for item in page["items"]] == ["Refund draft"]
    # Scoped to the search, but not to the status filter.
    assert page["status_counts"] == {"indexed": 2, "failed": 1}


def test_documents_stay_scoped_to_their_workspace(client: TestClient, db: Session):
    token, organization, knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        token,
        organization["id"],
        knowledge_base["id"],
        ["Ours"],
    )
    other_token, other_organization, other_knowledge_base = workspace(client)
    seed_documents(
        client,
        db,
        other_token,
        other_organization["id"],
        other_knowledge_base["id"],
        ["Theirs"],
    )

    page = fetch(client, other_token, other_organization["id"])

    assert [item["title"] for item in page["items"]] == ["Theirs"]


def make_conversation_with_messages(
    client: TestClient,
    db: Session,
    count: int,
) -> tuple[str, str, str]:
    """A thread with `count` messages, oldest first."""
    from app.models.conversation import Conversation
    from app.repositories.message_repository import MessageRepository

    token, organization, knowledge_base = workspace(client)
    created = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Refunds"},
        headers=auth_headers(token),
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    messages = MessageRepository(db)
    for index in range(count):
        messages.create(
            organization_id=uuid.UUID(organization["id"]),
            conversation_id=uuid.UUID(conversation_id),
            role="user" if index % 2 == 0 else "assistant",
            content=f"Message {index}",
        )
    db.commit()
    return token, organization["id"], conversation_id


def test_opening_a_thread_returns_its_newest_messages(
    client: TestClient,
    db: Session,
):
    """A thread opens at the end, the way a conversation is read."""
    token, organization_id, conversation_id = make_conversation_with_messages(
        client,
        db,
        count=12,
    )

    detail = client.get(
        f"/api/v1/organizations/{organization_id}/conversations/{conversation_id}",
        headers=auth_headers(token),
        params={"message_limit": 5},
    )

    body = detail.json()
    contents = [message["content"] for message in body["messages"]]
    assert contents == [f"Message {index}" for index in range(7, 12)]
    assert body["has_more_messages"] is True
    assert body["next_message_cursor"]


def test_earlier_messages_page_backwards_without_gaps(
    client: TestClient,
    db: Session,
):
    token, organization_id, conversation_id = make_conversation_with_messages(
        client,
        db,
        count=12,
    )
    detail = client.get(
        f"/api/v1/organizations/{organization_id}/conversations/{conversation_id}",
        headers=auth_headers(token),
        params={"message_limit": 5},
    ).json()

    earlier = client.get(
        f"/api/v1/organizations/{organization_id}"
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers(token),
        params={"limit": 5, "cursor": detail["next_message_cursor"]},
    ).json()

    assert [message["content"] for message in earlier["items"]] == [
        f"Message {index}" for index in range(2, 7)
    ]
    assert earlier["has_more"] is True

    oldest = client.get(
        f"/api/v1/organizations/{organization_id}"
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers(token),
        params={"limit": 5, "cursor": earlier["next_cursor"]},
    ).json()

    assert [message["content"] for message in oldest["items"]] == [
        "Message 0",
        "Message 1",
    ]
    assert oldest["has_more"] is False


def test_a_short_thread_reports_nothing_earlier(client: TestClient, db: Session):
    token, organization_id, conversation_id = make_conversation_with_messages(
        client,
        db,
        count=3,
    )

    detail = client.get(
        f"/api/v1/organizations/{organization_id}/conversations/{conversation_id}",
        headers=auth_headers(token),
    ).json()

    assert len(detail["messages"]) == 3
    assert detail["has_more_messages"] is False
    assert detail["next_message_cursor"] is None


def test_another_members_thread_stays_private(client: TestClient, db: Session):
    _token, organization_id, conversation_id = make_conversation_with_messages(
        client,
        db,
        count=2,
    )
    outsider = create_user_and_token(client, f"out-{uuid.uuid4().hex[:8]}@example.com")

    response = client.get(
        f"/api/v1/organizations/{organization_id}"
        f"/conversations/{conversation_id}/messages",
        headers=auth_headers(outsider),
    )

    # Not a member of that workspace at all, so the workspace itself is the
    # thing that does not exist.
    assert response.status_code == 404
