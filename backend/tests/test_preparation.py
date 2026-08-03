import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    ).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_workspace_with_document(
    client: TestClient,
    token: str,
    *,
    content: bytes = b"Refund requests are accepted within 30 days. " * 40,
    filename: str = "refund-policy.txt",
) -> tuple[str, str]:
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Preparation Org", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()
    knowledge_base = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        json={"name": "Policies"},
        headers=auth_headers(token),
    ).json()
    document = client.post(
        (
            f"/api/v1/organizations/{organization['id']}/knowledge-bases/"
            f"{knowledge_base['id']}/documents/upload"
        ),
        headers=auth_headers(token),
        files={"file": (filename, content, "text/plain")},
    ).json()
    return organization["id"], document["id"]


def test_prepare_takes_document_from_uploaded_to_ready(
    client: TestClient,
    db: Session,
) -> None:
    token = create_user_and_token(client, "prepare-owner@example.com")
    organization_id, document_id = create_workspace_with_document(client, token)

    assert db.get(Document, uuid.UUID(document_id)).status == "pending"

    response = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(token),
    )

    assert response.status_code == 202
    assert response.json()["document_id"] == document_id

    document = db.get(Document, uuid.UUID(document_id))
    db.refresh(document)
    assert document.status == "indexed"

    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(document_id))
    ).all()
    assert chunks
    assert all(chunk.embedding is not None for chunk in chunks)


def test_prepare_rejects_a_document_that_is_already_ready(
    client: TestClient,
    db: Session,
) -> None:
    token = create_user_and_token(client, "prepare-twice@example.com")
    organization_id, document_id = create_workspace_with_document(client, token)

    client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(token),
    )
    repeated = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(token),
    )

    assert repeated.status_code == 409
    assert "force=true" in repeated.json()["detail"]


def test_force_reprepares_a_ready_document(client: TestClient, db: Session) -> None:
    token = create_user_and_token(client, "prepare-force@example.com")
    organization_id, document_id = create_workspace_with_document(client, token)

    client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(token),
    )
    forced = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        params={"force": True},
        headers=auth_headers(token),
    )

    assert forced.status_code == 202
    document = db.get(Document, uuid.UUID(document_id))
    db.refresh(document)
    assert document.status == "indexed"


def test_prepare_leaves_a_failed_document_unindexed(
    client: TestClient,
    db: Session,
) -> None:
    """A document that yields no text must not be reported as ready."""
    token = create_user_and_token(client, "prepare-empty@example.com")
    organization_id, document_id = create_workspace_with_document(
        client,
        token,
        content=b"   \n\t  \n   ",
    )

    response = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(token),
    )

    assert response.status_code == 202
    document = db.get(Document, uuid.UUID(document_id))
    db.refresh(document)
    assert document.status == "failed"
    assert document.error_message


def test_prepare_requires_membership(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "prepare-owner2@example.com")
    organization_id, document_id = create_workspace_with_document(client, owner_token)
    outsider_token = create_user_and_token(client, "prepare-outsider@example.com")

    response = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/prepare",
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 404
