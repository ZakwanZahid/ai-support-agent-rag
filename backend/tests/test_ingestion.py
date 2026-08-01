import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
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


def create_organization(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Ingestion Organization", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_knowledge_base(client: TestClient, token: str, organization_id: str) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/knowledge-bases",
        json={"name": "Ingestion Docs"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def upload_document(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
    *,
    filename: str = "guide.txt",
    content: bytes = b"A useful support guide. " * 100,
    mime_type: str = "text/plain",
) -> dict:
    response = client.post(
        (
            f"/api/v1/organizations/{organization_id}/knowledge-bases/"
            f"{knowledge_base_id}/documents/upload"
        ),
        headers=auth_headers(token),
        files={"file": (filename, content, mime_type)},
    )
    assert response.status_code == 201
    return response.json()


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


def ingestion_url(organization_id: str, document_id: str, *, force: bool = False) -> str:
    url = f"/api/v1/organizations/{organization_id}/documents/{document_id}/ingest"
    return f"{url}?force=true" if force else url


def test_ingestion_requires_authentication(client: TestClient) -> None:
    response = client.post(ingestion_url(str(uuid.uuid4()), str(uuid.uuid4())))

    assert response.status_code == 401


def test_non_member_cannot_ingest_document(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )
    outsider_token = create_user_and_token(client, "outsider@example.com")

    response = client.post(
        ingestion_url(organization["id"], document["id"]),
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 404


def test_member_cannot_ingest_document(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
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
        role="member",
    )

    response = client.post(
        ingestion_url(organization["id"], document["id"]),
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403


def test_owner_can_ingest_and_create_chunks(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )

    response = client.post(
        ingestion_url(organization["id"], document["id"]),
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 202
    db.expire_all()
    stored_document = db.get(Document, uuid.UUID(document["id"]))
    assert stored_document is not None
    assert stored_document.status == "processed"
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == stored_document.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    assert len(chunks) >= 2
    assert chunks[0].embedding is None
    assert chunks[0].chunk_metadata["char_start"] == 0


def test_upload_can_schedule_automatic_ingestion(
    client: TestClient,
    db: Session,
) -> None:
    settings.auto_ingest_on_upload = True
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])

    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )

    db.expire_all()
    stored_document = db.get(Document, uuid.UUID(document["id"]))
    assert stored_document is not None
    assert stored_document.status == "processed"


def test_admin_can_trigger_ingestion(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )
    admin_token = create_user_and_token(client, "admin@example.com")
    add_membership(
        db,
        organization_id=organization["id"],
        email="admin@example.com",
        role="admin",
    )

    response = client.post(
        ingestion_url(organization["id"], document["id"]),
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 202


def test_force_replaces_chunks_without_duplicates(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )
    url = ingestion_url(organization["id"], document["id"])

    assert client.post(url, headers=auth_headers(owner_token)).status_code == 202
    duplicate = client.post(url, headers=auth_headers(owner_token))
    assert duplicate.status_code == 409

    db.expire_all()
    before = db.scalar(
        select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == uuid.UUID(document["id"])
        )
    )
    forced = client.post(
        ingestion_url(organization["id"], document["id"], force=True),
        headers=auth_headers(owner_token),
    )
    assert forced.status_code == 202
    db.expire_all()
    after = db.scalar(
        select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == uuid.UUID(document["id"])
        )
    )
    assert after == before


def test_failed_extraction_sets_failed_status(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
        filename="broken.pdf",
        content=b"this is not a valid PDF",
        mime_type="application/pdf",
    )

    response = client.post(
        ingestion_url(organization["id"], document["id"]),
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 202
    db.expire_all()
    stored_document = db.get(Document, uuid.UUID(document["id"]))
    assert stored_document is not None
    assert stored_document.status == "failed"
    assert stored_document.error_message
