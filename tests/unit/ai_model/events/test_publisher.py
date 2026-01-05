"""Unit tests for AI Model event publisher.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #2, #5, #11)

Tests for:
- EventPublisher publish methods
- Topic naming conventions
- Error handling
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from ai_model.events.models import (
    AgentCompletedEvent,
    AgentFailedEvent,
    CostRecordedEvent,
    EntityLinkage,
    ExtractorAgentResult,
)
from ai_model.events.publisher import EventPublisher

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def publisher() -> EventPublisher:
    """Create EventPublisher instance."""
    return EventPublisher(pubsub_name="pubsub")


@pytest.fixture
def sample_completed_event() -> AgentCompletedEvent:
    """Sample completed event for testing."""
    return AgentCompletedEvent(
        request_id="req-test-123",
        agent_id="disease-diagnosis",
        linkage=EntityLinkage(farmer_id="farmer-456"),
        result=ExtractorAgentResult(
            extracted_fields={"grade": "A"},
        ),
        execution_time_ms=150,
        model_used="anthropic/claude-3-haiku",
        cost_usd=Decimal("0.001"),
    )


@pytest.fixture
def sample_failed_event() -> AgentFailedEvent:
    """Sample failed event for testing."""
    return AgentFailedEvent(
        request_id="req-test-124",
        agent_id="qc-extractor",
        linkage=EntityLinkage(factory_id="factory-001"),
        error_type="llm_error",
        error_message="Rate limit exceeded",
        retry_count=3,
    )


@pytest.fixture
def sample_cost_event() -> CostRecordedEvent:
    """Sample cost event for testing."""
    return CostRecordedEvent(
        request_id="req-test-125",
        agent_id="disease-diagnosis",
        model="anthropic/claude-3-haiku",
        tokens_in=500,
        tokens_out=150,
        cost_usd=Decimal("0.00035"),
    )


# =============================================================================
# Publisher Initialization Tests
# =============================================================================


class TestPublisherInitialization:
    """Tests for EventPublisher initialization."""

    def test_default_pubsub_name(self) -> None:
        """Test default pubsub name is 'pubsub'."""
        publisher = EventPublisher()
        assert publisher._pubsub_name == "pubsub"

    def test_custom_pubsub_name(self) -> None:
        """Test custom pubsub name."""
        publisher = EventPublisher(pubsub_name="custom-pubsub")
        assert publisher._pubsub_name == "custom-pubsub"


# =============================================================================
# Topic Naming Tests
# =============================================================================


class TestTopicNaming:
    """Tests for topic naming conventions."""

    @pytest.mark.asyncio
    async def test_completed_event_topic_format(
        self, publisher: EventPublisher, sample_completed_event: AgentCompletedEvent
    ) -> None:
        """Test completed event publishes to correct topic format."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            await publisher.publish_agent_completed(sample_completed_event)

            mock_client.publish_event.assert_called_once()
            call_kwargs = mock_client.publish_event.call_args
            assert call_kwargs.kwargs["topic_name"] == "ai.agent.disease-diagnosis.completed"

    @pytest.mark.asyncio
    async def test_failed_event_topic_format(
        self, publisher: EventPublisher, sample_failed_event: AgentFailedEvent
    ) -> None:
        """Test failed event publishes to correct topic format."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            await publisher.publish_agent_failed(sample_failed_event)

            mock_client.publish_event.assert_called_once()
            call_kwargs = mock_client.publish_event.call_args
            assert call_kwargs.kwargs["topic_name"] == "ai.agent.qc-extractor.failed"

    @pytest.mark.asyncio
    async def test_cost_event_topic_format(
        self, publisher: EventPublisher, sample_cost_event: CostRecordedEvent
    ) -> None:
        """Test cost event publishes to correct topic format."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            await publisher.publish_cost_recorded(sample_cost_event)

            mock_client.publish_event.assert_called_once()
            call_kwargs = mock_client.publish_event.call_args
            assert call_kwargs.kwargs["topic_name"] == "ai.cost.recorded"


# =============================================================================
# Publish Data Tests
# =============================================================================


class TestPublishData:
    """Tests for published data format."""

    @pytest.mark.asyncio
    async def test_publish_uses_json_serialization(
        self, publisher: EventPublisher, sample_completed_event: AgentCompletedEvent
    ) -> None:
        """Test that events are serialized as JSON."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            await publisher.publish_agent_completed(sample_completed_event)

            call_kwargs = mock_client.publish_event.call_args
            assert call_kwargs.kwargs["data_content_type"] == "application/json"

    @pytest.mark.asyncio
    async def test_publish_uses_correct_pubsub_name(self, sample_completed_event: AgentCompletedEvent) -> None:
        """Test that custom pubsub name is used."""
        publisher = EventPublisher(pubsub_name="custom-pubsub")

        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            await publisher.publish_agent_completed(sample_completed_event)

            call_kwargs = mock_client.publish_event.call_args
            assert call_kwargs.kwargs["pubsub_name"] == "custom-pubsub"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestPublishErrorHandling:
    """Tests for publish error handling."""

    @pytest.mark.asyncio
    async def test_publish_raises_on_dapr_error(
        self, publisher: EventPublisher, sample_completed_event: AgentCompletedEvent
    ) -> None:
        """Test that DAPR errors are propagated."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.publish_event.side_effect = Exception("DAPR connection failed")
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(Exception) as exc_info:
                await publisher.publish_agent_completed(sample_completed_event)

            assert "DAPR connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_logs_error_on_failure(
        self, publisher: EventPublisher, sample_completed_event: AgentCompletedEvent
    ) -> None:
        """Test that errors are logged on publish failure."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.publish_event.side_effect = Exception("Test error")
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            with patch("ai_model.events.publisher.logger") as mock_logger:
                with pytest.raises(Exception):
                    await publisher.publish_agent_completed(sample_completed_event)

                mock_logger.exception.assert_called()


# =============================================================================
# Logging Tests
# =============================================================================


class TestPublishLogging:
    """Tests for publish logging."""

    @pytest.mark.asyncio
    async def test_publish_completed_logs_info(
        self, publisher: EventPublisher, sample_completed_event: AgentCompletedEvent
    ) -> None:
        """Test that successful completed publish logs info."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            with patch("ai_model.events.publisher.logger") as mock_logger:
                await publisher.publish_agent_completed(sample_completed_event)

                mock_logger.info.assert_called()
                call_args = mock_logger.info.call_args
                assert "Published agent completed event" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_publish_failed_logs_warning(
        self, publisher: EventPublisher, sample_failed_event: AgentFailedEvent
    ) -> None:
        """Test that failed event publish logs warning."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            with patch("ai_model.events.publisher.logger") as mock_logger:
                await publisher.publish_agent_failed(sample_failed_event)

                mock_logger.warning.assert_called()
                call_args = mock_logger.warning.call_args
                assert "Published agent failed event" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_publish_cost_logs_debug(
        self, publisher: EventPublisher, sample_cost_event: CostRecordedEvent
    ) -> None:
        """Test that cost event publish logs debug."""
        with patch("ai_model.events.publisher.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_dapr.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_dapr.return_value.__exit__ = MagicMock(return_value=False)

            with patch("ai_model.events.publisher.logger") as mock_logger:
                await publisher.publish_cost_recorded(sample_cost_event)

                mock_logger.debug.assert_called()
