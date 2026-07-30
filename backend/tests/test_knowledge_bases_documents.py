import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.organization import OrganizationMember
from app.models.user import User


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_organization(client: TestClient, token: str, slug: str = "support-org") -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Support Organization", "slug": slug},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def create_knowledge_base(
    client: TestClient,
    token: str,
    organization_id: str,
    name: str = "Product Docs",
) -> dict:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/knowledge-bases",
        json={"name": name, "description": "Product support documents"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def add_membership(
    db: Session,
    *,
    email: str,
    organization_id: str,
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


def upload_text_document(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
):
    return client.post(
        (
            f"/api/v1/organizations/{organization_id}/knowledge-bases/"
            f"{knowledge_base_id}/documents/upload"
        ),
        headers=auth_headers(token),
        data={"title": "Getting Started"},
        files={"file": ("getting-started.txt", b"Support document body", "text/plain")},
    )


def test_owner_and_admin_can_create_knowledge_bases(
    client: TestClient,
    db: Session,
) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    owner_knowledge_base = create_knowledge_base(
        client,
        owner_token,
        organization["id"],
        "Owner Docs",
    )

    admin_token = create_user_and_token(client, "admin@example.com")
    add_membership(
        db,
        email="admin@example.com",
        organization_id=organization["id"],
        role="admin",
    )
    admin_knowledge_base = create_knowledge_base(
        client,
        admin_token,
        organization["id"],
        "Admin Docs",
    )

    assert owner_knowledge_base["organization_id"] == organization["id"]
    assert admin_knowledge_base["organization_id"] == organization["id"]


def test_member_can_list_knowledge_bases(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    member_token = create_user_and_token(client, "member@example.com")
    add_membership(
        db,
        email="member@example.com",
        organization_id=organization["id"],
        role="member",
    )

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [knowledge_base["id"]]


def test_member_cannot_upload_document(client: TestClient, db: Session) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    member_token = create_user_and_token(client, "member@example.com")
    add_membership(
        db,
        email="member@example.com",
        organization_id=organization["id"],
        role="member",
    )

    response = upload_text_document(
        client,
        member_token,
        organization["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 403


def test_upload_creates_pending_document_and_file(
    client: TestClient,
    db: Session,
) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])

    response = upload_text_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["source_type"] == "upload"
    assert payload["file_name"] == "getting-started.txt"
    assert Path(payload["file_path"]).exists()

    document = db.get(Document, uuid.UUID(payload["id"]))
    assert document is not None
    assert document.status == "pending"
    assert document.organization_id == uuid.UUID(organization["id"])


def test_user_cannot_access_another_organizations_documents(
    client: TestClient,
) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, owner_token)
    knowledge_base = create_knowledge_base(client, owner_token, organization["id"])
    document = upload_text_document(
        client,
        owner_token,
        organization["id"],
        knowledge_base["id"],
    ).json()
    outsider_token = create_user_and_token(client, "outsider@example.com")

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/documents/{document['id']}",
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"
