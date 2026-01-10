"""Test fixtures for Weekly Action Plan Generator golden sample tests.

Story 0.75.20: Generator Agent Implementation - Sample Config & Golden Tests

This module provides fixtures for testing the Weekly Action Plan Generator with mocked LLM.
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
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
)

if TYPE_CHECKING:
    from tests.golden.framework import GoldenSampleCollection


@pytest.fixture
def weekly_action_plan_config() -> GeneratorConfig:
    """Weekly Action Plan Generator agent configuration."""
    return GeneratorConfig(
        id="weekly-action-plan:1.0.0",
        agent_id="weekly-action-plan",
        version="1.0.0",
        description="Generates personalized weekly action plans for farmers based on diagnoses and conditions",
        input=InputConfig(
            event="ai.agent.requested",
            schema={
                "type": "object",
                "required": ["farmer_id"],
            },
        ),
        output=OutputConfig(
            event="ai.agent.weekly-action-plan.completed",
            schema={"type": "object", "required": ["action_plan", "summary"]},
        ),
        llm=LLMConfig(
            model="anthropic/claude-3-5-sonnet",
            temperature=0.5,
            max_tokens=3000,
        ),
        rag=RAGConfig(
            enabled=True,
            query_template="tea farming best practices for: {{conditions}} season: {{season}} region: {{region}}",
            knowledge_domains=["tea-cultivation", "regional-context", "action-plan-best-practices"],
            top_k=5,
            min_similarity=0.65,
        ),
        output_format="markdown",
        mcp_sources=[
            MCPSourceConfig(server="plantation-mcp", tools=["get_farmer", "get_region", "get_weather_forecast"]),
            MCPSourceConfig(server="knowledge-mcp", tools=["get_recent_diagnoses"]),
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="dev-story-0.75.20"),
    )


@pytest.fixture
def weekly_action_plan_prompt() -> str:
    """Load Weekly Action Plan prompt template from config file."""
    prompt_file = Path(__file__).parent.parent.parent.parent / "config/prompts/weekly-action-plan.json"
    if prompt_file.exists():
        config = json.loads(prompt_file.read_text())
        return config["content"]["template"]
    return "Create a weekly action plan for the farmer based on: {{diagnoses}} {{weather_forecast}} {{farmer_context}}"


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
        "tokens_in": 800,
        "tokens_out": 600,
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
                "content": "Best practice: Apply fungicide before rain for better absorption.",
                "score": 0.82,
                "metadata": {"domain": "tea-cultivation"},
            },
            {
                "content": "Regional context: Kericho-High region has high humidity and is prone to fungal diseases.",
                "score": 0.78,
                "metadata": {"domain": "regional-context"},
            },
            {
                "content": "Action plan best practice: Prioritize critical actions first, max 5 actions per plan.",
                "score": 0.75,
                "metadata": {"domain": "action-plan-best-practices"},
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
            "farmer": {"id": "WM-4521", "name": "John Kamau", "region": "Kericho-High"},
            "weather": {"next_7_days": {"rain_probability": 0.7, "humidity_avg": 85, "temperature_avg_c": 20}},
            "recent_diagnoses": [{"condition": "tea_blister_blight", "severity": "moderate", "confidence": 0.88}],
        }
    )
    return integration


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
