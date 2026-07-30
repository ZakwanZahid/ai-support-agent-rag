import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import Organization, OrganizationMember
from app.models.user import User


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
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_size_mb = 10
    try:
        yield
    finally:
        settings.upload_dir = original_upload_dir
        settings.max_upload_size_mb = original_max_size


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
