import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import OrganizationMember


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


def test_user_can_create_organization(client: TestClient, db: Session) -> None:
    token = create_user_and_token(client, "owner@example.com")

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Example Support", "slug": "example-support"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "example-support"
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(response.json()["id"]),
        )
    )
    assert membership is not None
    assert membership.role == "owner"

    listed = client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert [organization["id"] for organization in listed.json()] == [response.json()["id"]]


def test_user_cannot_access_another_organization(client: TestClient) -> None:
    owner_token = create_user_and_token(client, "owner@example.com")
    outsider_token = create_user_and_token(client, "outsider@example.com")
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Private Support", "slug": "private-support"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    response = client.get(
        f"/api/v1/organizations/{organization['id']}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"
