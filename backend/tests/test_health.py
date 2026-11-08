import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


def test_app_starts_and_metadata_valid():
    """Verify application initializes successfully with expected metadata."""
    assert app.title == settings.PROJECT_NAME
    assert app.version == settings.VERSION
    assert app.openapi_url == f"{settings.API_V1_STR}/openapi.json"
    assert app.docs_url == f"{settings.API_V1_STR}/docs"


def test_health_check_sync_client():
    """Verify health endpoint returns HTTP 200 with expected synchronous payload."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.PROJECT_NAME
    assert data["environment"] == settings.ENVIRONMENT
    assert data["version"] == "1.0.0"
    assert data["api_version"] == "v1"


@pytest.mark.anyio
async def test_health_check_async_client():
    """Verify health endpoint responds asynchronously with valid JSON structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == settings.PROJECT_NAME
        assert data["environment"] == settings.ENVIRONMENT
        assert data["version"] == "1.0.0"
        assert data["api_version"] == "v1"


def test_health_check_schema_keys():
    """Verify health response contains all required fields with expected types."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    required_keys = {"status", "app_name", "environment", "version", "api_version"}
    assert required_keys == set(data.keys())
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["api_version"] == "v1"
    assert isinstance(data["status"], str)
    assert isinstance(data["app_name"], str)
    assert isinstance(data["environment"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["api_version"], str)
