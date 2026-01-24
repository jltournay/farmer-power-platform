"""E2E Tests: Platform Cost BFF REST API (Story 9.10a).

Validates the BFF REST layer for platform cost monitoring endpoints.
Tests the full flow: BFF HTTP → gRPC via DAPR → Platform Cost Service.

Acceptance Criteria (AC-E2E):
    Given the Platform Cost Service (Epic 13) is running with cost data populated,
    When the BFF receives GET /api/admin/costs/summary with date range,
    Then the response contains total_cost_usd > 0 with by_type breakdown
    matching the platform-cost service data.

Prerequisites:
    bash scripts/e2e-up.sh --build
    Wait for all services to be healthy before running tests.

Relates to #225
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient

pytestmark = pytest.mark.e2e


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


async def _admin_get(bff_api: BFFClient, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an admin GET request and return JSON response.

    Args:
        bff_api: BFF client fixture
        path: Request path (e.g., /api/admin/costs/summary)
        params: Optional query parameters

    Returns:
        JSON response body

    Raises:
        AssertionError: If response status is not 200
    """
    response = await bff_api.admin_request_raw("GET", path, params=params)
    assert response.status_code == 200, f"GET {path} returned {response.status_code}: {response.text}"
    return response.json()


async def _admin_put(bff_api: BFFClient, path: str, data: dict[str, Any]) -> dict[str, Any]:
    """Make an admin PUT request and return JSON response.

    Args:
        bff_api: BFF client fixture
        path: Request path
        data: Request body

    Returns:
        JSON response body

    Raises:
        AssertionError: If response status is not 200
    """
    response = await bff_api.admin_request_raw("PUT", path, json=data)
    assert response.status_code == 200, f"PUT {path} returned {response.status_code}: {response.text}"
    return response.json()


# ═══════════════════════════════════════════════════════════════════════════════
# AC-E2E: COST SUMMARY VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFSummary:
    """Test cost summary endpoint via BFF (AC-E2E)."""

    @pytest.mark.asyncio
    async def test_cost_summary_returns_breakdown_with_totals(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has cost data populated (seed data),
        When I call GET /api/admin/costs/summary with a date range,
        Then the response contains total_cost_usd >= 0 with by_type breakdown.
        """
        today = date.today().isoformat()
        start_of_month = date.today().replace(day=1).isoformat()

        result = await _admin_get(
            bff_api,
            "/api/admin/costs/summary",
            params={"start_date": start_of_month, "end_date": today},
        )

        # Verify response structure (AC 9.10a.1)
        assert "total_cost_usd" in result, "Response missing total_cost_usd"
        assert "by_type" in result, "Response missing by_type breakdown"
        assert "period_start" in result, "Response missing period_start"
        assert "period_end" in result, "Response missing period_end"

        # Verify total is non-negative
        total = Decimal(result["total_cost_usd"])
        assert total >= Decimal("0"), f"total_cost_usd should be non-negative, got {total}"

        # Verify by_type is a list
        by_type = result["by_type"]
        assert isinstance(by_type, list), "by_type should be a list"

        # If there are cost entries, verify structure
        if by_type:
            entry = by_type[0]
            assert "cost_type" in entry, "by_type entry missing cost_type"
            assert "total_cost_usd" in entry, "by_type entry missing total_cost_usd"

        print(f"[AC-E2E] Cost summary: total=${total}, types={len(by_type)}")

    @pytest.mark.asyncio
    async def test_cost_summary_with_factory_filter(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given cost data exists,
        When I call GET /api/admin/costs/summary with factory_id filter,
        Then the response succeeds and returns filtered data.
        """
        today = date.today().isoformat()

        result = await _admin_get(
            bff_api,
            "/api/admin/costs/summary",
            params={
                "start_date": today,
                "end_date": today,
                "factory_id": "KEN-FAC-001",
            },
        )

        assert "total_cost_usd" in result
        assert "by_type" in result
        print(f"[AC-E2E] Filtered summary: total=${result['total_cost_usd']}")


# ═══════════════════════════════════════════════════════════════════════════════
# CURRENT DAY COST VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFCurrentDay:
    """Test current day cost endpoint via BFF."""

    @pytest.mark.asyncio
    async def test_current_day_cost_returns_today(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service is running,
        When I call GET /api/admin/costs/today,
        Then the response contains today's date and running total.
        """
        result = await _admin_get(bff_api, "/api/admin/costs/today")

        # Verify response structure (AC 9.10a.3)
        assert "cost_date" in result, "Response missing cost_date"
        assert "total_cost_usd" in result, "Response missing total_cost_usd"
        assert "updated_at" in result, "Response missing updated_at"

        # Verify date is today
        assert result["cost_date"] == date.today().isoformat(), f"Expected today's date, got {result['cost_date']}"

        # Verify total is non-negative
        total = Decimal(result["total_cost_usd"])
        assert total >= Decimal("0"), f"total_cost_usd should be non-negative, got {total}"

        print(f"[AC-E2E] Current day cost: date={result['cost_date']}, total=${total}")


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET STATUS AND CONFIGURATION VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFBudget:
    """Test budget status and configuration endpoints via BFF."""

    @pytest.mark.asyncio
    async def test_budget_status_returns_thresholds_and_utilization(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has budget thresholds configured,
        When I call GET /api/admin/costs/budget,
        Then the response contains threshold, total, remaining, and utilization.
        """
        result = await _admin_get(bff_api, "/api/admin/costs/budget")

        # Verify response structure (AC 9.10a.7)
        assert "daily_threshold_usd" in result, "Response missing daily_threshold_usd"
        assert "daily_total_usd" in result, "Response missing daily_total_usd"
        assert "daily_remaining_usd" in result, "Response missing daily_remaining_usd"
        assert "daily_utilization_percent" in result, "Response missing daily_utilization_percent"
        assert "monthly_threshold_usd" in result, "Response missing monthly_threshold_usd"
        assert "current_day" in result, "Response missing current_day"
        assert "current_month" in result, "Response missing current_month"

        # Verify threshold is positive
        daily_threshold = Decimal(result["daily_threshold_usd"])
        assert daily_threshold > Decimal("0"), f"Daily threshold should be positive, got {daily_threshold}"

        print(
            f"[AC-E2E] Budget: daily=${result['daily_total_usd']}/{result['daily_threshold_usd']}, "
            f"utilization={result['daily_utilization_percent']}%"
        )

    @pytest.mark.asyncio
    async def test_configure_budget_updates_thresholds(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service is running,
        When I call PUT /api/admin/costs/budget with new thresholds,
        Then the response confirms the update with new values.
        """
        new_daily = "25.00"
        new_monthly = "500.00"

        result = await _admin_put(
            bff_api,
            "/api/admin/costs/budget",
            data={
                "daily_threshold_usd": new_daily,
                "monthly_threshold_usd": new_monthly,
            },
        )

        # Verify response structure (AC 9.10a.7)
        assert "daily_threshold_usd" in result, "Response missing daily_threshold_usd"
        assert "monthly_threshold_usd" in result, "Response missing monthly_threshold_usd"
        assert "message" in result, "Response missing message"
        assert "updated_at" in result, "Response missing updated_at"

        # Verify thresholds were updated
        assert result["daily_threshold_usd"] == new_daily, (
            f"Expected daily={new_daily}, got {result['daily_threshold_usd']}"
        )
        assert result["monthly_threshold_usd"] == new_monthly, (
            f"Expected monthly={new_monthly}, got {result['monthly_threshold_usd']}"
        )

        print(
            f"[AC-E2E] Budget configured: daily=${result['daily_threshold_usd']}, "
            f"monthly=${result['monthly_threshold_usd']}"
        )

        # Verify the update persists by reading back (compare as Decimal to avoid trailing zero differences)
        status = await _admin_get(bff_api, "/api/admin/costs/budget")
        assert Decimal(status["daily_threshold_usd"]) == Decimal(new_daily), "Budget update not persisted"

        # Restore a reasonable threshold for other tests
        await _admin_put(
            bff_api,
            "/api/admin/costs/budget",
            data={"daily_threshold_usd": "50.00", "monthly_threshold_usd": "1000.00"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY TREND VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFDailyTrend:
    """Test daily cost trend endpoint via BFF."""

    @pytest.mark.asyncio
    async def test_daily_trend_returns_entries(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has historical cost data,
        When I call GET /api/admin/costs/trend/daily,
        Then the response contains entries with date and cost breakdown.
        """
        result = await _admin_get(
            bff_api,
            "/api/admin/costs/trend/daily",
            params={"days": 7},
        )

        # Verify response structure (AC 9.10a.2)
        assert "entries" in result, "Response missing entries"
        assert "data_available_from" in result, "Response missing data_available_from"

        entries = result["entries"]
        assert isinstance(entries, list), "entries should be a list"

        # If entries exist, verify structure
        if entries:
            entry = entries[0]
            assert "entry_date" in entry, "Entry missing entry_date"
            assert "total_cost_usd" in entry, "Entry missing total_cost_usd"

        print(f"[AC-E2E] Daily trend: {len(entries)} entries, from={result['data_available_from']}")


# ═══════════════════════════════════════════════════════════════════════════════
# LLM BREAKDOWN VIA BFF (Story 9.10b - AC 9.10b.2)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFLlmBreakdown:
    """Test LLM cost breakdown endpoints via BFF (Story 9.10b)."""

    @pytest.mark.asyncio
    async def test_llm_by_agent_type_returns_costs(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has LLM cost data,
        When I call GET /api/admin/costs/llm/by-agent-type,
        Then the response contains agent_costs list and total.
        """
        today = date.today().isoformat()
        start_of_month = date.today().replace(day=1).isoformat()

        result = await _admin_get(
            bff_api,
            "/api/admin/costs/llm/by-agent-type",
            params={"start_date": start_of_month, "end_date": today},
        )

        assert "agent_costs" in result, "Response missing agent_costs"
        assert "total_llm_cost_usd" in result, "Response missing total_llm_cost_usd"
        assert isinstance(result["agent_costs"], list), "agent_costs should be a list"

        if result["agent_costs"]:
            entry = result["agent_costs"][0]
            assert "agent_type" in entry, "Entry missing agent_type"
            assert "cost_usd" in entry, "Entry missing cost_usd"

        print(f"[AC-E2E] LLM by agent type: {len(result['agent_costs'])} entries, total=${result['total_llm_cost_usd']}")

    @pytest.mark.asyncio
    async def test_llm_by_model_returns_costs(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has LLM cost data,
        When I call GET /api/admin/costs/llm/by-model,
        Then the response contains model_costs list and total.
        """
        today = date.today().isoformat()
        start_of_month = date.today().replace(day=1).isoformat()

        result = await _admin_get(
            bff_api,
            "/api/admin/costs/llm/by-model",
            params={"start_date": start_of_month, "end_date": today},
        )

        assert "model_costs" in result, "Response missing model_costs"
        assert "total_llm_cost_usd" in result, "Response missing total_llm_cost_usd"
        assert isinstance(result["model_costs"], list), "model_costs should be a list"

        if result["model_costs"]:
            entry = result["model_costs"][0]
            assert "model" in entry, "Entry missing model"
            assert "cost_usd" in entry, "Entry missing cost_usd"

        print(f"[AC-E2E] LLM by model: {len(result['model_costs'])} entries, total=${result['total_llm_cost_usd']}")


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDING BREAKDOWN VIA BFF (Story 9.10b - AC 9.10b.4)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFEmbeddingBreakdown:
    """Test embedding cost breakdown endpoint via BFF (Story 9.10b)."""

    @pytest.mark.asyncio
    async def test_embeddings_by_domain_returns_costs(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given the Platform Cost Service has embedding cost data,
        When I call GET /api/admin/costs/embeddings/by-domain,
        Then the response contains domain_costs list and total.
        """
        today = date.today().isoformat()
        start_of_month = date.today().replace(day=1).isoformat()

        result = await _admin_get(
            bff_api,
            "/api/admin/costs/embeddings/by-domain",
            params={"start_date": start_of_month, "end_date": today},
        )

        assert "domain_costs" in result, "Response missing domain_costs"
        assert "total_embedding_cost_usd" in result, "Response missing total_embedding_cost_usd"
        assert isinstance(result["domain_costs"], list), "domain_costs should be a list"

        if result["domain_costs"]:
            entry = result["domain_costs"][0]
            assert "knowledge_domain" in entry, "Entry missing knowledge_domain"
            assert "cost_usd" in entry, "Entry missing cost_usd"

        print(f"[AC-E2E] Embeddings by domain: {len(result['domain_costs'])} entries, total=${result['total_embedding_cost_usd']}")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlatformCostBFFAuth:
    """Test authorization enforcement on cost endpoints."""

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given a non-admin user,
        When they call any cost endpoint,
        Then they receive 403 Forbidden.
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/costs/summary",
            role="factory_manager",
            params={"start_date": "2026-01-01", "end_date": "2026-01-24"},
        )

        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("[AC-E2E] Non-admin correctly denied access (403)")
