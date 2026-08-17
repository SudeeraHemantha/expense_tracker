"""
Pytest configuration and shared fixtures for Expense Tracker test suite.
Configures isolated in-memory SQLite database, test user, auth headers, and FastAPI TestClient.
"""

import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
parent_dir = project_root.parent

for p in [str(project_root), str(parent_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from database.connection import Base, get_db
from database.models import User
from services.auth_service import AuthService
from main import app

# Single shared in-memory SQLite test database engine
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Reset database tables before each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provide a transactional database session for unit testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a default test user with seeded categories."""
    from schemas.auth_schemas import UserCreate
    user = AuthService.register_user(
        db_session,
        UserCreate(email="testuser@example.com", password="password123", full_name="Test User")
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate JWT authorization headers for the default test user."""
    token = AuthService.create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """Provide FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c
