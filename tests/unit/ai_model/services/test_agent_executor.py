"""Unit tests for AgentExecutor.

Story 0.75.16b: Event Subscriber Workflow Wiring

Tests for:
- AgentExecutor execute flow
- Error handling (config not found, workflow failure)
- Result event building
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.domain.agent_config import AgentType
from ai_model.services.agent_executor import AgentExecutor
from fp_common.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    EntityLinkage,
    ExtractorAgentResult,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_config_cache() -> MagicMock:
    """Mock agent config cache."""
    cache = MagicMock()
    cache.get = AsyncMock()
    return cache


@pytest.fixture
def mock_prompt_cache() -> MagicMock:
    """Mock prompt cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def mock_workflow_service() -> MagicMock:
    """Mock workflow execution service."""
    service = MagicMock()
    service.execute = AsyncMock()
    return service


@pytest.fixture
def mock_event_publisher() -> MagicMock:
    """Mock event publisher."""
    publisher = MagicMock()
    publisher.publish_agent_completed = AsyncMock()
    publisher.publish_agent_failed = AsyncMock()
    return publisher


@pytest.fixture
def agent_executor(
    mock_agent_config_cache: MagicMock,
    mock_prompt_cache: MagicMock,
    mock_workflow_service: MagicMock,
    mock_event_publisher: MagicMock,
) -> AgentExecutor:
    """Create AgentExecutor with mocked dependencies."""
    return AgentExecutor(
        agent_config_cache=mock_agent_config_cache,
        prompt_cache=mock_prompt_cache,
        workflow_service=mock_workflow_service,
        event_publisher=mock_event_publisher,
    )


@pytest.fixture
def sample_agent_request() -> AgentRequestEvent:
    """Sample agent request event."""
    return AgentRequestEvent(
        request_id="req-test-123",
        agent_id="qc-event-extractor",
        linkage=EntityLinkage(farmer_id="farmer-456"),
        input_data={"doc_content": "Sample text"},
        source="collection-model",
    )


@pytest.fixture
def mock_agent_config() -> MagicMock:
    """Mock agent config object (already parsed Pydantic model)."""
    config = MagicMock()
    config.agent_id = "qc-event-extractor"
    config.type = AgentType.EXTRACTOR
    config.mcp_sources = []
    config.model_dump.return_value = {
        "agent_id": "qc-event-extractor",
        "type": "extractor",
        "llm": {"model": "anthropic/claude-3-haiku"},
    }
    return config


# =============================================================================
# Execute Tests
# =============================================================================


class TestAgentExecutorExecute:
    """Tests for AgentExecutor.execute()."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test successful execution returns AgentCompletedEvent."""
        # Setup - mock internal _get_agent_config to return parsed config
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {"event_date": "2024-01-15", "event_type": "delivery"},
                "model_used": "anthropic/claude-3-haiku",
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentCompletedEvent)
        assert result.request_id == sample_agent_request.request_id
        assert result.agent_id == sample_agent_request.agent_id
        assert result.linkage == sample_agent_request.linkage
        assert isinstance(result.result, ExtractorAgentResult)
        assert result.result.extracted_fields == {"event_date": "2024-01-15", "event_type": "delivery"}

    @pytest.mark.asyncio
    async def test_execute_config_not_found(
        self,
        agent_executor: AgentExecutor,
        sample_agent_request: AgentRequestEvent,
    ) -> None:
        """Test execution returns AgentFailedEvent when config not found."""
        # Setup - mock internal _get_agent_config to return None
        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=None)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentFailedEvent)
        assert result.request_id == sample_agent_request.request_id
        assert result.error_type == "config_not_found"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_workflow_failure(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test execution returns AgentFailedEvent when workflow fails."""
        # Setup
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": False,
                "error_message": "LLM call failed: rate limited",
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentFailedEvent)
        assert result.error_type == "workflow_failed"
        assert "rate limited" in result.error_message


# =============================================================================
# Execute and Publish Tests
# =============================================================================


class TestAgentExecutorExecuteAndPublish:
    """Tests for AgentExecutor.execute_and_publish()."""

    @pytest.mark.asyncio
    async def test_execute_and_publish_success(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        mock_event_publisher: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test successful execution publishes AgentCompletedEvent."""
        # Setup
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {"extracted": "data"},
                "model_used": "anthropic/claude-3-haiku",
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute_and_publish(sample_agent_request)

        # Verify
        assert isinstance(result, AgentCompletedEvent)
        mock_event_publisher.publish_agent_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_and_publish_failure(
        self,
        agent_executor: AgentExecutor,
        mock_event_publisher: MagicMock,
        sample_agent_request: AgentRequestEvent,
    ) -> None:
        """Test failed execution publishes AgentFailedEvent."""
        # Setup
        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=None)):
            # Execute
            result = await agent_executor.execute_and_publish(sample_agent_request)

        # Verify
        assert isinstance(result, AgentFailedEvent)
        mock_event_publisher.publish_agent_failed.assert_called_once()


# =============================================================================
# Result Building Tests
# =============================================================================


class TestAgentExecutorResultBuilding:
    """Tests for AgentExecutor result building methods."""

    @pytest.mark.asyncio
    async def test_build_extractor_result(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test extractor result is built correctly."""
        # Setup
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {"field1": "value1"},
                "validation_warnings": ["Warning 1"],
                "validation_errors": [],
                "normalization_applied": True,
                "model_used": "test-model",
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentCompletedEvent)
        assert isinstance(result.result, ExtractorAgentResult)
        assert result.result.extracted_fields == {"field1": "value1"}
        assert result.result.validation_warnings == ["Warning 1"]
        assert result.result.normalization_applied is True

    @pytest.mark.asyncio
    async def test_execution_time_tracked(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test execution time is tracked."""
        # Setup
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {},
                "model_used": "test-model",
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentCompletedEvent)
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_cost_tracked_when_present(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
        sample_agent_request: AgentRequestEvent,
        mock_agent_config: MagicMock,
    ) -> None:
        """Test cost is tracked when present in workflow result."""
        # Setup
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {},
                "model_used": "test-model",
                "cost_usd": 0.00025,
            }
        )

        with patch.object(agent_executor, "_get_agent_config", AsyncMock(return_value=mock_agent_config)):
            # Execute
            result = await agent_executor.execute(sample_agent_request)

        # Verify
        assert isinstance(result, AgentCompletedEvent)
        assert result.cost_usd == Decimal("0.00025")
