"""E2E Tests: Source Config BFF REST API (Story 9.11b).

Validates the BFF REST layer for source configuration viewer endpoints.
Tests the full flow: BFF HTTP → gRPC via DAPR → Collection Model SourceConfigService.

Acceptance Criteria (AC-E2E):
    Given source configurations exist in MongoDB (from seed data),
    When the BFF receives GET /api/admin/source-configs,
    Then the response contains paginated SourceConfigSummary items
    with at least 5 configs from seed data.

Prerequisites:
    bash scripts/e2e-up.sh --build
    Wait for all services to be healthy before running tests.

Relates to #231
"""

import json
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
        path: Request path (e.g., /api/admin/source-configs)
        params: Optional query parameters

    Returns:
        JSON response body

    Raises:
        AssertionError: If response status is not 200
    """
    response = await bff_api.admin_request_raw("GET", path, params=params)
    assert response.status_code == 200, f"GET {path} returned {response.status_code}: {response.text}"
    return response.json()


# ═══════════════════════════════════════════════════════════════════════════════
# AC-E2E: LIST SOURCE CONFIGS VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestSourceConfigBFFList:
    """Test list source configs endpoint via BFF (AC 9.11b.3)."""

    @pytest.mark.asyncio
    async def test_list_source_configs_returns_paginated_data(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given source configs exist in seed data,
        When I call GET /api/admin/source-configs,
        Then the response contains data array with at least 5 configs.
        """
        result = await _admin_get(bff_api, "/api/admin/source-configs")

        # Verify response structure (AC 9.11b.3)
        assert "data" in result, "Response missing data"
        assert "pagination" in result, "Response missing pagination"

        data = result["data"]
        pagination = result["pagination"]

        # Verify at least 5 configs from seed data
        assert len(data) >= 5, f"Expected at least 5 configs, got {len(data)}"
        assert pagination["total_count"] >= 5, f"Expected total_count >= 5, got {pagination['total_count']}"

        # Verify data item structure
        config = data[0]
        assert "source_id" in config, "Config missing source_id"
        assert "display_name" in config, "Config missing display_name"
        assert "enabled" in config, "Config missing enabled"
        assert "ingestion_mode" in config, "Config missing ingestion_mode"

        print(f"[AC-E2E] List source configs: {len(data)} items, total={pagination['total_count']}")

    @pytest.mark.asyncio
    async def test_list_source_configs_with_pagination(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given source configs exist in seed data,
        When I call GET /api/admin/source-configs with page_size=2,
        Then the response contains 2 items and next_page_token.
        """
        result = await _admin_get(
            bff_api,
            "/api/admin/source-configs",
            params={"page_size": 2},
        )

        data = result["data"]
        pagination = result["pagination"]

        # Should only return 2 items
        assert len(data) == 2, f"Expected 2 items, got {len(data)}"
        assert pagination["page_size"] == 2, f"Expected page_size=2, got {pagination['page_size']}"

        # If there are more configs, next_page_token should be set
        if pagination["total_count"] > 2:
            assert pagination.get("next_page_token"), "Expected next_page_token for pagination"

            # Verify second page has different configs
            second_page = await _admin_get(
                bff_api,
                "/api/admin/source-configs",
                params={"page_size": 2, "page_token": pagination["next_page_token"]},
            )

            first_ids = {c["source_id"] for c in data}
            second_ids = {c["source_id"] for c in second_page["data"]}
            assert first_ids.isdisjoint(second_ids), "Pages should not overlap"

            print(f"[AC-E2E] Pagination: page1={first_ids}, page2={second_ids}")

    @pytest.mark.asyncio
    async def test_list_source_configs_with_enabled_only_filter(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given source configs exist in seed data,
        When I call GET /api/admin/source-configs with enabled_only=true,
        Then all returned configs have enabled=true.
        """
        result = await _admin_get(
            bff_api,
            "/api/admin/source-configs",
            params={"enabled_only": "true"},
        )

        data = result["data"]
        assert len(data) >= 5, f"Expected at least 5 enabled configs, got {len(data)}"

        # All configs should be enabled
        for config in data:
            assert config.get("enabled") is True, f"Config {config['source_id']} should be enabled"

        print(f"[AC-E2E] Enabled filter: {len(data)} enabled configs")

    @pytest.mark.asyncio
    async def test_list_source_configs_with_ingestion_mode_filter(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given source configs exist in seed data,
        When I call GET /api/admin/source-configs with ingestion_mode=blob_trigger,
        Then all returned configs have ingestion_mode=blob_trigger.
        """
        result = await _admin_get(
            bff_api,
            "/api/admin/source-configs",
            params={"ingestion_mode": "blob_trigger"},
        )

        data = result["data"]
        assert len(data) >= 4, f"Expected at least 4 blob_trigger configs, got {len(data)}"

        # All configs should be blob_trigger mode
        for config in data:
            assert config.get("ingestion_mode") == "blob_trigger", (
                f"Config {config['source_id']} has wrong mode: {config.get('ingestion_mode')}"
            )

        print(f"[AC-E2E] Ingestion mode filter: {len(data)} blob_trigger configs")


# ═══════════════════════════════════════════════════════════════════════════════
# AC-E2E: GET SOURCE CONFIG DETAIL VIA BFF
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestSourceConfigBFFDetail:
    """Test get source config detail endpoint via BFF (AC 9.11b.4)."""

    @pytest.mark.asyncio
    async def test_get_source_config_returns_full_detail(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given source configs exist in seed data,
        When I call GET /api/admin/source-configs/{source_id},
        Then the response contains full config with config_json.
        """
        result = await _admin_get(bff_api, "/api/admin/source-configs/e2e-qc-direct-json")

        # Verify response structure (AC 9.11b.4)
        assert result["source_id"] == "e2e-qc-direct-json", "Wrong source_id returned"
        assert result["display_name"] == "E2E QC Direct JSON", "Wrong display_name"
        assert result["enabled"] is True, "Config should be enabled"
        assert "config_json" in result, "Response missing config_json"

        # Verify ingestion_mode is populated (extracted from config_json for consistency)
        assert result["ingestion_mode"] == "blob_trigger", (
            f"Expected ingestion_mode='blob_trigger', got '{result.get('ingestion_mode')}'"
        )

        # Verify config_json is valid JSON with full configuration
        config_json = json.loads(result["config_json"])
        assert config_json["source_id"] == "e2e-qc-direct-json", "config_json source_id mismatch"
        assert "ingestion" in config_json, "config_json missing ingestion section"
        assert "transformation" in config_json, "config_json missing transformation section"
        assert "storage" in config_json, "config_json missing storage section"

        print(f"[AC-E2E] Source config detail: {result['source_id']}, config_json has all sections")

    @pytest.mark.asyncio
    async def test_get_source_config_scheduled_pull(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given a scheduled_pull source config exists,
        When I call GET /api/admin/source-configs/{source_id},
        Then the config_json contains scheduled_pull specific fields.
        """
        result = await _admin_get(bff_api, "/api/admin/source-configs/e2e-weather-api")

        assert result["source_id"] == "e2e-weather-api"
        assert "config_json" in result

        # Verify scheduled_pull specific fields in JSON
        config_json = json.loads(result["config_json"])
        assert config_json["ingestion"]["mode"] == "scheduled_pull"
        assert "iteration" in config_json["ingestion"], "Missing iteration config for scheduled_pull"

        print(f"[AC-E2E] Scheduled pull config: {result['source_id']} has iteration config")

    @pytest.mark.asyncio
    async def test_get_source_config_not_found_returns_404(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given a non-existent source_id,
        When I call GET /api/admin/source-configs/{source_id},
        Then the response is 404 Not Found.
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/source-configs/nonexistent-source-id",
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        error = response.json()
        assert "detail" in error, "Response missing detail"
        assert error["detail"]["code"] == "SOURCE_CONFIG_NOT_FOUND"

        print("[AC-E2E] Not found returns 404 with SOURCE_CONFIG_NOT_FOUND code")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestSourceConfigBFFAuth:
    """Test authorization enforcement on source config endpoints."""

    @pytest.mark.asyncio
    async def test_non_admin_gets_403_on_list(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given a non-admin user (factory_manager),
        When they call GET /api/admin/source-configs,
        Then they receive 403 Forbidden.
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/source-configs",
            role="factory_manager",
        )

        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("[AC-E2E] Non-admin correctly denied access to list (403)")

    @pytest.mark.asyncio
    async def test_non_admin_gets_403_on_detail(
        self,
        bff_api: BFFClient,
        seed_data: Any,
    ):
        """Given a non-admin user (factory_manager),
        When they call GET /api/admin/source-configs/{source_id},
        Then they receive 403 Forbidden.
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/source-configs/e2e-qc-direct-json",
            role="factory_manager",
        )

        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("[AC-E2E] Non-admin correctly denied access to detail (403)")
