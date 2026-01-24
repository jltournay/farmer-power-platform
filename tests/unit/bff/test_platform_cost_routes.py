"""Tests for Platform Cost admin routes (Story 9.10a).

Tests route layer: HTTP status codes, auth, query params, error handling.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from bff.api.middleware.auth import get_current_user
from bff.api.routes.admin.platform_cost import get_platform_cost_service
from bff.api.schemas.admin.platform_cost_schemas import (
    BudgetConfigResponse,
    BudgetStatusResponse,
    CostSummaryResponse,
    CostTypeBreakdown,
    CurrentDayCostResponse,
    DailyTrendEntry,
    DailyTrendResponse,
    DocumentCostResponse,
    EmbeddingByDomainResponse,
    LlmByAgentTypeResponse,
    LlmByModelResponse,
)
from bff.api.schemas.auth import TokenClaims
from bff.infrastructure.clients import ServiceUnavailableError
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Build test app with dependency overrides
app = FastAPI()

# Import and register the router (must come after app creation)
from bff.api.routes.admin.platform_cost import router  # noqa: E402

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


# Override auth dependency to bypass JWT validation
app.dependency_overrides[get_current_user] = _mock_admin_user

# Mock service instance shared across tests
_mock_service = AsyncMock()


def _get_mock_service():
    return _mock_service


app.dependency_overrides[get_platform_cost_service] = _get_mock_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mock_service():
    """Reset mock service before each test."""
    _mock_service.reset_mock()
    yield


class TestGetCostSummaryRoute:
    """Tests for GET /api/admin/costs/summary."""

    def test_success(self):
        """Test successful cost summary retrieval."""
        _mock_service.get_cost_summary.return_value = CostSummaryResponse(
            total_cost_usd=Decimal("150.75"),
            total_requests=1200,
            by_type=[
                CostTypeBreakdown(cost_type="llm", total_cost_usd=Decimal("120.50"), percentage=79.9),
            ],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        response = client.get("/api/admin/costs/summary?start_date=2026-01-01&end_date=2026-01-24")

        assert response.status_code == 200
        data = response.json()
        assert data["total_cost_usd"] == "150.75"
        assert data["total_requests"] == 1200
        assert len(data["by_type"]) == 1

    def test_with_factory_filter(self):
        """Test cost summary with factory filter."""
        _mock_service.get_cost_summary.return_value = CostSummaryResponse(
            total_cost_usd=Decimal("50.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        response = client.get("/api/admin/costs/summary?start_date=2026-01-01&end_date=2026-01-24&factory_id=fac-001")

        assert response.status_code == 200
        _mock_service.get_cost_summary.assert_called_once_with(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            factory_id="fac-001",
        )

    def test_missing_required_params(self):
        """Test missing required query params returns 422."""
        response = client.get("/api/admin/costs/summary")
        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test 503 when service is unavailable."""
        _mock_service.get_cost_summary.side_effect = ServiceUnavailableError("Platform Cost unavailable")

        response = client.get("/api/admin/costs/summary?start_date=2026-01-01&end_date=2026-01-24")

        assert response.status_code == 503


class TestGetDailyTrendRoute:
    """Tests for GET /api/admin/costs/trend/daily."""

    def test_success_default_days(self):
        """Test daily trend with default parameters."""
        _mock_service.get_daily_cost_trend.return_value = DailyTrendResponse(
            entries=[
                DailyTrendEntry(entry_date=date(2026, 1, 24), total_cost_usd=Decimal("5.50")),
            ],
            data_available_from=date(2025, 12, 25),
        )

        response = client.get("/api/admin/costs/trend/daily")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1

    def test_with_custom_days(self):
        """Test daily trend with custom days parameter."""
        _mock_service.get_daily_cost_trend.return_value = DailyTrendResponse(
            entries=[],
            data_available_from=date(2026, 1, 1),
        )

        response = client.get("/api/admin/costs/trend/daily?days=7")

        assert response.status_code == 200
        _mock_service.get_daily_cost_trend.assert_called_once_with(
            start_date=None,
            end_date=None,
            days=7,
        )

    def test_invalid_days(self):
        """Test invalid days parameter returns 422."""
        response = client.get("/api/admin/costs/trend/daily?days=0")
        assert response.status_code == 422


class TestGetCurrentDayCostRoute:
    """Tests for GET /api/admin/costs/today."""

    def test_success(self):
        """Test current day cost retrieval."""
        _mock_service.get_current_day_cost.return_value = CurrentDayCostResponse(
            cost_date=date(2026, 1, 24),
            total_cost_usd=Decimal("3.75"),
            by_type={"llm": Decimal("3.00")},
            updated_at=datetime(2026, 1, 24, 14, 30, 0),
        )

        response = client.get("/api/admin/costs/today")

        assert response.status_code == 200
        data = response.json()
        assert data["total_cost_usd"] == "3.75"
        assert data["cost_date"] == "2026-01-24"


class TestGetLlmByAgentTypeRoute:
    """Tests for GET /api/admin/costs/llm/by-agent-type."""

    def test_success(self):
        """Test LLM by agent type retrieval."""
        _mock_service.get_llm_cost_by_agent_type.return_value = LlmByAgentTypeResponse(
            agent_costs=[],
            total_llm_cost_usd=Decimal("83.33"),
        )

        response = client.get("/api/admin/costs/llm/by-agent-type")

        assert response.status_code == 200
        data = response.json()
        assert data["total_llm_cost_usd"] == "83.33"


class TestGetLlmByModelRoute:
    """Tests for GET /api/admin/costs/llm/by-model."""

    def test_success(self):
        """Test LLM by model retrieval."""
        _mock_service.get_llm_cost_by_model.return_value = LlmByModelResponse(
            model_costs=[],
            total_llm_cost_usd=Decimal("40.00"),
        )

        response = client.get("/api/admin/costs/llm/by-model")

        assert response.status_code == 200


class TestGetDocumentCostRoute:
    """Tests for GET /api/admin/costs/documents."""

    def test_success(self):
        """Test document cost summary retrieval."""
        _mock_service.get_document_cost_summary.return_value = DocumentCostResponse(
            total_cost_usd=Decimal("25.00"),
            total_pages=500,
            avg_cost_per_page_usd=Decimal("0.05"),
            document_count=50,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        response = client.get("/api/admin/costs/documents?start_date=2026-01-01&end_date=2026-01-24")

        assert response.status_code == 200
        data = response.json()
        assert data["total_pages"] == 500


class TestGetEmbeddingByDomainRoute:
    """Tests for GET /api/admin/costs/embeddings/by-domain."""

    def test_success(self):
        """Test embedding by domain retrieval."""
        _mock_service.get_embedding_cost_by_domain.return_value = EmbeddingByDomainResponse(
            domain_costs=[],
            total_embedding_cost_usd=Decimal("5.00"),
        )

        response = client.get("/api/admin/costs/embeddings/by-domain")

        assert response.status_code == 200


class TestGetBudgetStatusRoute:
    """Tests for GET /api/admin/costs/budget."""

    def test_success(self):
        """Test budget status retrieval."""
        _mock_service.get_budget_status.return_value = BudgetStatusResponse(
            daily_threshold_usd=Decimal("50.00"),
            daily_total_usd=Decimal("10.00"),
            daily_remaining_usd=Decimal("40.00"),
            daily_utilization_percent=20.0,
            monthly_threshold_usd=Decimal("1000.00"),
            monthly_total_usd=Decimal("150.00"),
            monthly_remaining_usd=Decimal("850.00"),
            monthly_utilization_percent=15.0,
            current_day="2026-01-24",
            current_month="2026-01",
        )

        response = client.get("/api/admin/costs/budget")

        assert response.status_code == 200
        data = response.json()
        assert data["daily_utilization_percent"] == 20.0


class TestConfigureBudgetRoute:
    """Tests for PUT /api/admin/costs/budget."""

    def test_success_daily_only(self):
        """Test configuring daily threshold only."""
        _mock_service.configure_budget_threshold.return_value = BudgetConfigResponse(
            daily_threshold_usd=Decimal("75.00"),
            monthly_threshold_usd=Decimal("1000.00"),
            message="Updated",
            updated_at=datetime(2026, 1, 24, 15, 0, 0),
        )

        response = client.put(
            "/api/admin/costs/budget",
            json={"daily_threshold_usd": "75.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["daily_threshold_usd"] == "75.00"

    def test_both_none_returns_400(self):
        """Test that both thresholds being None returns 400."""
        response = client.put(
            "/api/admin/costs/budget",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "VALIDATION_ERROR"

    def test_negative_threshold_returns_422(self):
        """Test that negative threshold returns validation error."""
        response = client.put(
            "/api/admin/costs/budget",
            json={"daily_threshold_usd": "-10.00"},
        )

        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test 503 when service unavailable."""
        _mock_service.configure_budget_threshold.side_effect = ServiceUnavailableError("unavailable")

        response = client.put(
            "/api/admin/costs/budget",
            json={"daily_threshold_usd": "50.00"},
        )

        assert response.status_code == 503
