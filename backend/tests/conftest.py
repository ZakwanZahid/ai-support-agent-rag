import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_db,
    get_indexing_runner,
    get_ingestion_runner,
    get_request_chat_provider,
    get_request_embedding_provider,
)
from app.core.config import settings
from app.embeddings.indexing import index_document
from app.main import app
from app.models.base import Base
from app.ingestion.pipeline import ingest_document
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.types import Vector


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embedding(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embedding(query)

    @staticmethod
    def _embedding(text: str) -> list[float]:
        normalized = text.lower()
        embedding = [0.0] * settings.embedding_dimensions
        embedding[0] = 1.0 if "refund" in normalized else 0.0
        embedding[1] = 1.0 if "shipping" in normalized else 0.0
        embedding[2] = 1.0 if "password" in normalized else 0.0
        if not any(embedding[:3]):
            embedding[3] = 1.0
        return embedding


class FakeChatProvider:
    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        assert "Use only the context" in system_prompt
        assert "[source 1]" in user_prompt
        return "Customers can request a refund within 14 days of purchase."


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@compiles(Vector, "sqlite")
def compile_vector_for_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
test_tables = [
    User.__table__,
    Organization.__table__,
    OrganizationMember.__table__,
    KnowledgeBase.__table__,
    Document.__table__,
    DocumentChunk.__table__,
    Conversation.__table__,
    Message.__table__,
    MessageCitation.__table__,
]


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(bind=engine, tables=test_tables)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine, tables=reversed(test_tables))


@pytest.fixture(autouse=True)
def temporary_upload_directory(tmp_path):
    original_upload_dir = settings.upload_dir
    original_max_size = settings.max_upload_size_mb
    original_auto_ingest = settings.auto_ingest_on_upload
    original_chunk_size = settings.chunk_size
    original_chunk_overlap = settings.chunk_overlap
    original_embedding_dimensions = settings.embedding_dimensions
    original_index_batch_size = settings.index_batch_size
    original_rag_top_k = settings.rag_top_k
    original_rag_max_context_chars = settings.rag_max_context_chars
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_size_mb = 10
    settings.auto_ingest_on_upload = False
    settings.chunk_size = 1200
    settings.chunk_overlap = 200
    settings.embedding_dimensions = 1536
    settings.index_batch_size = 50
    settings.rag_top_k = 5
    settings.rag_max_context_chars = 12000
    try:
        yield
    finally:
        settings.upload_dir = original_upload_dir
        settings.max_upload_size_mb = original_max_size
        settings.auto_ingest_on_upload = original_auto_ingest
        settings.chunk_size = original_chunk_size
        settings.chunk_overlap = original_chunk_overlap
        settings.embedding_dimensions = original_embedding_dimensions
        settings.index_batch_size = original_index_batch_size
        settings.rag_top_k = original_rag_top_k
        settings.rag_max_context_chars = original_rag_max_context_chars


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db():
        yield db

    def run_ingestion_for_test(document_id, organization_id, force=False):
        ingest_document(
            document_id,
            organization_id,
            force,
            session_factory=TestingSessionLocal,
        )

    def get_fake_embedding_provider():
        return FakeEmbeddingProvider()

    def run_indexing_for_test(document_id, organization_id, force=False):
        index_document(
            document_id,
            organization_id,
            force,
            session_factory=TestingSessionLocal,
            provider_factory=get_fake_embedding_provider,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ingestion_runner] = lambda: run_ingestion_for_test
    app.dependency_overrides[get_indexing_runner] = lambda: run_indexing_for_test
    app.dependency_overrides[get_request_embedding_provider] = (
        get_fake_embedding_provider
    )
    app.dependency_overrides[get_request_chat_provider] = FakeChatProvider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
