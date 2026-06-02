"""
Unit tests for FastAPI application initialization
"""

import pytest
from fastapi import FastAPI

from app.core.config import settings
from app.main import create_app


@pytest.mark.unit
def test_app_creation():
    app = create_app()
    assert app is not None
    assert isinstance(app, FastAPI)


@pytest.mark.unit
def test_app_title():
    app = create_app()
    assert app.title == f"{settings.app_name} API"


@pytest.mark.unit
def test_app_version():
    app = create_app()
    assert app.version == "0.1.0"


@pytest.mark.unit
def test_app_description():
    app = create_app()
    assert "Gold Trading" in app.description or "Gold" in app.description


@pytest.mark.unit
def test_cors_middleware_installed(client):
    # Verify CORS is active by checking that a cross-origin preflight returns the header
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" in response.headers


@pytest.mark.unit
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.unit
def test_app_root_endpoint(client):
    response = client.get("/")
    assert response.status_code in [200, 404, 307]


@pytest.mark.unit
def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
