"""
pytest Configuration and Shared Fixtures

This file is auto-loaded by pytest before running any tests.
"Fixtures" are reusable setup/teardown functions that tests can use.

WHY THIS IS HERE:
  Tests need a database, but not the PRODUCTION database.
  This file sets up an in-memory/test database that is:
    - Completely separate from production
    - Reset between test runs
    - Fast (no actual Redis/Celery needed for unit tests)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from core.database import Base, get_db

# ─── Test Database ────────────────────────────────────────────────────────────
# We use SQLite for unit tests (no PostgreSQL needed for simple tests)
# Integration tests (in CI) use the real PostgreSQL from environment variables
TEST_DATABASE_URL = "sqlite:///./test_gridmind.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite in tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh test database for each test function.
    All tables are created before the test, dropped after.
    This ensures tests are isolated from each other.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a FastAPI test client that uses our test database.
    
    We override the `get_db` dependency so the API uses the test DB,
    not the production DB.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Test fixture handles closing

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
