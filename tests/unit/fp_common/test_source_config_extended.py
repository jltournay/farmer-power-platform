"""Unit tests for extended SourceConfig models (Story 2.4).

Tests cover:
- processor_type field in IngestionConfig
- EventsConfig and EventConfig models
- TransformationConfig.ai_agent_id field
"""

import pytest

from fp_common.models.source_config import (
    EventConfig,
    EventsConfig,
    IngestionConfig,
    SourceConfig,
    StorageConfig,
    TransformationConfig,
)


class TestIngestionConfigProcessorType:
    """Tests for processor_type in IngestionConfig."""

    def test_processor_type_default_none(self) -> None:
        """Test processor_type defaults to None."""
        config = IngestionConfig(mode="blob_trigger")
        assert config.processor_type is None

    def test_processor_type_explicit(self) -> None:
        """Test setting processor_type explicitly."""
        config = IngestionConfig(
            mode="blob_trigger",
            processor_type="json-extraction",
        )
        assert config.processor_type == "json-extraction"

    def test_processor_type_in_model_dump(self) -> None:
        """Test processor_type included in model_dump."""
        config = IngestionConfig(
            mode="blob_trigger",
            processor_type="zip-extraction",
        )
        data = config.model_dump()
        assert "processor_type" in data
        assert data["processor_type"] == "zip-extraction"


class TestTransformationConfigAiAgentId:
    """Tests for ai_agent_id in TransformationConfig."""

    def test_ai_agent_id_default_none(self) -> None:
        """Test ai_agent_id defaults to None."""
        config = TransformationConfig(
            extract_fields=["field1"],
            link_field="id",
        )
        assert config.ai_agent_id is None

    def test_ai_agent_id_explicit(self) -> None:
        """Test setting ai_agent_id explicitly."""
        config = TransformationConfig(
            ai_agent_id="qc-result-extraction-agent",
            extract_fields=["field1"],
            link_field="id",
        )
        assert config.ai_agent_id == "qc-result-extraction-agent"

    def test_get_ai_agent_id_prefers_ai_agent_id(self) -> None:
        """Test get_ai_agent_id returns ai_agent_id over agent."""
        config = TransformationConfig(
            ai_agent_id="new-agent",
            agent="old-agent",
            extract_fields=["field1"],
            link_field="id",
        )
        assert config.get_ai_agent_id() == "new-agent"

    def test_get_ai_agent_id_falls_back_to_agent(self) -> None:
        """Test get_ai_agent_id falls back to agent if ai_agent_id not set."""
        config = TransformationConfig(
            agent="old-agent",
            extract_fields=["field1"],
            link_field="id",
        )
        assert config.get_ai_agent_id() == "old-agent"

    def test_get_ai_agent_id_returns_none_if_both_missing(self) -> None:
        """Test get_ai_agent_id returns None if both fields missing."""
        config = TransformationConfig(
            extract_fields=["field1"],
            link_field="id",
        )
        assert config.get_ai_agent_id() is None


class TestEventConfig:
    """Tests for EventConfig model."""

    def test_event_config_required_topic(self) -> None:
        """Test EventConfig requires topic."""
        config = EventConfig(topic="collection.quality_result.received")
        assert config.topic == "collection.quality_result.received"
        assert config.payload_fields == []

    def test_event_config_with_payload_fields(self) -> None:
        """Test EventConfig with payload_fields."""
        config = EventConfig(
            topic="collection.quality_result.received",
            payload_fields=["document_id", "source_id", "farmer_id"],
        )
        assert config.payload_fields == ["document_id", "source_id", "farmer_id"]


class TestEventsConfig:
    """Tests for EventsConfig model."""

    def test_events_config_defaults_none(self) -> None:
        """Test EventsConfig defaults to None for both events."""
        config = EventsConfig()
        assert config.on_success is None
        assert config.on_failure is None

    def test_events_config_with_on_success(self) -> None:
        """Test EventsConfig with on_success event."""
        config = EventsConfig(
            on_success=EventConfig(
                topic="collection.quality_result.received",
                payload_fields=["document_id"],
            )
        )
        assert config.on_success is not None
        assert config.on_success.topic == "collection.quality_result.received"
        assert config.on_failure is None

    def test_events_config_with_both_events(self) -> None:
        """Test EventsConfig with both success and failure events."""
        config = EventsConfig(
            on_success=EventConfig(topic="topic.success"),
            on_failure=EventConfig(topic="topic.failure"),
        )
        assert config.on_success.topic == "topic.success"
        assert config.on_failure.topic == "topic.failure"


class TestSourceConfigEvents:
    """Tests for events field in SourceConfig."""

    def test_source_config_events_default_none(self) -> None:
        """Test SourceConfig.events defaults to None."""
        config = SourceConfig(
            source_id="test-source",
            display_name="Test Source",
            description="Test description",
            ingestion=IngestionConfig(mode="blob_trigger"),
            transformation=TransformationConfig(
                extract_fields=["field1"],
                link_field="id",
            ),
            storage=StorageConfig(
                raw_container="raw",
                index_collection="index",
            ),
        )
        assert config.events is None

    def test_source_config_with_events(self) -> None:
        """Test SourceConfig with events configuration."""
        config = SourceConfig(
            source_id="test-source",
            display_name="Test Source",
            description="Test description",
            ingestion=IngestionConfig(
                mode="blob_trigger",
                processor_type="json-extraction",
            ),
            transformation=TransformationConfig(
                ai_agent_id="test-agent",
                extract_fields=["field1"],
                link_field="id",
            ),
            storage=StorageConfig(
                raw_container="raw",
                index_collection="index",
            ),
            events=EventsConfig(
                on_success=EventConfig(
                    topic="collection.document.stored",
                    payload_fields=["document_id", "source_id"],
                ),
            ),
        )
        assert config.events is not None
        assert config.events.on_success.topic == "collection.document.stored"

    def test_source_config_model_dump_includes_events(self) -> None:
        """Test that model_dump includes events field."""
        config = SourceConfig(
            source_id="test-source",
            display_name="Test Source",
            description="Test description",
            ingestion=IngestionConfig(mode="blob_trigger"),
            transformation=TransformationConfig(
                extract_fields=["field1"],
                link_field="id",
            ),
            storage=StorageConfig(
                raw_container="raw",
                index_collection="index",
            ),
            events=EventsConfig(
                on_success=EventConfig(topic="test.topic"),
            ),
        )
        data = config.model_dump()
        assert "events" in data
        assert data["events"]["on_success"]["topic"] == "test.topic"
