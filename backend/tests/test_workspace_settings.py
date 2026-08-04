import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import OrganizationMember
from app.models.user import User


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


def create_organization(client: TestClient, token: str) -> dict:
    return client.post(
        "/api/v1/organizations",
        json={"name": "Original Name", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()


def add_member(db: Session, *, organization_id: str, email: str, role: str) -> None:
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


def test_owner_can_rename_workspace(client: TestClient) -> None:
    token = create_user_and_token(client, "rename-owner@example.com")
    organization = create_organization(client, token)

    response = client.patch(
        f"/api/v1/organizations/{organization['id']}",
        json={"name": "  Renamed Workspace  "},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed Workspace"
    # The slug is an identifier and must survive a rename untouched.
    assert body["slug"] == organization["slug"]


def test_rename_rejects_a_blank_name(client: TestClient) -> None:
    token = create_user_and_token(client, "rename-blank@example.com")
    organization = create_organization(client, token)

    response = client.patch(
        f"/api/v1/organizations/{organization['id']}",
        json={"name": "   "},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert client.get(
        f"/api/v1/organizations/{organization['id']}",
        headers=auth_headers(token),
    ).json()["name"] == "Original Name"


def test_plain_member_cannot_rename_workspace(
    client: TestClient,
    db: Session,
) -> None:
    owner_token = create_user_and_token(client, "rename-owner2@example.com")
    organization = create_organization(client, owner_token)

    member_token = create_user_and_token(client, "rename-member@example.com")
    add_member(
        db,
        organization_id=organization["id"],
        email="rename-member@example.com",
        role="member",
    )

    response = client.patch(
        f"/api/v1/organizations/{organization['id']}",
        json={"name": "Member Rename"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403


def test_non_member_cannot_rename_workspace(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "rename-owner3@example.com")
    organization = create_organization(client, owner_token)
    outsider_token = create_user_and_token(client, "rename-outsider@example.com")

    response = client.patch(
        f"/api/v1/organizations/{organization['id']}",
        json={"name": "Outsider Rename"},
        headers=auth_headers(outsider_token),
    )

    # Same response as a missing workspace, so membership is not discoverable.
    assert response.status_code == 404
