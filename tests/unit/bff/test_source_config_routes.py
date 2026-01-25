"""Tests for Source Config admin routes (Story 9.11b).

Tests route layer: HTTP status codes, auth, query params, error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from bff.api.middleware.auth import get_current_user
from bff.api.routes.admin.source_configs import get_source_config_client
from bff.api.schemas import PaginatedResponse
from bff.api.schemas.auth import TokenClaims
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fp_common.models import SourceConfigDetail, SourceConfigSummary

# Build test app with dependency overrides
app = FastAPI()

# Import and register the router (must come after app creation)
from bff.api.routes.admin.source_configs import router  # noqa: E402

app.include_router(router, prefix="/api/admin")


def _mock_admin_user() -> TokenClaims:
    """Create a mock platform admin TokenClaims."""
    return TokenClaims(
        sub="admin-user",
        email="admin@farmerpower.test",
        name="Test Admin",
        role="platform_admin",
        factory_id=None,
    )


def _mock_non_admin_user() -> TokenClaims:
    """Create a mock factory_manager TokenClaims."""
    return TokenClaims(
        sub="manager-user",
        email="manager@factory.test",
        name="Test Manager",
        role="factory_manager",
        factory_id="FAC-001",
    )


# Override auth dependency to bypass JWT validation
app.dependency_overrides[get_current_user] = _mock_admin_user

# Mock client instance shared across tests
_mock_client = AsyncMock()


def _get_mock_client():
    return _mock_client


app.dependency_overrides[get_source_config_client] = _get_mock_client

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mock_client():
    """Reset mock client before each test."""
    _mock_client.reset_mock()
    # Clear side_effect to prevent lingering error states
    _mock_client.list_source_configs.side_effect = None
    _mock_client.get_source_config.side_effect = None
    yield


def create_source_config_summary(
    source_id: str = "qc-analyzer-result",
    display_name: str = "QC Analyzer Results",
    enabled: bool = True,
    ingestion_mode: str = "blob_trigger",
) -> SourceConfigSummary:
    """Create a SourceConfigSummary domain model for testing."""
    return SourceConfigSummary(
        source_id=source_id,
        display_name=display_name,
        description="Test description",
        enabled=enabled,
        ingestion_mode=ingestion_mode,
        ai_agent_id="qc-extractor-v1",
        updated_at=datetime.now(UTC),
    )


def create_source_config_detail(
    source_id: str = "qc-analyzer-result",
    display_name: str = "QC Analyzer Results",
) -> SourceConfigDetail:
    """Create a SourceConfigDetail domain model for testing."""
    return SourceConfigDetail(
        source_id=source_id,
        display_name=display_name,
        description="Test description",
        enabled=True,
        ingestion_mode="blob_trigger",
        ai_agent_id="qc-extractor-v1",
        config_json='{"source_id": "qc-analyzer-result", "enabled": true}',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestListSourceConfigsRoute:
    """Tests for GET /api/admin/source-configs."""

    def test_success(self):
        """Test successful source config listing."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[
                create_source_config_summary(source_id="source-001"),
                create_source_config_summary(source_id="source-002"),
            ],
            total_count=2,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/source-configs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["source_id"] == "source-001"
        assert data["data"][1]["source_id"] == "source-002"
        assert data["pagination"]["total_count"] == 2

    def test_with_pagination(self):
        """Test source config listing with pagination parameters."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_source_config_summary()],
            total_count=100,
            page_size=10,
            next_page_token="next-token",
        )

        response = client.get("/api/admin/source-configs?page_size=10&page_token=prev-token")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 10
        assert data["pagination"]["next_page_token"] == "next-token"
        _mock_client.list_source_configs.assert_called_once_with(
            page_size=10,
            page_token="prev-token",
            enabled_only=False,
            ingestion_mode=None,
        )

    def test_with_enabled_only_filter(self):
        """Test source config listing with enabled_only filter."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_source_config_summary(enabled=True)],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/source-configs?enabled_only=true")

        assert response.status_code == 200
        _mock_client.list_source_configs.assert_called_once_with(
            page_size=20,
            page_token=None,
            enabled_only=True,
            ingestion_mode=None,
        )

    def test_with_ingestion_mode_filter(self):
        """Test source config listing with ingestion_mode filter."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_source_config_summary(ingestion_mode="blob_trigger")],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/source-configs?ingestion_mode=blob_trigger")

        assert response.status_code == 200
        _mock_client.list_source_configs.assert_called_once_with(
            page_size=20,
            page_token=None,
            enabled_only=False,
            ingestion_mode="blob_trigger",
        )

    def test_page_size_validation(self):
        """Test page_size validation (max 100)."""
        response = client.get("/api/admin/source-configs?page_size=200")
        # FastAPI validates Query constraints
        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test 503 when Collection Model is unavailable."""
        _mock_client.list_source_configs.side_effect = ServiceUnavailableError("Collection Model unavailable")

        response = client.get("/api/admin/source-configs")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_empty_result(self):
        """Test successful empty result."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[],
            total_count=0,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/source-configs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
        assert data["pagination"]["total_count"] == 0


class TestGetSourceConfigRoute:
    """Tests for GET /api/admin/source-configs/{source_id}."""

    def test_success(self):
        """Test successful source config detail retrieval."""
        _mock_client.get_source_config.return_value = create_source_config_detail(
            source_id="qc-analyzer-result",
            display_name="QC Analyzer Results",
        )

        response = client.get("/api/admin/source-configs/qc-analyzer-result")

        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "qc-analyzer-result"
        assert data["display_name"] == "QC Analyzer Results"
        assert "config_json" in data
        assert data["config_json"] == '{"source_id": "qc-analyzer-result", "enabled": true}'

    def test_not_found(self):
        """Test 404 when source config not found."""
        _mock_client.get_source_config.side_effect = NotFoundError("Source config not found")

        response = client.get("/api/admin/source-configs/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "SOURCE_CONFIG_NOT_FOUND"
        assert "nonexistent" in data["detail"]["message"]

    def test_service_unavailable(self):
        """Test 503 when Collection Model is unavailable."""
        _mock_client.get_source_config.side_effect = ServiceUnavailableError("Collection Model unavailable")

        response = client.get("/api/admin/source-configs/qc-analyzer-result")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_with_special_characters_in_id(self):
        """Test source_id with special characters."""
        _mock_client.get_source_config.return_value = create_source_config_detail(
            source_id="source-with-dashes-v2",
        )

        response = client.get("/api/admin/source-configs/source-with-dashes-v2")

        assert response.status_code == 200
        _mock_client.get_source_config.assert_called_once_with("source-with-dashes-v2")


class TestAuthRequirement:
    """Tests for authentication requirement on all routes."""

    def test_list_requires_platform_admin(self):
        """Test list endpoint requires platform_admin role."""
        # Override to use non-admin user
        app.dependency_overrides[get_current_user] = _mock_non_admin_user

        response = client.get("/api/admin/source-configs")

        # Should get 403 Forbidden
        assert response.status_code == 403

        # Restore admin user
        app.dependency_overrides[get_current_user] = _mock_admin_user

    def test_get_requires_platform_admin(self):
        """Test get endpoint requires platform_admin role."""
        # Override to use non-admin user
        app.dependency_overrides[get_current_user] = _mock_non_admin_user

        response = client.get("/api/admin/source-configs/qc-analyzer-result")

        # Should get 403 Forbidden
        assert response.status_code == 403

        # Restore admin user
        app.dependency_overrides[get_current_user] = _mock_admin_user


class TestResponseFormat:
    """Tests for response format compliance."""

    def test_list_response_format(self):
        """Test list response follows SourceConfigListResponse schema."""
        _mock_client.list_source_configs.return_value = PaginatedResponse.from_client_response(
            items=[create_source_config_summary()],
            total_count=1,
            page_size=20,
            next_page_token=None,
        )

        response = client.get("/api/admin/source-configs")

        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "data" in data
        assert "pagination" in data
        # Check data item fields
        item = data["data"][0]
        assert "source_id" in item
        assert "display_name" in item
        assert "description" in item
        assert "enabled" in item
        assert "ingestion_mode" in item
        # Pagination fields
        assert "page_size" in data["pagination"]
        assert "total_count" in data["pagination"]

    def test_detail_response_format(self):
        """Test detail response follows SourceConfigDetailResponse schema."""
        _mock_client.get_source_config.return_value = create_source_config_detail()

        response = client.get("/api/admin/source-configs/qc-analyzer-result")

        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "source_id" in data
        assert "display_name" in data
        assert "description" in data
        assert "enabled" in data
        assert "config_json" in data
        # Detail-specific fields
        assert "created_at" in data
        assert "updated_at" in data

    def test_timestamps_are_iso_format(self):
        """Test timestamp fields are ISO format strings."""
        _mock_client.get_source_config.return_value = create_source_config_detail()

        response = client.get("/api/admin/source-configs/qc-analyzer-result")

        assert response.status_code == 200
        data = response.json()
        # Should be ISO format strings like "2026-01-25T12:00:00"
        assert data["created_at"] is None or "T" in data["created_at"]
        assert data["updated_at"] is None or "T" in data["updated_at"]
