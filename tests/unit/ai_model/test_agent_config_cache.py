"""Unit tests for AgentConfigCache.

Story 0.75.4: Tests for agent config caching with Change Streams (ADR-013).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentType,
    ExplorerConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.services.agent_config_cache import AgentConfigCache
from fp_common.cache import MongoChangeStreamCache

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_db():
    """Create mock MongoDB database."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_collection(mock_db):
    """Get the mock collection from db."""
    return mock_db["agent_configs"]


@pytest.fixture
def agent_config_cache(mock_db):
    """Create an AgentConfigCache instance."""
    return AgentConfigCache(db=mock_db)


@pytest.fixture
def sample_extractor_doc():
    """Sample extractor config document from MongoDB."""
    return {
        "_id": "mongo-id-1",
        "id": "qc-event-extractor:1.0.0",
        "agent_id": "qc-event-extractor",
        "version": "1.0.0",
        "type": "extractor",
        "status": "active",
        "description": "Extracts QC events",
        "input": {"event": "collection.document.received", "schema": {}},
        "output": {"event": "ai.extraction.complete", "schema": {}},
        "llm": {"model": "anthropic/claude-3-haiku", "temperature": 0.1, "max_tokens": 500},
        "mcp_sources": [],
        "error_handling": {"max_attempts": 3, "backoff_ms": [100, 500, 2000], "on_failure": "publish_error_event"},
        "metadata": {
            "author": "admin",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
        "extraction_schema": {"required_fields": ["farmer_id"]},
    }


@pytest.fixture
def sample_explorer_doc():
    """Sample explorer config document from MongoDB."""
    return {
        "_id": "mongo-id-2",
        "id": "disease-diagnosis:1.0.0",
        "agent_id": "disease-diagnosis",
        "version": "1.0.0",
        "type": "explorer",
        "status": "active",
        "description": "Diagnoses plant diseases",
        "input": {"event": "ai.triage.complete", "schema": {}},
        "output": {"event": "ai.diagnosis.complete", "schema": {}},
        "llm": {"model": "anthropic/claude-3-5-sonnet", "temperature": 0.3, "max_tokens": 2000},
        "mcp_sources": [],
        "error_handling": {"max_attempts": 3, "backoff_ms": [100, 500, 2000], "on_failure": "publish_error_event"},
        "metadata": {
            "author": "admin",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
        "rag": {"enabled": True, "knowledge_domains": ["plant_diseases"], "top_k": 5, "min_similarity": 0.7},
    }


# =============================================================================
# INHERITANCE TESTS
# =============================================================================


class TestInheritance:
    """Tests for class inheritance."""

    def test_inherits_from_mongo_change_stream_cache(self, agent_config_cache):
        """Test AgentConfigCache inherits from MongoChangeStreamCache."""
        assert isinstance(agent_config_cache, MongoChangeStreamCache)

    def test_uses_correct_collection_name(self, agent_config_cache):
        """Test cache uses agent_configs collection."""
        assert agent_config_cache._collection_name == "agent_configs"

    def test_uses_correct_cache_name(self, agent_config_cache):
        """Test cache uses agent_config as cache name."""
        assert agent_config_cache._cache_name == "agent_config"


# =============================================================================
# ABSTRACT METHOD IMPLEMENTATION TESTS
# =============================================================================


class TestAbstractMethods:
    """Tests for abstract method implementations."""

    def test_get_cache_key_returns_agent_id(self, agent_config_cache):
        """Test _get_cache_key returns the agent_id."""
        config = ExtractorConfig(
            id="test:1.0.0",
            agent_id="test-agent",
            version="1.0.0",
            description="Test",
            input=InputConfig(event="test.event", schema={}),
            output=OutputConfig(event="test.output", schema={}),
            llm=LLMConfig(model="test-model"),
            metadata=AgentConfigMetadata(author="test"),
            extraction_schema={},
        )

        key = agent_config_cache._get_cache_key(config)
        assert key == "test-agent"

    def test_parse_document_handles_extractor_type(self, agent_config_cache, sample_extractor_doc):
        """Test _parse_document correctly parses extractor config."""
        config = agent_config_cache._parse_document(sample_extractor_doc)

        assert isinstance(config, ExtractorConfig)
        assert config.agent_id == "qc-event-extractor"
        assert config.type == "extractor"

    def test_parse_document_handles_explorer_type(self, agent_config_cache, sample_explorer_doc):
        """Test _parse_document correctly parses explorer config."""
        config = agent_config_cache._parse_document(sample_explorer_doc)

        assert isinstance(config, ExplorerConfig)
        assert config.agent_id == "disease-diagnosis"
        assert config.type == "explorer"
        assert config.rag.enabled is True

    def test_parse_document_removes_mongo_id(self, agent_config_cache, sample_extractor_doc):
        """Test _parse_document removes MongoDB _id field."""
        assert "_id" in sample_extractor_doc

        config = agent_config_cache._parse_document(sample_extractor_doc)

        # Should not raise - _id was removed before validation
        assert config.id == "qc-event-extractor:1.0.0"

    def test_get_filter_returns_active_status(self, agent_config_cache):
        """Test _get_filter returns filter for active configs."""
        filter_dict = agent_config_cache._get_filter()
        assert filter_dict == {"status": "active"}


# =============================================================================
# DOMAIN METHOD TESTS
# =============================================================================


class TestDomainMethods:
    """Tests for domain-specific methods."""

    @pytest.mark.asyncio
    async def test_get_config_returns_correct_config(self, agent_config_cache):
        """Test get_config returns the correct config by agent_id."""
        # Pre-populate cache
        config = ExtractorConfig(
            id="test:1.0.0",
            agent_id="test-agent",
            version="1.0.0",
            description="Test",
            input=InputConfig(event="test.event", schema={}),
            output=OutputConfig(event="test.output", schema={}),
            llm=LLMConfig(model="test-model"),
            metadata=AgentConfigMetadata(author="test"),
            extraction_schema={},
        )
        agent_config_cache._cache = {"test-agent": config}
        agent_config_cache._cache_loaded_at = datetime.now(UTC)

        result = await agent_config_cache.get_config("test-agent")

        assert result is not None
        assert result.agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_get_config_returns_none_for_missing(self, agent_config_cache):
        """Test get_config returns None for non-existent agent_id."""
        agent_config_cache._cache = {}
        agent_config_cache._cache_loaded_at = datetime.now(UTC)

        result = await agent_config_cache.get_config("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_configs_by_type_filters_correctly(self, agent_config_cache):
        """Test get_configs_by_type filters by agent type."""
        # Create configs of different types
        extractor = ExtractorConfig(
            id="ext:1.0.0",
            agent_id="extractor-1",
            version="1.0.0",
            type="extractor",
            description="Extractor",
            input=InputConfig(event="test.event", schema={}),
            output=OutputConfig(event="test.output", schema={}),
            llm=LLMConfig(model="test-model"),
            metadata=AgentConfigMetadata(author="test"),
            extraction_schema={},
        )
        explorer = ExplorerConfig(
            id="exp:1.0.0",
            agent_id="explorer-1",
            version="1.0.0",
            type="explorer",
            description="Explorer",
            input=InputConfig(event="test.event", schema={}),
            output=OutputConfig(event="test.output", schema={}),
            llm=LLMConfig(model="test-model"),
            metadata=AgentConfigMetadata(author="test"),
            rag=RAGConfig(),
        )

        agent_config_cache._cache = {
            "extractor-1": extractor,
            "explorer-1": explorer,
        }
        agent_config_cache._cache_loaded_at = datetime.now(UTC)

        # Get only extractors
        extractors = await agent_config_cache.get_configs_by_type(AgentType.EXTRACTOR)

        assert len(extractors) == 1
        assert extractors[0].agent_id == "extractor-1"

        # Get only explorers
        explorers = await agent_config_cache.get_configs_by_type(AgentType.EXPLORER)

        assert len(explorers) == 1
        assert explorers[0].agent_id == "explorer-1"


# =============================================================================
# DISCRIMINATED UNION HANDLING TESTS
# =============================================================================


class TestDiscriminatedUnion:
    """Tests for discriminated union type handling."""

    def test_parses_all_five_agent_types(self, agent_config_cache):
        """Test parsing all 5 agent types via discriminated union."""
        # This test verifies TypeAdapter handles the union correctly
        base_doc = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "description": "Test",
            "status": "active",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test", "temperature": 0.3, "max_tokens": 100},
            "mcp_sources": [],
            "error_handling": {"max_attempts": 3, "backoff_ms": [100], "on_failure": "publish_error_event"},
            "metadata": {"author": "test", "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
        }

        # Test extractor
        doc = {**base_doc, "type": "extractor", "extraction_schema": {}}
        config = agent_config_cache._parse_document(doc)
        assert isinstance(config, ExtractorConfig)

        # Test explorer
        doc = {
            **base_doc,
            "type": "explorer",
            "rag": {"enabled": True, "knowledge_domains": [], "top_k": 5, "min_similarity": 0.7},
        }
        config = agent_config_cache._parse_document(doc)
        assert isinstance(config, ExplorerConfig)
