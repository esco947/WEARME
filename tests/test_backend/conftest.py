"""Pytest fixtures for backend tests.

Uses an in-memory SQLite database so tests are isolated and fast.
The SMPL avatar_service is mocked — no .pkl files required.
"""

from __future__ import annotations

import pytest
from backend.database import Base, get_db
from backend.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# In-memory DB — StaticPool ensures all connections share the same DB
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Return a FastAPI TestClient using the in-memory DB."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def registered_user(client):
    """Register a user and return (client, token, user_data)."""
    resp = client.post("/api/auth/register", json={"email": "user@test.com", "password": "password123"})
    assert resp.status_code == 201
    data = resp.json()
    return data["access_token"], data["user"]


@pytest.fixture
def auth_headers(registered_user):
    token, _ = registered_user
    return {"Authorization": f"Bearer {token}"}
