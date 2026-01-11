"""Test fixtures for Farmer Voice Advisor Conversational golden sample tests.

Story 0.75.21: Conversational Agent Implementation - Sample Config & Golden Tests

This module provides fixtures for testing the Farmer Voice Advisor with mocked LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ConversationalConfig,
    ErrorHandlingConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
    StateConfig,
)
from ai_model.workflows.conversational import ConversationalWorkflow

if TYPE_CHECKING:
    from tests.golden.framework import GoldenSampleCollection


@pytest.fixture
def farmer_voice_advisor_config() -> ConversationalConfig:
    """Farmer Voice Advisor Conversational agent configuration."""
    return ConversationalConfig(
        id="farmer-voice-advisor:1.0.0",
        agent_id="farmer-voice-advisor",
        version="1.0.0",
        description="Voice-based agricultural advisor for Kenyan smallholder farmers",
        input=InputConfig(
            event="ai.agent.requested",
            schema={
                "type": "object",
                "required": ["session_id", "user_message"],
            },
        ),
        output=OutputConfig(
            event="ai.agent.farmer-voice-advisor.completed",
            schema={"type": "object", "required": ["response", "session_id"]},
        ),
        llm=LLMConfig(
            model="anthropic/claude-3-5-sonnet",
            temperature=0.4,
            max_tokens=500,
        ),
        rag=RAGConfig(
            enabled=True,
            query_template="agricultural advice for tea farmers: {{user_message}} topic: {{intent}}",
            knowledge_domains=["tea-cultivation", "pest-management", "seasonal-practices"],
            top_k=3,
            min_similarity=0.65,
        ),
        state=StateConfig(
            max_turns=5,
            session_ttl_minutes=30,
            checkpoint_backend="mongodb",
            context_window=3,
        ),
        intent_model="anthropic/claude-3-haiku",
        response_model="anthropic/claude-3-5-sonnet",
        mcp_sources=[
            MCPSourceConfig(server="plantation-mcp", tools=["get_farmer", "get_region"]),
        ],
        error_handling=ErrorHandlingConfig(
            max_attempts=2,
            backoff_ms=[100, 500],
            on_failure="graceful_fallback",
        ),
        metadata=AgentConfigMetadata(author="dev-story-0.75.21"),
    )


@pytest.fixture
def farmer_voice_advisor_prompt() -> str:
    """Load Farmer Voice Advisor prompt template from config file."""
    prompt_file = Path(__file__).parent.parent.parent.parent / "config/prompts/farmer-voice-advisor.json"
    if prompt_file.exists():
        config = json.loads(prompt_file.read_text())
        return config["content"]["template"]
    return "Respond to: {{user_message}}"


def create_mock_llm_response(expected_output: dict[str, Any]) -> dict[str, Any]:
    """Create a mock LLM response for a given expected output.

    Args:
        expected_output: The expected output from the golden sample.

    Returns:
        Mock LLM response dict.
    """
    # For conversational, we mock the response text directly
    response_text = expected_output.get("response", "")
    return {
        "content": response_text,
        "model": "anthropic/claude-3-5-sonnet",
        "tokens_in": 400,
        "tokens_out": 150,
    }


def create_mock_intent_response(intent: str = "question") -> dict[str, Any]:
    """Create a mock intent classification response.

    Args:
        intent: The intent to return.

    Returns:
        Mock intent response dict.
    """
    intent_json = json.dumps(
        {
            "intent": intent,
            "confidence": 0.92,
            "entities": {},
        }
    )
    return {
        "content": intent_json,
        "model": "anthropic/claude-3-haiku",
        "tokens_in": 50,
        "tokens_out": 30,
    }


@pytest.fixture
def mock_llm_gateway_factory():
    """Factory fixture to create mock LLM gateway with specific response."""

    def _factory(expected_output: dict[str, Any], intent: str = "question") -> MagicMock:
        gateway = MagicMock()

        # Create a side_effect function that returns different responses
        # based on the model being called
        async def mock_complete(*args, **kwargs):
            model = kwargs.get("model", "")
            if "haiku" in model.lower():
                return create_mock_intent_response(intent)
            return create_mock_llm_response(expected_output)

        gateway.complete = AsyncMock(side_effect=mock_complete)
        return gateway

    return _factory


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Default mock LLM gateway (returns empty response)."""
    gateway = MagicMock()

    async def mock_complete(*args, **kwargs):
        model = kwargs.get("model", "")
        if "haiku" in model.lower():
            return create_mock_intent_response("question")
        return {
            "content": "I understand. How can I help you?",
            "model": "anthropic/claude-3-5-sonnet",
            "tokens_in": 100,
            "tokens_out": 50,
        }

    gateway.complete = AsyncMock(side_effect=mock_complete)
    return gateway


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Mock ranking service for RAG retrieval."""
    service = MagicMock()

    # Create mock match objects
    mock_match_1 = MagicMock()
    mock_match_1.content = "Tea thrips cause small holes in young leaves. Apply neem oil for control."
    mock_match_1.title = "Tea Pest Management"
    mock_match_1.domain = "pest-management"
    mock_match_1.rerank_score = 0.88

    mock_match_2 = MagicMock()
    mock_match_2.content = "For healthy tea growth, maintain proper spacing and drainage."
    mock_match_2.title = "Tea Cultivation Basics"
    mock_match_2.domain = "tea-cultivation"
    mock_match_2.rerank_score = 0.82

    mock_result = MagicMock()
    mock_result.matches = [mock_match_1, mock_match_2]

    service.rank = AsyncMock(return_value=mock_result)
    return service


@pytest.fixture
def conversational_workflow(
    mock_llm_gateway: MagicMock,
    mock_ranking_service: MagicMock,
) -> ConversationalWorkflow:
    """Conversational workflow instance with mocked dependencies."""
    return ConversationalWorkflow(
        llm_gateway=mock_llm_gateway,
        ranking_service=mock_ranking_service,
        checkpointer=None,
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
