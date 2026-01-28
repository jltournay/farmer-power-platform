"""E2E Tests for AI Agent Config Admin API (Story 9.12b).

Tests the BFF REST endpoints for AI agent configuration viewer:
- GET /api/admin/ai-agents - List agent configs
- GET /api/admin/ai-agents/{agent_id} - Get agent config detail
- GET /api/admin/ai-agents/{agent_id}/prompts - List prompts by agent

Uses seed data from tests/e2e/infrastructure/seed/agent_configs.json and prompts.json.

Seed data contains 3 agent configs:
- qc-event-extractor (extractor, active)
- weather-extractor (extractor, active)
- disease-diagnosis (explorer, active)
"""

from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient


async def _admin_get(bff_api: BFFClient, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Helper to make admin GET request and return JSON."""
    response = await bff_api.admin_request_raw("GET", path, params=params)
    assert response.status_code == 200
    return response.json()


async def _admin_get_raw(bff_api: BFFClient, path: str, params: dict[str, Any] | None = None):
    """Helper to make admin GET request and return raw response."""
    return await bff_api.admin_request_raw("GET", path, params=params)


async def _manager_get_raw(bff_api: BFFClient, path: str, params: dict[str, Any] | None = None):
    """Helper to make factory_manager GET request and return raw response."""
    return await bff_api.admin_request_raw("GET", path, role="factory_manager", params=params)


@pytest.mark.e2e
class TestAiAgentList:
    """Tests for GET /api/admin/ai-agents."""

    @pytest.mark.asyncio
    async def test_list_ai_agents_structure(self, bff_api, seed_data):
        """Test list AI agents returns correct response structure."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents")

        # Verify pagination structure
        assert "data" in data
        assert "pagination" in data
        assert "page_size" in data["pagination"]
        assert "total_count" in data["pagination"]

        # Verify data items have expected fields
        assert len(data["data"]) >= 3  # At least 3 from seed data
        for item in data["data"]:
            assert "agent_id" in item
            assert "version" in item
            assert "agent_type" in item
            assert "status" in item
            assert "description" in item
            assert "prompt_count" in item

    @pytest.mark.asyncio
    async def test_list_ai_agents_with_seed_data(self, bff_api, seed_data):
        """Test list AI agents includes all seeded configs."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents")

        agent_ids = [item["agent_id"] for item in data["data"]]
        assert "qc-event-extractor" in agent_ids
        assert "weather-extractor" in agent_ids
        assert "disease-diagnosis" in agent_ids

    @pytest.mark.asyncio
    async def test_list_ai_agents_filter_by_agent_type(self, bff_api, seed_data):
        """Test list AI agents filters by agent_type."""
        # Act - filter for extractors only
        data = await _admin_get(bff_api, "/api/admin/ai-agents", params={"agent_type": "extractor"})

        # All returned items should be extractors
        assert len(data["data"]) >= 2  # qc-event-extractor and weather-extractor
        for item in data["data"]:
            assert item["agent_type"] == "extractor"

    @pytest.mark.asyncio
    async def test_list_ai_agents_filter_by_status(self, bff_api, seed_data):
        """Test list AI agents filters by status."""
        # Act - filter for active only
        data = await _admin_get(bff_api, "/api/admin/ai-agents", params={"status": "active"})

        # All returned items should be active
        assert len(data["data"]) >= 3  # All seed configs are active
        for item in data["data"]:
            assert item["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_ai_agents_pagination(self, bff_api, seed_data):
        """Test list AI agents pagination works correctly."""
        # Act - First page with small page_size
        data1 = await _admin_get(bff_api, "/api/admin/ai-agents", params={"page_size": 2})

        # Assert first page
        assert len(data1["data"]) == 2
        assert data1["pagination"]["total_count"] >= 3

        # If there are more results, next_page_token should be set
        if data1["pagination"]["total_count"] > 2:
            assert data1["pagination"]["next_page_token"]

            # Act - Second page
            token = data1["pagination"]["next_page_token"]
            data2 = await _admin_get(
                bff_api,
                "/api/admin/ai-agents",
                params={"page_size": 2, "page_token": token},
            )

            # Assert second page has different configs
            first_ids = {a["agent_id"] for a in data1["data"]}
            second_ids = {a["agent_id"] for a in data2["data"]}
            assert first_ids.isdisjoint(second_ids), "Pages should not overlap"


@pytest.mark.e2e
class TestAiAgentDetail:
    """Tests for GET /api/admin/ai-agents/{agent_id}."""

    @pytest.mark.asyncio
    async def test_ai_agent_detail_loads(self, bff_api, seed_data):
        """Test AI agent detail loads successfully."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        assert data["agent_id"] == "qc-event-extractor"
        assert data["version"] == "1.0.0"
        assert data["agent_type"] == "extractor"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_ai_agent_detail_has_config_json(self, bff_api, seed_data):
        """Test AI agent detail includes config_json."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        assert "config_json" in data
        assert data["config_json"]  # Should not be empty

        # config_json should be a valid JSON string
        import json

        config = json.loads(data["config_json"])
        assert config["agent_id"] == "qc-event-extractor"

    @pytest.mark.asyncio
    async def test_ai_agent_detail_has_prompts(self, bff_api, seed_data):
        """Test AI agent detail includes linked prompts."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        assert "prompts" in data
        assert len(data["prompts"]) >= 1

        # Verify prompt structure
        prompt = data["prompts"][0]
        assert "id" in prompt
        assert "prompt_id" in prompt
        assert "agent_id" in prompt
        assert prompt["agent_id"] == "qc-event-extractor"
        assert "version" in prompt
        assert "status" in prompt

    @pytest.mark.asyncio
    async def test_ai_agent_detail_has_timestamps(self, bff_api, seed_data):
        """Test AI agent detail includes timestamps."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_ai_agent_detail_explorer_type(self, bff_api, seed_data):
        """Test AI agent detail for explorer type."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/disease-diagnosis")

        assert data["agent_id"] == "disease-diagnosis"
        assert data["agent_type"] == "explorer"

    @pytest.mark.asyncio
    async def test_ai_agent_detail_404_not_found(self, bff_api, seed_data):
        """Test AI agent detail returns 404 for unknown agent."""
        # Act
        response = await _admin_get_raw(bff_api, "/api/admin/ai-agents/nonexistent-agent")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "AGENT_CONFIG_NOT_FOUND"


@pytest.mark.e2e
class TestAiAgentPrompts:
    """Tests for GET /api/admin/ai-agents/{agent_id}/prompts."""

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_structure(self, bff_api, seed_data):
        """Test list prompts by agent returns correct structure."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor/prompts")

        assert "data" in data
        assert "total_count" in data
        assert data["total_count"] >= 1

        # Verify prompt structure
        prompt = data["data"][0]
        assert "id" in prompt
        assert "prompt_id" in prompt
        assert "agent_id" in prompt
        assert "version" in prompt
        assert "status" in prompt
        assert "author" in prompt

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_all_linked(self, bff_api, seed_data):
        """Test all returned prompts belong to the agent."""
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor/prompts")

        for prompt in data["data"]:
            assert prompt["agent_id"] == "qc-event-extractor"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_with_status_filter(self, bff_api, seed_data):
        """Test list prompts filters by status."""
        # Act
        data = await _admin_get(
            bff_api,
            "/api/admin/ai-agents/qc-event-extractor/prompts",
            params={"status": "active"},
        )

        for prompt in data["data"]:
            assert prompt["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_empty_for_unknown(self, bff_api, seed_data):
        """Test list prompts returns empty list for unknown agent.

        Note: The AI Model service returns an empty list for non-existent agents
        rather than a 404, which is a valid design choice for listing operations.
        """
        # Act
        data = await _admin_get(bff_api, "/api/admin/ai-agents/nonexistent-agent/prompts")

        # Assert - Returns empty list since agent doesn't exist
        assert data["data"] == []
        assert data["total_count"] == 0


@pytest.mark.e2e
class TestAiAgentAuthorization:
    """Tests for authorization requirements."""

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_ai_agents(self, bff_api, seed_data):
        """Test non-admin cannot list AI agents."""
        # Act - Use factory_manager token instead of platform_admin
        response = await _manager_get_raw(bff_api, "/api/admin/ai-agents")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_get_ai_agent_detail(self, bff_api, seed_data):
        """Test non-admin cannot get AI agent detail."""
        # Act
        response = await _manager_get_raw(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_prompts(self, bff_api, seed_data):
        """Test non-admin cannot list prompts."""
        # Act
        response = await _manager_get_raw(bff_api, "/api/admin/ai-agents/qc-event-extractor/prompts")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, bff_api, seed_data):
        """Test unauthenticated request is rejected.

        Note: The BFF returns 403 Forbidden for unauthenticated requests
        (the auth middleware checks role first, rejecting with 403).
        """
        # Act - No auth header (use internal client directly)
        response = await bff_api.client.get("/api/admin/ai-agents")

        # Assert - Returns 403 (forbidden) for unauthenticated requests
        assert response.status_code == 403


@pytest.mark.e2e
class TestAiAgentUIIntegration:
    """Tests for UI integration flows."""

    @pytest.mark.asyncio
    async def test_list_to_detail_flow(self, bff_api, seed_data):
        """Test list -> detail navigation flow."""
        # Step 1: List AI agents
        list_data = await _admin_get(bff_api, "/api/admin/ai-agents")

        # Step 2: Get detail for first agent
        first_agent = list_data["data"][0]
        detail_data = await _admin_get(bff_api, f"/api/admin/ai-agents/{first_agent['agent_id']}")

        # Assert detail matches list item
        assert detail_data["agent_id"] == first_agent["agent_id"]
        assert detail_data["version"] == first_agent["version"]
        assert detail_data["agent_type"] == first_agent["agent_type"]

    @pytest.mark.asyncio
    async def test_detail_to_prompts_flow(self, bff_api, seed_data):
        """Test detail -> prompts navigation flow."""
        # Step 1: Get agent detail
        detail_data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor")

        # Detail should include prompts inline
        assert len(detail_data["prompts"]) >= 1

        # Step 2: Get prompts endpoint should return same prompts
        prompts_data = await _admin_get(bff_api, "/api/admin/ai-agents/qc-event-extractor/prompts")

        # Same prompts should be returned
        assert len(prompts_data["data"]) >= 1
        detail_prompt_ids = {p["id"] for p in detail_data["prompts"]}
        prompts_endpoint_ids = {p["id"] for p in prompts_data["data"]}
        assert detail_prompt_ids == prompts_endpoint_ids

    @pytest.mark.asyncio
    async def test_filter_then_detail_flow(self, bff_api, seed_data):
        """Test filter list -> detail flow."""
        # Step 1: List with filter
        list_data = await _admin_get(bff_api, "/api/admin/ai-agents", params={"agent_type": "explorer"})

        # Step 2: Get detail for filtered agent
        assert len(list_data["data"]) >= 1
        explorer = list_data["data"][0]
        assert explorer["agent_type"] == "explorer"

        detail_data = await _admin_get(bff_api, f"/api/admin/ai-agents/{explorer['agent_id']}")
        assert detail_data["agent_type"] == "explorer"
