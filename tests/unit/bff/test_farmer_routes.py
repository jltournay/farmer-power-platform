"""Tests for Farmer API routes.

Tests endpoint behavior, authentication, and error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bff.api.schemas import PaginationMeta
from bff.api.schemas.farmer_schemas import (
    FarmerDetailResponse,
    FarmerListResponse,
    FarmerPerformanceAPI,
    FarmerProfile,
    FarmerSummary,
    TierLevel,
    TrendIndicator,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from fastapi.testclient import TestClient

from tests.unit.bff.conftest import MOCK_JWT_SECRET, auth_headers


@pytest.fixture
def mock_farmer_service():
    """Create a mock FarmerService."""
    service = MagicMock()
    service.list_farmers = AsyncMock()
    service.get_farmer = AsyncMock()
    return service


@pytest.fixture
def sample_farmer_list_response() -> FarmerListResponse:
    """Create a sample FarmerListResponse."""
    return FarmerListResponse(
        data=[
            FarmerSummary(
                id="WM-0001",
                name="Wanjiku Muthoni",
                primary_percentage_30d=82.5,
                tier=TierLevel.TIER_2,
                trend=TrendIndicator.UP,
            ),
            FarmerSummary(
                id="WM-0002",
                name="John Kamau",
                primary_percentage_30d=91.0,
                tier=TierLevel.TIER_1,
                trend=TrendIndicator.STABLE,
            ),
        ],
        pagination=PaginationMeta(
            page=1,
            page_size=50,
            total_count=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@pytest.fixture
def sample_farmer_detail_response() -> FarmerDetailResponse:
    """Create a sample FarmerDetailResponse."""
    return FarmerDetailResponse(
        profile=FarmerProfile(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Muthoni",
            phone="+254712345678",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_size_hectares=1.5,
            registration_date=datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC),
            is_active=True,
        ),
        performance=FarmerPerformanceAPI(
            primary_percentage_30d=82.5,
            primary_percentage_90d=78.0,
            total_kg_30d=450.0,
            total_kg_90d=1200.0,
            trend=TrendIndicator.UP,
            deliveries_today=2,
            kg_today=35.5,
        ),
        tier=TierLevel.TIER_2,
    )


@pytest.fixture
def bff_client_with_mock_service(monkeypatch, mock_farmer_service):
    """Create BFF client with mocked farmer service."""
    # Set the environment variable for mock JWT secret
    monkeypatch.setenv("MOCK_JWT_SECRET", MOCK_JWT_SECRET)

    # Clear cached settings so new env var is picked up
    from bff.config import get_settings

    get_settings.cache_clear()

    from bff.api.routes.farmers import get_farmer_service
    from bff.main import create_app

    app = create_app()

    # Override the dependency
    app.dependency_overrides[get_farmer_service] = lambda: mock_farmer_service

    return TestClient(app)


class TestListFarmersEndpoint:
    """Tests for GET /api/farmers endpoint."""

    def test_list_farmers_success(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_manager_token: str,
        sample_farmer_list_response: FarmerListResponse,
    ):
        """Test successful farmer listing."""
        mock_farmer_service.list_farmers.return_value = sample_farmer_list_response

        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-001",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "WM-0001"
        assert data["data"][0]["name"] == "Wanjiku Muthoni"
        assert data["data"][0]["tier"] == "tier_2"
        assert data["data"][0]["trend"] == "up"
        assert data["pagination"]["total_count"] == 2

    def test_list_farmers_with_pagination(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_manager_token: str,
        sample_farmer_list_response: FarmerListResponse,
    ):
        """Test farmer listing with pagination parameters."""
        mock_farmer_service.list_farmers.return_value = sample_farmer_list_response

        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-001&page_size=20&page_token=cursor-abc",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 200
        mock_farmer_service.list_farmers.assert_called_once_with(
            factory_id="KEN-FAC-001",
            page_size=20,
            page_token="cursor-abc",
        )

    def test_list_farmers_requires_authentication(
        self,
        bff_client: TestClient,
    ):
        """Test that endpoint requires authentication."""
        response = bff_client.get("/api/farmers?factory_id=KEN-FAC-001")
        assert response.status_code == 403  # HTTPBearer returns 403 for missing credentials

    def test_list_farmers_requires_permission(
        self,
        bff_client: TestClient,
        mock_regulator_token: str,  # Regulator doesn't have farmers:read
    ):
        """Test that endpoint requires farmers:read permission."""
        response = bff_client.get(
            "/api/farmers?factory_id=KEN-FAC-001",
            headers=auth_headers(mock_regulator_token),
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "insufficient_permissions"

    def test_list_farmers_requires_factory_access(
        self,
        bff_client_with_mock_service: TestClient,
        mock_manager_token: str,
    ):
        """Test that user must have access to the requested factory."""
        # Manager has access to KEN-FAC-001 but not KEN-FAC-999
        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-999",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "forbidden"

    def test_list_farmers_platform_admin_any_factory(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_admin_token: str,
        sample_farmer_list_response: FarmerListResponse,
    ):
        """Test that platform admin can access any factory."""
        mock_farmer_service.list_farmers.return_value = sample_farmer_list_response

        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-999",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 200

    def test_list_farmers_factory_not_found(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_admin_token: str,
    ):
        """Test 404 when factory not found."""
        mock_farmer_service.list_farmers.side_effect = NotFoundError("Factory not found")

        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-001",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "not_found"

    def test_list_farmers_service_unavailable(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_admin_token: str,
    ):
        """Test 503 when downstream service unavailable."""
        mock_farmer_service.list_farmers.side_effect = ServiceUnavailableError("Service down")

        response = bff_client_with_mock_service.get(
            "/api/farmers?factory_id=KEN-FAC-001",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "service_unavailable"

    def test_list_farmers_requires_factory_id(
        self,
        bff_client: TestClient,
        mock_manager_token: str,
    ):
        """Test that factory_id is required."""
        response = bff_client.get(
            "/api/farmers",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 422  # Validation error

    def test_list_farmers_validates_factory_id_format(
        self,
        bff_client: TestClient,
        mock_manager_token: str,
    ):
        """Test factory_id format validation."""
        response = bff_client.get(
            "/api/farmers?factory_id=invalid-format",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 422  # Validation error

    def test_list_farmers_validates_page_size_range(
        self,
        bff_client: TestClient,
        mock_manager_token: str,
    ):
        """Test page_size must be 1-100."""
        # Too large
        response = bff_client.get(
            "/api/farmers?factory_id=KEN-FAC-001&page_size=200",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 422

        # Too small
        response = bff_client.get(
            "/api/farmers?factory_id=KEN-FAC-001&page_size=0",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 422

    def test_list_farmers_expired_token(
        self,
        bff_client: TestClient,
        expired_token: str,
    ):
        """Test expired token is rejected."""
        response = bff_client.get(
            "/api/farmers?factory_id=KEN-FAC-001",
            headers=auth_headers(expired_token),
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == "token_expired"


class TestGetFarmerEndpoint:
    """Tests for GET /api/farmers/{farmer_id} endpoint."""

    def test_get_farmer_success(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_manager_token: str,
        sample_farmer_detail_response: FarmerDetailResponse,
    ):
        """Test successful farmer detail retrieval."""
        mock_farmer_service.get_farmer.return_value = sample_farmer_detail_response

        response = bff_client_with_mock_service.get(
            "/api/farmers/WM-0001",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["id"] == "WM-0001"
        assert data["profile"]["first_name"] == "Wanjiku"
        assert data["profile"]["last_name"] == "Muthoni"
        assert data["performance"]["primary_percentage_30d"] == 82.5
        assert data["performance"]["deliveries_today"] == 2
        assert data["tier"] == "tier_2"
        assert "meta" in data

    def test_get_farmer_not_found(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_manager_token: str,
    ):
        """Test 404 when farmer not found."""
        mock_farmer_service.get_farmer.side_effect = NotFoundError("Farmer not found")

        response = bff_client_with_mock_service.get(
            "/api/farmers/WM-9999",
            headers=auth_headers(mock_manager_token),
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "not_found"
        assert "WM-9999" in data["detail"]["message"]

    def test_get_farmer_requires_authentication(
        self,
        bff_client: TestClient,
    ):
        """Test that endpoint requires authentication."""
        response = bff_client.get("/api/farmers/WM-0001")
        assert response.status_code == 403  # HTTPBearer returns 403 for missing credentials

    def test_get_farmer_requires_permission(
        self,
        bff_client: TestClient,
        mock_regulator_token: str,
    ):
        """Test that endpoint requires farmers:read permission."""
        response = bff_client.get(
            "/api/farmers/WM-0001",
            headers=auth_headers(mock_regulator_token),
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "insufficient_permissions"

    def test_get_farmer_validates_id_format(
        self,
        bff_client: TestClient,
        mock_manager_token: str,
    ):
        """Test farmer_id format validation."""
        response = bff_client.get(
            "/api/farmers/invalid-id",
            headers=auth_headers(mock_manager_token),
        )
        assert response.status_code == 422

    def test_get_farmer_service_unavailable(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_admin_token: str,
    ):
        """Test 503 when downstream service unavailable."""
        mock_farmer_service.get_farmer.side_effect = ServiceUnavailableError("Service down")

        response = bff_client_with_mock_service.get(
            "/api/farmers/WM-0001",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 503

    def test_get_farmer_platform_admin_access(
        self,
        bff_client_with_mock_service: TestClient,
        mock_farmer_service: MagicMock,
        mock_admin_token: str,
        sample_farmer_detail_response: FarmerDetailResponse,
    ):
        """Test that platform admin can access any farmer."""
        mock_farmer_service.get_farmer.return_value = sample_farmer_detail_response

        response = bff_client_with_mock_service.get(
            "/api/farmers/WM-0001",
            headers=auth_headers(mock_admin_token),
        )

        assert response.status_code == 200
