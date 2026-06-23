"""API endpoint connectivity tests."""
import pytest


@pytest.mark.anyio
async def test_health_endpoint(async_client):
    """Verify /health returns healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.anyio
async def test_docs_endpoint(async_client):
    """Verify /docs returns Swagger UI."""
    response = await async_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_dashboard_requires_auth(async_client):
    """Verify /api/v1/dashboard returns 401 without auth."""
    response = await async_client.get("/api/v1/dashboard")
    assert response.status_code in (401, 403)
