"""E2E Tests for AgentConfigService gRPC (Story 9.12a).

Tests the read-only gRPC service for agent config and prompt queries.
Uses seed data from tests/e2e/infrastructure/seed/agent_configs.json and prompts.json.

Seed data contains 3 agent configs:
- qc-event-extractor (extractor, active)
- weather-extractor (extractor, active)
- disease-diagnosis (explorer, active)

Seed data contains 3 prompts:
- qc-event-extractor:1.0.0 (linked to qc-event-extractor)
- weather-extractor:1.0.0 (linked to weather-extractor)
- disease-diagnosis:1.0.0 (linked to disease-diagnosis)
"""

import json

import grpc
import pytest

from tests.e2e.helpers.mcp_clients import AiModelServiceError


@pytest.mark.e2e
class TestListAgentConfigs:
    """Tests for ListAgentConfigs RPC."""

    @pytest.mark.asyncio
    async def test_list_agent_configs_returns_all(self, ai_model_service, seed_data):
        """Test ListAgentConfigs returns all configs from seed data."""
        # Act
        result = await ai_model_service.list_agent_configs()

        # Assert
        assert "agents" in result
        assert "total_count" in result
        assert result["total_count"] >= 3  # At least 3 from seed data

        # Verify we got configs with expected fields
        agents = result["agents"]
        assert len(agents) >= 3
        for agent in agents:
            assert "agent_id" in agent
            assert "version" in agent
            assert "agent_type" in agent
            assert "status" in agent
            assert "description" in agent

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_type_filter(self, ai_model_service, seed_data):
        """Test ListAgentConfigs filters by agent_type."""
        # Act - filter for extractors only
        result = await ai_model_service.list_agent_configs(agent_type="extractor")

        # Assert
        agents = result.get("agents", [])
        assert len(agents) >= 2  # qc-event-extractor and weather-extractor

        # All returned agents should be extractors
        for agent in agents:
            assert agent.get("agent_type") == "extractor"

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_explorer_filter(self, ai_model_service, seed_data):
        """Test ListAgentConfigs filters by agent_type=explorer."""
        # Act - filter for explorers only
        result = await ai_model_service.list_agent_configs(agent_type="explorer")

        # Assert
        agents = result.get("agents", [])
        assert len(agents) >= 1  # disease-diagnosis

        # All returned agents should be explorers
        for agent in agents:
            assert agent.get("agent_type") == "explorer"

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_status_filter(self, ai_model_service, seed_data):
        """Test ListAgentConfigs filters by status."""
        # Act - filter for active only
        result = await ai_model_service.list_agent_configs(status="active")

        # Assert
        agents = result.get("agents", [])
        assert len(agents) >= 3  # All seed configs are active

        # All returned agents should be active
        for agent in agents:
            assert agent.get("status") == "active"

    @pytest.mark.asyncio
    async def test_list_agent_configs_pagination(self, ai_model_service, seed_data):
        """Test ListAgentConfigs pagination works correctly."""
        # Act - First page with small page_size
        first_page = await ai_model_service.list_agent_configs(page_size=2)

        # Assert first page
        assert len(first_page.get("agents", [])) == 2
        assert first_page["total_count"] >= 3

        # If there are more results, next_page_token should be set
        if first_page["total_count"] > 2:
            assert first_page.get("next_page_token")

            # Act - Second page
            second_page = await ai_model_service.list_agent_configs(
                page_size=2,
                page_token=first_page["next_page_token"],
            )

            # Assert second page has different configs
            first_ids = {a["agent_id"] for a in first_page["agents"]}
            second_ids = {a["agent_id"] for a in second_page["agents"]}
            assert first_ids.isdisjoint(second_ids), "Pages should not overlap"

    @pytest.mark.asyncio
    async def test_list_agent_configs_includes_prompt_count(self, ai_model_service, seed_data):
        """Test ListAgentConfigs includes prompt_count field."""
        # Act
        result = await ai_model_service.list_agent_configs()

        # Assert - each agent should have prompt_count
        agents = result.get("agents", [])
        for agent in agents:
            assert "prompt_count" in agent
            # Seed data has 1 prompt per agent
            if agent["agent_id"] in ["qc-event-extractor", "weather-extractor", "disease-diagnosis"]:
                assert agent["prompt_count"] >= 1


@pytest.mark.e2e
class TestGetAgentConfig:
    """Tests for GetAgentConfig RPC."""

    @pytest.mark.asyncio
    async def test_get_agent_config_returns_full_json(self, ai_model_service, seed_data):
        """Test GetAgentConfig returns full config with JSON."""
        # Act
        result = await ai_model_service.get_agent_config("qc-event-extractor")

        # Assert
        assert result["agent_id"] == "qc-event-extractor"
        assert result["version"] == "1.0.0"
        assert result["agent_type"] == "extractor"
        assert result["status"] == "active"
        assert "config_json" in result

        # Verify config_json is valid JSON with full config
        config_json = json.loads(result["config_json"])
        assert config_json["agent_id"] == "qc-event-extractor"
        assert "llm" in config_json
        assert config_json["llm"]["model"] == "anthropic/claude-3-haiku"

    @pytest.mark.asyncio
    async def test_get_agent_config_explorer_type(self, ai_model_service, seed_data):
        """Test GetAgentConfig for explorer type config."""
        # Act
        result = await ai_model_service.get_agent_config("disease-diagnosis")

        # Assert
        assert result["agent_id"] == "disease-diagnosis"
        assert result["agent_type"] == "explorer"
        assert "config_json" in result

        # Verify explorer-specific fields in JSON
        config_json = json.loads(result["config_json"])
        assert config_json["type"] == "explorer"
        assert "rag" in config_json
        assert config_json["rag"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_agent_config_includes_prompts(self, ai_model_service, seed_data):
        """Test GetAgentConfig returns linked prompts."""
        # Act
        result = await ai_model_service.get_agent_config("qc-event-extractor")

        # Assert
        assert "prompts" in result
        prompts = result["prompts"]
        assert len(prompts) >= 1

        # Verify prompt summary fields
        prompt = prompts[0]
        assert "prompt_id" in prompt
        assert "agent_id" in prompt
        assert prompt["agent_id"] == "qc-event-extractor"
        assert "version" in prompt
        assert "status" in prompt

    @pytest.mark.asyncio
    async def test_get_agent_config_not_found(self, ai_model_service, seed_data):
        """Test GetAgentConfig returns NOT_FOUND for invalid agent_id."""
        # Act & Assert
        with pytest.raises(AiModelServiceError) as exc_info:
            await ai_model_service.get_agent_config("nonexistent-agent-id")

        assert exc_info.value.code == grpc.StatusCode.NOT_FOUND
        assert "not found" in exc_info.value.details.lower()

    @pytest.mark.asyncio
    async def test_get_agent_config_empty_agent_id(self, ai_model_service, seed_data):
        """Test GetAgentConfig returns INVALID_ARGUMENT for empty agent_id."""
        # Act & Assert
        with pytest.raises(AiModelServiceError) as exc_info:
            await ai_model_service.get_agent_config("")

        assert exc_info.value.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.e2e
class TestListPromptsByAgent:
    """Tests for ListPromptsByAgent RPC."""

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_returns_prompts(self, ai_model_service, seed_data):
        """Test ListPromptsByAgent returns prompts for an agent."""
        # Act
        result = await ai_model_service.list_prompts_by_agent("qc-event-extractor")

        # Assert
        assert "prompts" in result
        assert "total_count" in result
        assert result["total_count"] >= 1

        prompts = result["prompts"]
        assert len(prompts) >= 1

        # All prompts should belong to the requested agent
        for prompt in prompts:
            assert prompt["agent_id"] == "qc-event-extractor"
            assert "prompt_id" in prompt
            assert "version" in prompt
            assert "status" in prompt

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_with_status_filter(self, ai_model_service, seed_data):
        """Test ListPromptsByAgent filters by status."""
        # Act - filter for active only
        result = await ai_model_service.list_prompts_by_agent("qc-event-extractor", status="active")

        # Assert
        prompts = result.get("prompts", [])
        # All returned prompts should be active
        for prompt in prompts:
            assert prompt.get("status") == "active"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_empty_for_unknown(self, ai_model_service, seed_data):
        """Test ListPromptsByAgent returns empty for agent with no prompts."""
        # Act - query for an agent that doesn't exist (won't error, just returns empty)
        result = await ai_model_service.list_prompts_by_agent("unknown-agent-no-prompts")

        # Assert
        assert result.get("total_count", 0) == 0
        assert len(result.get("prompts", [])) == 0

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_empty_agent_id(self, ai_model_service, seed_data):
        """Test ListPromptsByAgent returns INVALID_ARGUMENT for empty agent_id."""
        # Act & Assert
        with pytest.raises(AiModelServiceError) as exc_info:
            await ai_model_service.list_prompts_by_agent("")

        assert exc_info.value.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.e2e
class TestAgentConfigServiceConnectivity:
    """Verify AgentConfigService is accessible."""

    @pytest.mark.asyncio
    async def test_agent_config_service_connectivity(self, ai_model_service):
        """Verify AgentConfigService is reachable via gRPC."""
        # Act - try to list configs (uses AgentConfigService)
        result = await ai_model_service.list_agent_configs(page_size=1)

        # Assert - should return a valid response
        assert "agents" in result or "total_count" in result
        print("AgentConfigService gRPC: OK")
