import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.organization import OrganizationMember
from app.models.user import User


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
        json={"name": "Search Docs"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_processed_document(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
    *,
    filename: str,
    content: str,
) -> dict:
    upload = client.post(
        (
            f"/api/v1/organizations/{organization_id}/knowledge-bases/"
            f"{knowledge_base_id}/documents/upload"
        ),
        headers=auth_headers(token),
        files={"file": (filename, content.encode(), "text/plain")},
    )
    assert upload.status_code == 201
    document = upload.json()
    ingestion = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document['id']}/ingest",
        headers=auth_headers(token),
    )
    assert ingestion.status_code == 202
    return document


def trigger_indexing(
    client: TestClient,
    token: str,
    organization_id: str,
    document_id: str,
    *,
    force: bool = False,
) -> int:
    suffix = "?force=true" if force else ""
    response = client.post(
        (
            f"/api/v1/organizations/{organization_id}/documents/"
            f"{document_id}/index{suffix}"
        ),
        headers=auth_headers(token),
    )
    return response.status_code


def add_membership(
    db: Session,
    *,
    organization_id: str,
    email: str,
    role: str,
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


def test_indexing_requires_authentication(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/organizations/{uuid.uuid4()}/documents/{uuid.uuid4()}/index"
    )

    assert response.status_code == 401


def test_non_member_cannot_index(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token, "Owner Org")
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = create_processed_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
        filename="refund.txt",
        content="Refunds are available within thirty days.",
    )
    outsider_token = create_user_and_token(client, "outsider@example.com")

    status_code = trigger_indexing(
        client,
        outsider_token,
        organization["id"],
        document["id"],
    )

    assert status_code == 404


def test_member_cannot_index(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token, "Owner Org")
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = create_processed_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
        filename="refund.txt",
        content="Refunds are available within thirty days.",
    )
    member_token = create_user_and_token(client, "member@example.com")
    add_membership(
        db,
        organization_id=organization["id"],
        email="member@example.com",
        role="member",
    )

    status_code = trigger_indexing(
        client,
        member_token,
        organization["id"],
        document["id"],
    )

    assert status_code == 403


def test_owner_and_admin_can_index_processed_documents(
    client: TestClient,
    db: Session,
) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token, "Owner Org")
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    owner_document = create_processed_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
        filename="refund.txt",
        content="Refunds are available within thirty days.",
    )

    assert trigger_indexing(
        client,
        owner_token,
        organization["id"],
        owner_document["id"],
    ) == 202

    admin_token = create_user_and_token(client, "admin@example.com")
    add_membership(
        db,
        organization_id=organization["id"],
        email="admin@example.com",
        role="admin",
    )
    admin_document = create_processed_document(
        client,
        admin_token,
        organization["id"],
        knowledge_base["id"],
        filename="shipping.txt",
        content="Shipping normally takes three business days.",
    )
    assert trigger_indexing(
        client,
        admin_token,
        organization["id"],
        admin_document["id"],
    ) == 202

    db.expire_all()
    stored_document = db.get(Document, uuid.UUID(owner_document["id"]))
    assert stored_document is not None
    assert stored_document.status == "indexed"
    chunks = db.scalars(
        select(DocumentChunk).where(
            DocumentChunk.document_id == stored_document.id
        )
    ).all()
    assert chunks
    assert all(
        chunk.embedding is not None and len(chunk.embedding) == 1536
        for chunk in chunks
    )
    assert trigger_indexing(
        client,
        owner_token,
        organization["id"],
        owner_document["id"],
    ) == 409
    assert trigger_indexing(
        client,
        owner_token,
        organization["id"],
        owner_document["id"],
        force=True,
    ) == 202


def test_search_requires_authentication(client: TestClient) -> None:
    response = client.post(
        (
            f"/api/v1/organizations/{uuid.uuid4()}/knowledge-bases/"
            f"{uuid.uuid4()}/search"
        ),
        json={"query": "refund policy", "top_k": 5},
    )

    assert response.status_code == 401


def test_search_is_tenant_scoped_and_honors_top_k(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    first_org = create_organization(client, owner_token, "First Org")
    first_kb = create_knowledge_base(client, owner_token, first_org["id"])
    refund_document = create_processed_document(
        client,
        owner_token,
        first_org["id"],
        first_kb["id"],
        filename="refund.txt",
        content="The refund policy allows returns within thirty days.",
    )
    shipping_document = create_processed_document(
        client,
        owner_token,
        first_org["id"],
        first_kb["id"],
        filename="shipping.txt",
        content="Shipping generally takes three business days.",
    )
    assert trigger_indexing(
        client, owner_token, first_org["id"], refund_document["id"]
    ) == 202
    assert trigger_indexing(
        client, owner_token, first_org["id"], shipping_document["id"]
    ) == 202

    second_org = create_organization(client, owner_token, "Second Org")
    second_kb = create_knowledge_base(client, owner_token, second_org["id"])
    private_document = create_processed_document(
        client,
        owner_token,
        second_org["id"],
        second_kb["id"],
        filename="private-refund.txt",
        content="Private refund instructions from another tenant.",
    )
    assert trigger_indexing(
        client, owner_token, second_org["id"], private_document["id"]
    ) == 202

    response = client.post(
        (
            f"/api/v1/organizations/{first_org['id']}/knowledge-bases/"
            f"{first_kb['id']}/search"
        ),
        json={"query": "What is the refund policy?", "top_k": 1},
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["document_id"] == refund_document["id"]
    assert results[0]["document_id"] != private_document["id"]
