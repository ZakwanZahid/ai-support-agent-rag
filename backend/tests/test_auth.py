from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


REGISTER_DATA = {
    "email": "user@example.com",
    "password": "strongpassword",
    "full_name": "User Name",
}


def register(client: TestClient, **overrides: str):
    return client.post("/api/v1/auth/register", json=REGISTER_DATA | overrides)


def login(client: TestClient, **overrides: str):
    credentials = {
        "email": REGISTER_DATA["email"],
        "password": REGISTER_DATA["password"],
    }
    return client.post("/api/v1/auth/login", json=credentials | overrides)


def test_user_can_register(client: TestClient) -> None:
    response = register(client)

    assert response.status_code == 201
    assert response.json()["email"] == REGISTER_DATA["email"]
    assert response.json()["full_name"] == REGISTER_DATA["full_name"]
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_password_is_hashed(client: TestClient, db: Session) -> None:
    register(client)

    user = db.scalar(select(User).where(User.email == REGISTER_DATA["email"]))

    assert user is not None
    assert user.password_hash != REGISTER_DATA["password"]
    assert verify_password(REGISTER_DATA["password"], user.password_hash)


def test_duplicate_email_fails(client: TestClient) -> None:
    register(client)

    response = register(client, email="USER@example.com")

    assert response.status_code == 409


def test_user_can_login(client: TestClient) -> None:
    register(client)

    response = login(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_wrong_password_fails(client: TestClient) -> None:
    register(client)

    response = login(client, password="wrongpassword")

    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_DATA["email"]
