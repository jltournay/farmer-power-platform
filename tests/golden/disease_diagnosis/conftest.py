"""Test fixtures for Disease Diagnosis Explorer golden sample tests.

Story 0.75.19: Explorer Agent Implementation - Sample Config & Golden Tests

This module provides fixtures for testing the Disease Diagnosis Explorer with mocked LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ErrorHandlingConfig,
    ExplorerConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.workflows.explorer import ExplorerWorkflow

if TYPE_CHECKING:
    from tests.golden.framework import GoldenSampleCollection


@pytest.fixture
def disease_diagnosis_config() -> ExplorerConfig:
    """Disease Diagnosis Explorer agent configuration."""
    return ExplorerConfig(
        id="disease-diagnosis:1.0.0",
        agent_id="disease-diagnosis",
        version="1.0.0",
        description="Diagnoses tea plant diseases from quality events and farmer context using RAG knowledge",
        input=InputConfig(
            event="ai.agent.requested",
            schema={
                "type": "object",
                "required": ["farmer_id", "quality_issues"],
            },
        ),
        output=OutputConfig(
            event="ai.agent.disease-diagnosis.completed",
            schema={"type": "object", "required": ["diagnosis", "recommendations"]},
        ),
        llm=LLMConfig(
            model="anthropic/claude-3-5-sonnet",
            temperature=0.3,
            max_tokens=2000,
        ),
        rag=RAGConfig(
            enabled=True,
            query_template="tea plant disease symptoms: {{quality_issues}} conditions: {{weather_conditions}} region: {{region}}",
            knowledge_domains=["tea-disease", "plant-pathology"],
            top_k=5,
            min_similarity=0.7,
        ),
        mcp_sources=[
            MCPSourceConfig(server="plantation-mcp", tools=["get_farmer", "get_region"]),
            MCPSourceConfig(server="collection-mcp", tools=["get_document"]),
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="dev-story-0.75.19"),
    )


@pytest.fixture
def disease_diagnosis_prompt() -> str:
    """Load Disease Diagnosis prompt template from config file."""
    prompt_file = Path(__file__).parent.parent.parent.parent / "config/prompts/disease-diagnosis.json"
    if prompt_file.exists():
        config = json.loads(prompt_file.read_text())
        return config["content"]["template"]
    return "Diagnose the following quality issues: {{quality_issues}}"


def create_mock_llm_response(expected_output: dict[str, Any]) -> dict[str, Any]:
    """Create a mock LLM response for a given expected output.

    Args:
        expected_output: The expected output from the golden sample.

    Returns:
        Mock LLM response dict.
    """
    return {
        "content": json.dumps(expected_output),
        "model": "anthropic/claude-3-5-sonnet",
        "tokens_in": 500,
        "tokens_out": 300,
    }


@pytest.fixture
def mock_llm_gateway_factory():
    """Factory fixture to create mock LLM gateway with specific response."""

    def _factory(expected_output: dict[str, Any]) -> MagicMock:
        gateway = MagicMock()
        gateway.complete = AsyncMock(return_value=create_mock_llm_response(expected_output))
        return gateway

    return _factory


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Default mock LLM gateway (returns empty response)."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": "{}",
            "model": "anthropic/claude-3-5-sonnet",
            "tokens_in": 100,
            "tokens_out": 50,
        }
    )
    return gateway


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Mock ranking service for RAG retrieval."""
    service = MagicMock()
    service.retrieve = AsyncMock(
        return_value=[
            {
                "content": "Tea blister blight is a fungal disease caused by Exobasidium vexans. It thrives in high humidity conditions.",
                "score": 0.85,
                "metadata": {"domain": "tea-disease"},
            },
            {
                "content": "Nitrogen deficiency in tea plants causes yellowing of older leaves and stunted growth.",
                "score": 0.82,
                "metadata": {"domain": "plant-pathology"},
            },
        ]
    )
    return service


@pytest.fixture
def mock_mcp_integration() -> MagicMock:
    """Mock MCP integration for context fetching."""
    integration = MagicMock()
    integration.fetch_context = AsyncMock(
        return_value={
            "farmer": {"id": "WM-4521", "region": "Kericho-High"},
            "weather": {"last_7_days": {"rainfall_mm": 85, "avg_humidity": 90}},
        }
    )
    return integration


@pytest.fixture
def explorer_workflow(
    mock_llm_gateway: MagicMock,
    mock_ranking_service: MagicMock,
    mock_mcp_integration: MagicMock,
) -> ExplorerWorkflow:
    """Explorer workflow instance with mocked dependencies."""
    return ExplorerWorkflow(
        llm_gateway=mock_llm_gateway,
        ranking_service=mock_ranking_service,
        mcp_integration=mock_mcp_integration,
    )


@pytest.fixture
def golden_samples_path() -> Path:
    """Path to golden samples directory."""
    return Path(__file__).parent


@pytest.fixture
def load_golden_samples(golden_samples_path: Path) -> GoldenSampleCollection:
    """Load golden samples from JSON file."""
    from tests.golden.framework import GoldenSampleCollection

    samples_file = golden_samples_path / "samples.json"
    data = json.loads(samples_file.read_text())
    return GoldenSampleCollection(**data)
