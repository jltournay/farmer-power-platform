"""Unit tests for BFF main application.

Tests application startup and lifespan per AC5 requirements.
"""

from fastapi.testclient import TestClient


def test_app_creation() -> None:
    """Test that the FastAPI application is created successfully."""
    from bff.main import create_app

    app = create_app()
    assert app is not None
    assert app.title == "Farmer Power BFF"


def test_app_has_version() -> None:
    """Test that the app has a version."""
    from bff.main import create_app

    app = create_app()
    assert app.version == "0.1.0"


def test_app_has_description() -> None:
    """Test that the app has a description."""
    from bff.main import create_app

    app = create_app()
    assert "Backend for Frontend" in app.description


def test_app_lifespan_startup(bff_client: TestClient) -> None:
    """Test that the application starts up correctly via lifespan."""
    # TestClient handles lifespan automatically
    # If we get a response, lifespan startup succeeded
    response = bff_client.get("/health")
    assert response.status_code == 200


def test_health_router_included(bff_client: TestClient) -> None:
    """Test that health router is included in the application."""
    response = bff_client.get("/health")
    assert response.status_code == 200


def test_ready_router_included(bff_client: TestClient) -> None:
    """Test that ready endpoint router is included in the application."""
    response = bff_client.get("/ready")
    assert response.status_code == 200


def test_openapi_schema_available(bff_client: TestClient) -> None:
    """Test that OpenAPI schema is available."""
    response = bff_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Farmer Power BFF"
