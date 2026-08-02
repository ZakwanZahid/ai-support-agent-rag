import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_request_chat_provider
from app.llm.provider import ChatProviderError
from app.main import app
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.organization import OrganizationMember
from app.models.user import User
from app.rag.citation_builder import build_citations
from app.rag.context_builder import build_context
from app.repositories.document_chunk_repository import ChunkSearchMatch
from app.services.rag_service import NO_CONTEXT_ANSWER


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    ).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_organization(client: TestClient, token: str, name: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": name,
            "slug": f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_knowledge_base(
    client: TestClient,
    token: str,
    organization_id: str,
) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/knowledge-bases",
        json={"name": f"Support Docs {uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_conversation(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str | None,
) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/conversations",
        json={
            "title": "Refund policy question",
            "knowledge_base_id": knowledge_base_id,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_indexed_document(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
) -> dict:
    upload = client.post(
        (
            f"/api/v1/organizations/{organization_id}/knowledge-bases/"
            f"{knowledge_base_id}/documents/upload"
        ),
        headers=auth_headers(token),
        files={
            "file": (
                "sample-faq.txt",
                b"Customers can request a refund within 14 days of purchase.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201
    document = upload.json()

    ingestion = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document['id']}/ingest",
        headers=auth_headers(token),
    )
    assert ingestion.status_code == 202
    indexing = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document['id']}/index",
        headers=auth_headers(token),
    )
    assert indexing.status_code == 202
    return document


def send_chat(
    client: TestClient,
    token: str,
    organization_id: str,
    conversation_id: str,
    knowledge_base_id: str,
) -> object:
    return client.post(
        (
            f"/api/v1/organizations/{organization_id}/conversations/"
            f"{conversation_id}/messages"
        ),
        json={
            "question": "What is the refund policy?",
            "knowledge_base_id": knowledge_base_id,
            "top_k": 5,
        },
        headers=auth_headers(token),
    )


def add_membership(
    db: Session,
    *,
    organization_id: str,
    email: str,
    role: str = "member",
) -> None:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    db.add(
        OrganizationMember(
            organization_id=uuid.UUID(organization_id),
            user_id=user.id,
            role=role,
        )
    )
    db.commit()


def test_context_builder_caps_context_and_citation_quote() -> None:
    match = ChunkSearchMatch(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="Long policy",
        content="refund policy " * 200,
        distance=0.1,
        chunk_metadata={"chunk_index": 0},
    )

    result = build_context([match], max_chars=300)
    citations = build_citations(result.included_matches)

    assert len(result.context) <= 300
    assert len(result.included_matches) == 1
    assert citations[0].quote in " ".join(result.context.split())
    assert len(citations[0].quote) < len(" ".join(match.content.split()))


def test_chat_requires_authentication(client: TestClient) -> None:
    response = client.post(
        (
            f"/api/v1/organizations/{uuid.uuid4()}/conversations/"
            f"{uuid.uuid4()}/messages"
        ),
        json={
            "question": "What is the refund policy?",
            "knowledge_base_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 401


def test_non_member_cannot_chat_in_organization(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token, "Owner Org")
    knowledge_base = create_knowledge_base(
        client,
        owner_token,
        organization["id"],
    )
    conversation = create_conversation(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )
    outsider_token = create_user_and_token(client, "outsider@example.com")

    response = send_chat(
        client,
        outsider_token,
        organization["id"],
        conversation["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 404


def test_chat_rejects_another_organizations_knowledge_base(
    client: TestClient,
) -> None:
    token = create_user_and_token(client, "owner@example.com")
    first_org = create_organization(client, token, "First Org")
    first_kb = create_knowledge_base(client, token, first_org["id"])
    conversation = create_conversation(
        client,
        token,
        first_org["id"],
        first_kb["id"],
    )
    second_org = create_organization(client, token, "Second Org")
    second_kb = create_knowledge_base(client, token, second_org["id"])

    response = send_chat(
        client,
        token,
        first_org["id"],
        conversation["id"],
        second_kb["id"],
    )

    assert response.status_code == 404


def test_chat_saves_messages_and_returns_stored_citations(
    client: TestClient,
    db: Session,
) -> None:
    token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, token, "Owner Org")
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    document = create_indexed_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )
    conversation = create_conversation(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )

    response = send_chat(
        client,
        token,
        organization["id"],
        conversation["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "Customers can request a refund within 14 days of purchase."
    )
    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_id"] == document["id"]
    assert body["citations"][0]["document_title"] == document["title"]
    assert "refund within 14 days" in body["citations"][0]["quote"]

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == uuid.UUID(conversation["id"]))
        .order_by(Message.created_at, Message.id)
    ).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].organization_id == uuid.UUID(organization["id"])
    assert messages[1].content == body["answer"]

    citations = db.scalars(
        select(MessageCitation).where(
            MessageCitation.message_id == uuid.UUID(
                body["assistant_message_id"]
            )
        )
    ).all()
    assert len(citations) == 1
    assert citations[0].organization_id == uuid.UUID(organization["id"])
    assert citations[0].message_id == messages[1].id
    assert citations[0].document_id == uuid.UUID(document["id"])

    detail = client.get(
        (
            f"/api/v1/organizations/{organization['id']}/conversations/"
            f"{conversation['id']}"
        ),
        headers=auth_headers(token),
    )
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "assistant",
    ]
    assert detail.json()["messages"][1]["citations"] == body["citations"]


def test_chat_returns_safe_answer_when_no_indexed_chunks_exist(
    client: TestClient,
    db: Session,
) -> None:
    token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, token, "Owner Org")
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    conversation = create_conversation(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )

    response = send_chat(
        client,
        token,
        organization["id"],
        conversation["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == NO_CONTEXT_ANSWER
    assert body["citations"] == []
    messages = db.scalars(
        select(Message).where(
            Message.conversation_id == uuid.UUID(conversation["id"])
        )
    ).all()
    assert {message.role for message in messages} == {"user", "assistant"}
    assert db.scalars(select(MessageCitation)).all() == []


def test_llm_failure_keeps_user_message_without_fake_assistant(
    client: TestClient,
    db: Session,
) -> None:
    class FailingChatProvider:
        def generate_answer(
            self,
            system_prompt: str,
            user_prompt: str,
        ) -> str:
            raise ChatProviderError("Test chat provider failed")

    app.dependency_overrides[get_request_chat_provider] = FailingChatProvider
    token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, token, "Owner Org")
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    create_indexed_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )
    conversation = create_conversation(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )

    response = send_chat(
        client,
        token,
        organization["id"],
        conversation["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 502
    messages = db.scalars(
        select(Message).where(
            Message.conversation_id == uuid.UUID(conversation["id"])
        )
    ).all()
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert db.scalars(select(MessageCitation)).all() == []


def test_conversation_list_is_current_user_only_and_admin_can_get_detail(
    client: TestClient,
    db: Session,
) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token, "Owner Org")
    knowledge_base = create_knowledge_base(
        client,
        owner_token,
        organization["id"],
    )
    owner_conversation = create_conversation(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )
    member_token = create_user_and_token(client, "member@example.com")
    add_membership(
        db,
        organization_id=organization["id"],
        email="member@example.com",
    )
    member_conversation = create_conversation(
        client,
        member_token,
        organization["id"],
        knowledge_base["id"],
    )

    listed = client.get(
        f"/api/v1/organizations/{organization['id']}/conversations",
        headers=auth_headers(member_token),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [member_conversation["id"]]

    denied = client.get(
        (
            f"/api/v1/organizations/{organization['id']}/conversations/"
            f"{owner_conversation['id']}"
        ),
        headers=auth_headers(member_token),
    )
    assert denied.status_code == 403

    owner_detail = client.get(
        (
            f"/api/v1/organizations/{organization['id']}/conversations/"
            f"{member_conversation['id']}"
        ),
        headers=auth_headers(owner_token),
    )
    assert owner_detail.status_code == 200
    assert owner_detail.json()["messages"] == []

    stored = db.get(Conversation, uuid.UUID(member_conversation["id"]))
    assert stored is not None
    assert stored.knowledge_base_id == uuid.UUID(knowledge_base["id"])
