import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_ingestion_runner
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.ingestion.pipeline import ingest_document
from app.models.document import Document, DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.types import Vector


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
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_size_mb = 10
    settings.auto_ingest_on_upload = False
    settings.chunk_size = 1200
    settings.chunk_overlap = 200
    try:
        yield
    finally:
        settings.upload_dir = original_upload_dir
        settings.max_upload_size_mb = original_max_size
        settings.auto_ingest_on_upload = original_auto_ingest
        settings.chunk_size = original_chunk_size
        settings.chunk_overlap = original_chunk_overlap


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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ingestion_runner] = lambda: run_ingestion_for_test
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
