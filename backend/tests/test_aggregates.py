import uuid

from fastapi.testclient import TestClient


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    ).status_code == 201
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_base_list_reports_document_counts(client: TestClient) -> None:
    token = create_user_and_token(client, "counts@example.com")
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Counts Org", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()
    knowledge_base = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        json={"name": "Policies"},
        headers=auth_headers(token),
    ).json()

    # A brand new knowledge base reports zeroes rather than omitting the field.
    assert knowledge_base["document_count"] == 0
    assert knowledge_base["ready_document_count"] == 0

    upload_url = (
        f"/api/v1/organizations/{organization['id']}/knowledge-bases/"
        f"{knowledge_base['id']}/documents/upload"
    )
    for index in range(2):
        client.post(
            upload_url,
            headers=auth_headers(token),
            files={
                "file": (
                    f"policy-{index}.txt",
                    b"Refunds are accepted within 30 days. " * 30,
                    "text/plain",
                )
            },
        )

    listed = client.get(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        headers=auth_headers(token),
    ).json()
    assert listed[0]["document_count"] == 2
    assert listed[0]["ready_document_count"] == 0

    # Preparing one document moves it, and only it, into the ready count.
    documents = client.get(
        f"/api/v1/organizations/{organization['id']}/documents",
        headers=auth_headers(token),
    ).json()
    client.post(
        f"/api/v1/organizations/{organization['id']}/documents/{documents[0]['id']}/prepare",
        headers=auth_headers(token),
    )

    listed = client.get(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        headers=auth_headers(token),
    ).json()
    assert listed[0]["document_count"] == 2
    assert listed[0]["ready_document_count"] == 1


def test_conversation_list_reports_message_count_and_preview(
    client: TestClient,
) -> None:
    token = create_user_and_token(client, "previews@example.com")
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Preview Org", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()
    knowledge_base = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        json={"name": "Policies"},
        headers=auth_headers(token),
    ).json()
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"title": "Refunds", "knowledge_base_id": knowledge_base["id"]},
        headers=auth_headers(token),
    ).json()

    empty = client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
        headers=auth_headers(token),
    ).json()
    assert empty[0]["message_count"] == 0
    assert empty[0]["last_message_preview"] is None

    client.post(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
        json={
            "question": "What is the refund window?",
            "knowledge_base_id": knowledge_base["id"],
        },
        headers=auth_headers(token),
    )

    listed = client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
        headers=auth_headers(token),
    ).json()
    # One question plus one answer.
    assert listed[0]["message_count"] == 2

    # The preview is the most recent message, which is the assistant's reply.
    # Its wording depends on the model, so compare against the stored thread
    # rather than asserting particular text.
    detail = client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        headers=auth_headers(token),
    ).json()
    assert detail["messages"][-1]["role"] == "assistant"
    assert listed[0]["last_message_preview"] == detail["messages"][-1]["content"]


def test_messages_keep_question_before_answer(client: TestClient) -> None:
    """Ordering must not depend on clock resolution.

    A question and its answer are written close enough together to land on the
    same timestamp, and the primary key tiebreak is a random UUID, so without
    explicit sequencing the answer can sort above the question.
    """
    token = create_user_and_token(client, "ordering@example.com")
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Ordering Org", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()
    knowledge_base = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        json={"name": "Policies"},
        headers=auth_headers(token),
    ).json()
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"]},
        headers=auth_headers(token),
    ).json()

    for question in ("First question?", "Second question?"):
        client.post(
            f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}/messages",
            json={
                "question": question,
                "knowledge_base_id": knowledge_base["id"],
            },
            headers=auth_headers(token),
        )

    messages = client.get(
        f"/api/v1/organizations/{organization['id']}/conversations/{conversation['id']}",
        headers=auth_headers(token),
    ).json()["messages"]

    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[0]["content"] == "First question?"
    assert messages[2]["content"] == "Second question?"

    timestamps = [message["created_at"] for message in messages]
    assert timestamps == sorted(timestamps)
    assert len(set(timestamps)) == len(timestamps)


def test_long_message_preview_is_truncated(client: TestClient) -> None:
    from app.schemas.conversation import MESSAGE_PREVIEW_MAX_CHARS
    from app.services.conversation_service import _preview

    assert _preview(None) is None
    assert _preview("  hello   there \n world ") == "hello there world"

    long_preview = _preview("word " * 200)
    assert long_preview is not None
    assert long_preview.endswith("…")
    assert len(long_preview) <= MESSAGE_PREVIEW_MAX_CHARS + 1
