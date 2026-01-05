"""Pytest fixtures for agent config CLI tests."""

# Add the CLI package to the path
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

cli_path = Path(__file__).parent.parent.parent.parent / "scripts" / "agent-config" / "src"
if str(cli_path) not in sys.path:
    sys.path.insert(0, str(cli_path))


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the agent_config fixtures directory."""
    return Path(__file__).parent.parent.parent / "fixtures" / "agent_config"


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock()
    settings.get_mongodb_uri.return_value = "mongodb://localhost:27017"
    settings.database_name = "ai_model"
    settings.agent_configs_collection = "agent_configs"
    return settings


@pytest.fixture
def mock_motor_client():
    """Create a mock Motor MongoDB client."""
    client = AsyncMock()
    db = MagicMock()
    collection = AsyncMock()

    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    client.__getitem__ = MagicMock(return_value=db)
    db.__getitem__ = MagicMock(return_value=collection)

    # Default find returns empty
    cursor = AsyncMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    collection.find = MagicMock(return_value=cursor)
    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()

    return client


@pytest.fixture
def sample_extractor_config() -> dict:
    """Return a sample extractor config as a dict."""
    return {
        "id": "qc-event-extractor:1.0.0",
        "agent_id": "qc-event-extractor",
        "type": "extractor",
        "version": "1.0.0",
        "status": "active",
        "description": "Extracts structured data from QC analyzer payloads",
        "input": {
            "event": "collection.document.received",
            "schema": {"required": ["doc_id"]},
        },
        "output": {
            "event": "ai.extraction.complete",
            "schema": {"fields": ["farmer_id", "grade"]},
        },
        "llm": {
            "model": "anthropic/claude-3-haiku",
            "temperature": 0.1,
            "max_tokens": 500,
        },
        "extraction_schema": {"required_fields": ["farmer_id", "grade"]},
        "mcp_sources": [],
        "error_handling": {
            "max_attempts": 3,
            "backoff_ms": [100, 500, 2000],
            "on_failure": "publish_error_event",
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }


@pytest.fixture
def sample_explorer_config() -> dict:
    """Return a sample explorer config as a dict."""
    return {
        "id": "disease-diagnosis:1.0.0",
        "agent_id": "disease-diagnosis",
        "type": "explorer",
        "version": "1.0.0",
        "status": "active",
        "description": "Analyzes quality issues and produces diagnosis",
        "input": {
            "event": "ai.extraction.complete",
            "schema": {"required": ["farmer_id"]},
        },
        "output": {
            "event": "ai.diagnosis.complete",
            "schema": {"fields": ["diagnosis_id"]},
        },
        "llm": {
            "model": "anthropic/claude-3-5-sonnet",
            "temperature": 0.3,
            "max_tokens": 2000,
        },
        "rag": {
            "enabled": True,
            "knowledge_domains": ["plant_diseases"],
            "top_k": 5,
            "min_similarity": 0.7,
        },
        "mcp_sources": [],
        "error_handling": {
            "max_attempts": 3,
            "backoff_ms": [100, 500, 2000],
            "on_failure": "publish_error_event",
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }


@pytest.fixture
def sample_generator_config() -> dict:
    """Return a sample generator config as a dict."""
    return {
        "id": "weekly-action-plan:1.0.0",
        "agent_id": "weekly-action-plan",
        "type": "generator",
        "version": "1.0.0",
        "status": "active",
        "description": "Generates personalized weekly action plans",
        "input": {
            "event": "action-plan.request",
            "schema": {"required": ["farmer_id"]},
        },
        "output": {
            "event": "action-plan.generated",
            "schema": {"fields": ["plan_id"]},
        },
        "llm": {
            "model": "anthropic/claude-3-5-sonnet",
            "temperature": 0.5,
            "max_tokens": 3000,
        },
        "rag": {
            "enabled": True,
            "knowledge_domains": ["tea_cultivation"],
            "top_k": 8,
            "min_similarity": 0.6,
        },
        "output_format": "markdown",
        "mcp_sources": [],
        "error_handling": {
            "max_attempts": 3,
            "backoff_ms": [100, 500, 2000],
            "on_failure": "publish_error_event",
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }


@pytest.fixture
def sample_conversational_config() -> dict:
    """Return a sample conversational config as a dict."""
    return {
        "id": "dialogue-responder:1.0.0",
        "agent_id": "dialogue-responder",
        "type": "conversational",
        "version": "1.0.0",
        "status": "active",
        "description": "Handles multi-turn dialogue with farmers",
        "input": {
            "event": "conversation.message.received",
            "schema": {"required": ["session_id", "message"]},
        },
        "output": {
            "event": "conversation.response.generated",
            "schema": {"fields": ["response"]},
        },
        "llm": {
            "model": "anthropic/claude-3-5-sonnet",
            "temperature": 0.4,
            "max_tokens": 1000,
        },
        "rag": {
            "enabled": True,
            "knowledge_domains": ["tea_cultivation"],
            "top_k": 5,
            "min_similarity": 0.7,
        },
        "state": {
            "max_turns": 5,
            "session_ttl_minutes": 30,
            "checkpoint_backend": "mongodb",
            "context_window": 3,
        },
        "intent_model": "anthropic/claude-3-haiku",
        "response_model": "anthropic/claude-3-5-sonnet",
        "mcp_sources": [],
        "error_handling": {
            "max_attempts": 3,
            "backoff_ms": [100, 500, 2000],
            "on_failure": "publish_error_event",
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }


@pytest.fixture
def sample_tiered_vision_config() -> dict:
    """Return a sample tiered-vision config as a dict."""
    return {
        "id": "leaf-quality-analyzer:1.0.0",
        "agent_id": "leaf-quality-analyzer",
        "type": "tiered-vision",
        "version": "1.0.0",
        "status": "active",
        "description": "Cost-optimized image analysis for tea leaf quality",
        "input": {
            "event": "collection.image.received",
            "schema": {"required": ["image_url"]},
        },
        "output": {
            "event": "ai.vision.complete",
            "schema": {"fields": ["classification"]},
        },
        "llm": None,
        "rag": {
            "enabled": True,
            "knowledge_domains": ["plant_diseases"],
            "top_k": 3,
            "min_similarity": 0.75,
        },
        "tiered_llm": {
            "screen": {
                "model": "anthropic/claude-3-haiku",
                "temperature": 0.1,
                "max_tokens": 200,
            },
            "diagnose": {
                "model": "anthropic/claude-3-5-sonnet",
                "temperature": 0.3,
                "max_tokens": 2000,
            },
        },
        "routing": {
            "screen_threshold": 0.7,
            "healthy_skip_threshold": 0.85,
            "obvious_skip_threshold": 0.75,
        },
        "mcp_sources": [],
        "error_handling": {
            "max_attempts": 3,
            "backoff_ms": [100, 500, 2000],
            "on_failure": "publish_error_event",
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
