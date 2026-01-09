"""Integration tests for Extractor workflow with AgentExecutor.

Story 0.75.17: Extractor Agent Implementation

These tests verify the complete execution flow from AgentRequestEvent
through ExtractorWorkflow to AgentCompletedEvent using mocked LLM.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ErrorHandlingConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
)
from ai_model.services.agent_executor import AgentExecutor
from ai_model.workflows.extractor import ExtractorWorkflow
from ai_model.workflows.states.extractor import ExtractorState
from fp_common.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    EntityLinkage,
    ExtractorAgentResult,
)


@pytest.fixture
def qc_extractor_config() -> ExtractorConfig:
    """QC Event Extractor agent configuration."""
    return ExtractorConfig(
        id="qc-event-extractor:1.0.0",
        agent_id="qc-event-extractor",
        version="1.0.0",
        description="Extracts structured QC data from QC Analyzer END_BAG events",
        input=InputConfig(
            event="collection.document.received",
            schema={"type": "object", "required": ["raw_data"]},
        ),
        output=OutputConfig(
            event="ai.extraction.complete",
            schema={"type": "object"},
        ),
        llm=LLMConfig(
            model="anthropic/claude-3-haiku",
            temperature=0.1,
            max_tokens=500,
        ),
        extraction_schema={
            "required_fields": [
                "grade",
                "quality_score",
                "leaf_count",
                "moisture_percent",
                "extraction_confidence",
            ],
            "optional_fields": ["farmer_id", "defects", "validation_warnings"],
            "field_types": {
                "farmer_id": "string",
                "grade": "string",
                "quality_score": "number",
                "leaf_count": "integer",
                "moisture_percent": "number",
                "defects": "array",
                "validation_warnings": "array",
                "extraction_confidence": "number",
            },
        },
        normalization_rules=[
            {"field": "farmer_id", "transform": "uppercase"},
            {"field": "grade", "transform": "uppercase"},
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="test"),
    )


@pytest.fixture
def standard_extraction_output() -> dict[str, Any]:
    """Standard successful extraction output."""
    return {
        "farmer_id": "WM-4521",
        "grade": "B",
        "quality_score": 78.0,
        "leaf_count": 150,
        "moisture_percent": 72.5,
        "defects": ["yellow_leaves", "insect_damage"],
        "validation_warnings": [],
        "extraction_confidence": 0.95,
    }


@pytest.fixture
def mock_llm_gateway(standard_extraction_output: dict[str, Any]) -> MagicMock:
    """Mock LLM gateway returning standard extraction output."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": json.dumps(standard_extraction_output),
            "model": "anthropic/claude-3-haiku",
            "tokens_in": 150,
            "tokens_out": 75,
        }
    )
    return gateway


class TestExtractorWorkflowIntegration:
    """Integration tests for ExtractorWorkflow."""

    @pytest.mark.asyncio
    async def test_complete_extraction_flow(
        self,
        qc_extractor_config: ExtractorConfig,
        mock_llm_gateway: MagicMock,
        standard_extraction_output: dict[str, Any],
    ) -> None:
        """Test complete extraction flow from input to output."""
        workflow = ExtractorWorkflow(llm_gateway=mock_llm_gateway)

        input_data = {
            "source": "qc-analyzer",
            "event_type": "END_BAG",
            "timestamp": "2026-01-09T10:30:00Z",
            "raw_data": {
                "farmer_code": "WM-4521",
                "leaf_count": 150,
                "moisture_percent": 72.5,
                "defects": ["yellow_leaves", "insect_damage"],
                "assigned_grade": "B",
            },
        }

        initial_state: ExtractorState = {
            "input_data": input_data,
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "Extract from: {{raw_data}}",
            "correlation_id": "test-corr-123",
        }

        result = await workflow.execute(initial_state)

        # Verify success
        assert result["success"] is True
        assert result.get("error_message") is None

        # Verify output
        output = result["output"]
        assert output["farmer_id"] == "WM-4521"
        assert output["grade"] == "B"
        assert output["quality_score"] == 78.0
        assert output["leaf_count"] == 150
        assert output["moisture_percent"] == 72.5

        # Verify LLM was called
        mock_llm_gateway.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_extraction_with_missing_farmer_id(
        self,
        qc_extractor_config: ExtractorConfig,
    ) -> None:
        """Test extraction when farmer_id is null.

        When farmer_id is missing from the input, the LLM should return
        farmer_id: null with a validation_warning. The workflow accepts
        null values for all types (represents missing/unknown value).
        """
        expected_output = {
            "farmer_id": None,
            "grade": "REJECT",
            "quality_score": 25.0,
            "leaf_count": 80,
            "moisture_percent": 85.0,
            "defects": ["wilting", "brown_spots"],
            "validation_warnings": ["missing_farmer_id"],
            "extraction_confidence": 0.90,
        }

        gateway = MagicMock()
        gateway.complete = AsyncMock(
            return_value={
                "content": json.dumps(expected_output),
                "model": "anthropic/claude-3-haiku",
                "tokens_in": 150,
                "tokens_out": 75,
            }
        )

        workflow = ExtractorWorkflow(llm_gateway=gateway)

        input_data = {
            "raw_data": {
                "leaf_count": 80,
                "moisture_percent": 85.0,
                "defects": ["wilting", "brown_spots"],
                "assigned_grade": "Reject",
            }
        }

        initial_state: ExtractorState = {
            "input_data": input_data,
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "",
            "correlation_id": "test-missing-farmer",
        }

        result = await workflow.execute(initial_state)

        # Should succeed - null is valid for optional fields
        assert result["success"] is True
        assert result["output"]["farmer_id"] is None
        assert result["output"]["grade"] == "REJECT"
        assert "missing_farmer_id" in result["output"]["validation_warnings"]

    @pytest.mark.asyncio
    async def test_extraction_normalization(
        self,
        qc_extractor_config: ExtractorConfig,
    ) -> None:
        """Test normalization rules are applied (uppercase farmer_id and grade)."""
        # LLM returns lowercase, normalization should uppercase
        llm_output = {
            "farmer_id": "pk-1357",  # lowercase
            "grade": "c",  # lowercase
            "quality_score": 58.0,
            "leaf_count": 95,
            "moisture_percent": 78.5,
            "defects": ["brown_spots"],
            "validation_warnings": [],
            "extraction_confidence": 0.89,
        }

        gateway = MagicMock()
        gateway.complete = AsyncMock(
            return_value={
                "content": json.dumps(llm_output),
                "model": "anthropic/claude-3-haiku",
                "tokens_in": 150,
                "tokens_out": 75,
            }
        )

        workflow = ExtractorWorkflow(llm_gateway=gateway)

        initial_state: ExtractorState = {
            "input_data": {"raw_data": {"farmer_code": "pk-1357", "assigned_grade": "c"}},
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "",
            "correlation_id": "test-normalize",
        }

        result = await workflow.execute(initial_state)

        assert result["success"] is True
        # Normalization should uppercase these
        assert result["output"]["farmer_id"] == "PK-1357"
        assert result["output"]["grade"] == "C"

    @pytest.mark.asyncio
    async def test_extraction_llm_error_handling(
        self,
        qc_extractor_config: ExtractorConfig,
    ) -> None:
        """Test error handling when LLM fails."""
        gateway = MagicMock()
        gateway.complete = AsyncMock(side_effect=Exception("LLM service unavailable"))

        workflow = ExtractorWorkflow(llm_gateway=gateway)

        initial_state: ExtractorState = {
            "input_data": {"raw_data": {"farmer_code": "WM-1234"}},
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "",
            "correlation_id": "test-llm-error",
        }

        result = await workflow.execute(initial_state)

        assert result["success"] is False
        assert "LLM service unavailable" in result.get("error_message", "")

    @pytest.mark.asyncio
    async def test_extraction_invalid_json_response(
        self,
        qc_extractor_config: ExtractorConfig,
    ) -> None:
        """Test handling of invalid JSON from LLM."""
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            return_value={
                "content": "This is not valid JSON at all",
                "model": "anthropic/claude-3-haiku",
                "tokens_in": 100,
                "tokens_out": 50,
            }
        )

        workflow = ExtractorWorkflow(llm_gateway=gateway)

        initial_state: ExtractorState = {
            "input_data": {"raw_data": {"farmer_code": "WM-1234"}},
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "",
            "correlation_id": "test-invalid-json",
        }

        result = await workflow.execute(initial_state)

        # Should fail validation due to empty extraction
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_extraction_empty_input_data(
        self,
        qc_extractor_config: ExtractorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test extraction with empty input data."""
        workflow = ExtractorWorkflow(llm_gateway=mock_llm_gateway)

        initial_state: ExtractorState = {
            "input_data": {},  # Empty
            "agent_id": "qc-event-extractor",
            "agent_config": qc_extractor_config,
            "prompt_template": "",
            "correlation_id": "test-empty-input",
        }

        result = await workflow.execute(initial_state)

        assert result["success"] is False
        assert "no input" in result.get("error_message", "").lower()


class TestAgentExecutorWithExtractor:
    """Integration tests for AgentExecutor with ExtractorWorkflow."""

    @pytest.fixture
    def mock_agent_config_cache(self, qc_extractor_config: ExtractorConfig) -> MagicMock:
        """Mock agent config cache that returns qc_extractor_config."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=qc_extractor_config.model_dump())
        return cache

    @pytest.fixture
    def mock_prompt_cache(self) -> MagicMock:
        """Mock prompt cache."""
        cache = MagicMock()
        cache.get = AsyncMock(
            return_value={
                "template": "Extract QC data from: {{raw_data}}",
            }
        )
        return cache

    @pytest.fixture
    def mock_event_publisher(self) -> MagicMock:
        """Mock event publisher."""
        publisher = MagicMock()
        publisher.publish_agent_completed = AsyncMock()
        publisher.publish_agent_failed = AsyncMock()
        return publisher

    @pytest.fixture
    def mock_workflow_service(self, standard_extraction_output: dict[str, Any]) -> MagicMock:
        """Mock workflow execution service."""
        service = MagicMock()
        service.execute = AsyncMock(
            return_value={
                "success": True,
                "output": standard_extraction_output,
                "model_used": "anthropic/claude-3-haiku",
                "tokens_used": 225,
            }
        )
        return service

    @pytest.fixture
    def agent_executor(
        self,
        mock_agent_config_cache: MagicMock,
        mock_prompt_cache: MagicMock,
        mock_workflow_service: MagicMock,
        mock_event_publisher: MagicMock,
    ) -> AgentExecutor:
        """Create AgentExecutor with all mocks."""
        return AgentExecutor(
            agent_config_cache=mock_agent_config_cache,
            prompt_cache=mock_prompt_cache,
            workflow_service=mock_workflow_service,
            event_publisher=mock_event_publisher,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_completed_event(
        self,
        agent_executor: AgentExecutor,
    ) -> None:
        """Test AgentExecutor.execute returns AgentCompletedEvent on success."""
        request = AgentRequestEvent(
            request_id="req-123",
            agent_id="qc-event-extractor",
            linkage=EntityLinkage(farmer_id="WM-4521"),
            input_data={
                "raw_data": {
                    "farmer_code": "WM-4521",
                    "assigned_grade": "B",
                }
            },
            source="collection-model",
        )

        result = await agent_executor.execute(request)

        assert isinstance(result, AgentCompletedEvent)
        assert result.request_id == "req-123"
        assert result.agent_id == "qc-event-extractor"
        assert isinstance(result.result, ExtractorAgentResult)
        assert result.result.extracted_fields["farmer_id"] == "WM-4521"

    @pytest.mark.asyncio
    async def test_execute_and_publish_publishes_completed(
        self,
        agent_executor: AgentExecutor,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Test AgentExecutor.execute_and_publish publishes result."""
        request = AgentRequestEvent(
            request_id="req-456",
            agent_id="qc-event-extractor",
            linkage=EntityLinkage(farmer_id="WM-1234"),
            input_data={"raw_data": {"farmer_code": "WM-1234"}},
            source="collection-model",
        )

        result = await agent_executor.execute_and_publish(request)

        assert isinstance(result, AgentCompletedEvent)
        mock_event_publisher.publish_agent_completed.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_execute_config_not_found_returns_failed(
        self,
        agent_executor: AgentExecutor,
        mock_agent_config_cache: MagicMock,
    ) -> None:
        """Test AgentExecutor returns failed event when config not found."""
        mock_agent_config_cache.get = AsyncMock(return_value=None)

        request = AgentRequestEvent(
            request_id="req-789",
            agent_id="nonexistent-agent",
            linkage=EntityLinkage(farmer_id="WM-1234"),
            input_data={},
            source="test",
        )

        result = await agent_executor.execute(request)

        assert isinstance(result, AgentFailedEvent)
        assert result.error_type == "config_not_found"
        assert "nonexistent-agent" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_workflow_failure_returns_failed(
        self,
        agent_executor: AgentExecutor,
        mock_workflow_service: MagicMock,
    ) -> None:
        """Test AgentExecutor returns failed event when workflow fails."""
        mock_workflow_service.execute = AsyncMock(
            return_value={
                "success": False,
                "error_message": "Validation failed: missing required field",
            }
        )

        request = AgentRequestEvent(
            request_id="req-999",
            agent_id="qc-event-extractor",
            linkage=EntityLinkage(farmer_id="WM-1234"),
            input_data={},
            source="test",
        )

        result = await agent_executor.execute(request)

        assert isinstance(result, AgentFailedEvent)
        assert result.error_type == "workflow_failed"
        assert "Validation failed" in result.error_message
