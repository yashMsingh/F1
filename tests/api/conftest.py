"""Pytest fixtures for API layer tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.deps import get_db
from tests.analytics.conftest import bahrain_analytics_data  # noqa: F401


@pytest.fixture
def client(session: Session, bahrain_analytics_data):  # noqa: F811
    """FastAPI TestClient with overridden get_db yielding the test session."""

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
