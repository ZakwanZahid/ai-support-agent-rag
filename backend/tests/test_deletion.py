"""Deleting documents, knowledge spaces and workspaces.

Two things each test is really checking: that the rows underneath go too, and
that the uploaded file on disk goes with them. The database cascades do the
first — SQLite enforces them here because conftest turns the pragma on — and
the service does the second, after the commit.
"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import resolve_storage_path
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization, OrganizationMember
from tests.test_knowledge_bases_documents import (
    add_membership,
    auth_headers,
    create_knowledge_base,
    create_organization,
    create_user_and_token,
    upload_text_document,
)


def prepared_document(
    client: TestClient,
    token: str,
    organization_id: str,
    knowledge_base_id: str,
) -> dict:
    """A document taken all the way to indexed, so it has chunks to cascade."""
    uploaded = upload_text_document(
        client,
        token,
        organization_id,
        knowledge_base_id,
    )
    assert uploaded.status_code == 201
    document = uploaded.json()
    prepared = client.post(
        f"/api/v1/organizations/{organization_id}/documents/{document['id']}/prepare",
        headers=auth_headers(token),
    )
    assert prepared.status_code in {200, 202}
    return document


def stored_file(document: dict) -> Path:
    return resolve_storage_path(document["file_path"]) if document.get(
        "file_path"
    ) else Path()


@pytest.fixture
def workspace(client: TestClient):
    token = create_user_and_token(client, "owner@example.com")
    organization = create_organization(client, token)
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    return token, organization, knowledge_base


def test_deleting_a_document_takes_its_chunks_and_its_file(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    document = prepared_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )
    document_id = uuid.UUID(document["id"])
    stored = db.get(Document, document_id)
    assert stored is not None
    on_disk = resolve_storage_path(stored.file_path)
    assert on_disk.exists()
    assert db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}/documents/{document['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    db.expire_all()
    assert db.get(Document, document_id) is None
    assert not db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    assert not on_disk.exists()


def test_deleting_a_document_that_is_being_prepared_is_refused(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    uploaded = upload_text_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    ).json()
    stored = db.get(Document, uuid.UUID(uploaded["id"]))
    stored.status = "processing"
    db.commit()

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}/documents/{uploaded['id']}",
        headers=auth_headers(token),
    )

    # Refused rather than accepted, because deleting the row would not call
    # back the embedding request that is already in flight.
    assert response.status_code == 409
    db.expire_all()
    assert db.get(Document, uuid.UUID(uploaded["id"])) is not None


def test_a_plain_member_cannot_delete_a_document(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    document = upload_text_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    ).json()
    member_token = create_user_and_token(client, "member@example.com")
    add_membership(
        db,
        email="member@example.com",
        organization_id=organization["id"],
        role="member",
    )

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}/documents/{document['id']}",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403


def test_a_document_in_another_workspace_is_not_found(client: TestClient, workspace):
    token, organization, knowledge_base = workspace
    document = upload_text_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    ).json()
    other_token = create_user_and_token(client, "outsider@example.com")
    other_organization = create_organization(client, other_token, slug="other-org")

    response = client.delete(
        f"/api/v1/organizations/{other_organization['id']}/documents/{document['id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_deleting_a_knowledge_space_takes_its_documents(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    document = prepared_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )
    on_disk = resolve_storage_path(
        db.get(Document, uuid.UUID(document["id"])).file_path
    )
    assert on_disk.exists()

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}"
        f"/knowledge-bases/{knowledge_base['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    db.expire_all()
    assert db.get(KnowledgeBase, uuid.UUID(knowledge_base["id"])) is None
    assert db.get(Document, uuid.UUID(document["id"])) is None
    assert not on_disk.exists()


def test_deleting_a_knowledge_space_keeps_its_conversations(
    client: TestClient,
    db: Session,
    workspace,
):
    """History survives; it just has nothing left to search.

    Deleting the answers because someone removed the source would be
    destroying a second thing they did not ask about.
    """
    token, organization, knowledge_base = workspace
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Refunds"},
        headers=auth_headers(token),
    )
    assert conversation.status_code == 201
    conversation_id = uuid.UUID(conversation.json()["id"])

    client.delete(
        f"/api/v1/organizations/{organization['id']}"
        f"/knowledge-bases/{knowledge_base['id']}",
        headers=auth_headers(token),
    )

    db.expire_all()
    surviving = db.get(Conversation, conversation_id)
    assert surviving is not None
    assert surviving.knowledge_base_id is None


def test_deleting_a_knowledge_space_mid_preparation_is_refused(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    uploaded = upload_text_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    ).json()
    db.get(Document, uuid.UUID(uploaded["id"])).status = "processing"
    db.commit()

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}"
        f"/knowledge-bases/{knowledge_base['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_deleting_a_workspace_takes_everything_keyed_to_it(
    client: TestClient,
    db: Session,
    workspace,
):
    token, organization, knowledge_base = workspace
    document = prepared_document(
        client,
        token,
        organization["id"],
        knowledge_base["id"],
    )
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Refunds"},
        headers=auth_headers(token),
    ).json()
    message = client.post(
        f"/api/v1/organizations/{organization['id']}"
        f"/conversations/{conversation['id']}/messages",
        json={
            "question": "How do refunds work?",
            "knowledge_base_id": knowledge_base["id"],
        },
        headers=auth_headers(token),
    )
    assert message.status_code == 200
    organization_id = uuid.UUID(organization["id"])
    upload_root = resolve_storage_path(
        Path(settings.upload_dir) / organization["id"]
    )
    assert upload_root.exists()

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    db.expire_all()
    assert db.get(Organization, organization_id) is None
    for model in (
        KnowledgeBase,
        Document,
        DocumentChunk,
        Conversation,
        Message,
        MessageCitation,
        OrganizationMember,
    ):
        remaining = db.scalars(
            select(model).where(model.organization_id == organization_id)
        ).all()
        assert not remaining, f"{model.__name__} rows survived the workspace"
    assert not upload_root.exists()


def test_deleting_a_workspace_leaves_its_members_accounts_alone(
    client: TestClient,
    db: Session,
    workspace,
):
    """A person is not owned by a workspace; someone in two must keep both."""
    token, organization, _knowledge_base = workspace
    second = create_organization(client, token, slug="second-org")

    client.delete(
        f"/api/v1/organizations/{organization['id']}",
        headers=auth_headers(token),
    )

    still_signed_in = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert still_signed_in.status_code == 200
    remaining = client.get("/api/v1/organizations", headers=auth_headers(token))
    assert [row["id"] for row in remaining.json()] == [second["id"]]


def test_an_admin_cannot_delete_a_workspace(client: TestClient, db: Session, workspace):
    """Owner only. Every other destructive action here is recoverable by
    re-uploading; this one takes other people's chat history too."""
    token, organization, _knowledge_base = workspace
    admin_token = create_user_and_token(client, "admin@example.com")
    add_membership(
        db,
        email="admin@example.com",
        organization_id=organization["id"],
        role="admin",
    )

    response = client.delete(
        f"/api/v1/organizations/{organization['id']}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 403
