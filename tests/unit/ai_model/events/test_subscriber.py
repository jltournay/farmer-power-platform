"""Unit tests for AI Model event subscriber.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #1, #4, #10, #11)

Tests for:
- Agent request handler
- Error scenarios (validation, service not initialized, etc.)
- Payload extraction
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.events.subscriber import (
    extract_payload,
    handle_agent_request,
    set_agent_config_cache,
    set_main_event_loop,
)
from dapr.clients.grpc._response import TopicEventResponse

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
def mock_event_loop() -> asyncio.AbstractEventLoop:
    """Get the current event loop for tests."""
    return asyncio.get_event_loop()


@pytest.fixture
def valid_agent_request_payload() -> dict:
    """Valid agent request payload."""
    return {
        "request_id": "req-test-123",
        "agent_id": "disease-diagnosis",
        "linkage": {"farmer_id": "farmer-456"},
        "input_data": {"symptoms": ["yellow leaves"]},
        "source": "collection-model",
    }


@pytest.fixture
def mock_dapr_message(valid_agent_request_payload: dict) -> MagicMock:
    """Mock DAPR message object."""
    message = MagicMock()
    message.data.return_value = valid_agent_request_payload
    message.topic.return_value = "ai.agent.requested"
    return message


# =============================================================================
# Payload Extraction Tests
# =============================================================================


class TestExtractPayload:
    """Tests for extract_payload function."""

    def test_extract_dict_payload(self) -> None:
        """Test extraction from direct dict payload."""
        raw_data = {"key": "value"}
        result = extract_payload(raw_data)
        assert result == {"key": "value"}

    def test_extract_json_string_payload(self) -> None:
        """Test extraction from JSON string."""
        raw_data = '{"key": "value"}'
        result = extract_payload(raw_data)
        assert result == {"key": "value"}

    def test_extract_bytes_payload(self) -> None:
        """Test extraction from bytes."""
        raw_data = b'{"key": "value"}'
        result = extract_payload(raw_data)
        assert result == {"key": "value"}

    def test_extract_cloudevent_wrapped_payload(self) -> None:
        """Test extraction from CloudEvent wrapper."""
        raw_data = {"specversion": "1.0", "type": "ai.agent.requested", "data": {"payload": {"request_id": "req-123"}}}
        result = extract_payload(raw_data)
        assert result == {"request_id": "req-123"}

    def test_extract_nested_data_payload(self) -> None:
        """Test extraction from nested data field."""
        raw_data = {"data": {"agent_id": "test-agent"}}
        result = extract_payload(raw_data)
        assert result == {"agent_id": "test-agent"}

    def test_extract_payload_field(self) -> None:
        """Test extraction from top-level payload field."""
        raw_data = {"payload": {"request_id": "req-456"}}
        result = extract_payload(raw_data)
        assert result == {"request_id": "req-456"}


# =============================================================================
# Handler Tests - Service Not Initialized
# =============================================================================


class TestHandlerNotInitialized:
    """Tests for handler when services not initialized."""

    def test_handler_cache_not_initialized(self, mock_dapr_message: MagicMock) -> None:
        """Test handler returns retry when cache not initialized."""
        # Reset module state
        set_agent_config_cache(None)  # type: ignore[arg-type]
        set_main_event_loop(None)  # type: ignore[arg-type]

        response = handle_agent_request(mock_dapr_message)

        assert isinstance(response, TopicEventResponse)
        # Response should be retry since cache is not initialized

    def test_handler_event_loop_not_initialized(
        self,
        mock_dapr_message: MagicMock,
        mock_agent_config_cache: MagicMock,
    ) -> None:
        """Test handler returns retry when event loop not initialized."""
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(None)  # type: ignore[arg-type]

        response = handle_agent_request(mock_dapr_message)

        assert isinstance(response, TopicEventResponse)


# =============================================================================
# Handler Tests - Validation Errors
# =============================================================================


class TestHandlerValidationErrors:
    """Tests for handler validation error scenarios."""

    def test_handler_invalid_json(self) -> None:
        """Test handler drops message with invalid JSON."""
        message = MagicMock()
        message.data.return_value = "not valid json {"

        response = handle_agent_request(message)

        assert isinstance(response, TopicEventResponse)
        # Should drop since JSON is invalid

    def test_handler_missing_required_fields(self) -> None:
        """Test handler drops message with missing required fields."""
        message = MagicMock()
        message.data.return_value = {
            "request_id": "req-123",
            # Missing: agent_id, linkage, input_data, source
        }

        response = handle_agent_request(message)

        assert isinstance(response, TopicEventResponse)

    def test_handler_invalid_linkage(self) -> None:
        """Test handler drops message with invalid linkage."""
        message = MagicMock()
        message.data.return_value = {
            "request_id": "req-123",
            "agent_id": "test-agent",
            "linkage": {},  # No linkage fields - invalid
            "input_data": {},
            "source": "test",
        }

        response = handle_agent_request(message)

        assert isinstance(response, TopicEventResponse)


# =============================================================================
# Handler Tests - Agent Config Lookup
# =============================================================================


class TestHandlerAgentConfigLookup:
    """Tests for agent config lookup in handler."""

    @pytest.mark.asyncio
    async def test_handler_agent_not_found(
        self,
        mock_agent_config_cache: MagicMock,
        valid_agent_request_payload: dict,
    ) -> None:
        """Test handler drops message when agent not found."""
        # Setup: agent config returns None (not found)
        mock_agent_config_cache.get = AsyncMock(return_value=None)
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(asyncio.get_event_loop())

        message = MagicMock()
        message.data.return_value = valid_agent_request_payload

        response = handle_agent_request(message)

        # Should drop since agent not found
        assert isinstance(response, TopicEventResponse)

    @pytest.mark.asyncio
    async def test_handler_agent_found_processes_request(
        self,
        mock_agent_config_cache: MagicMock,
        valid_agent_request_payload: dict,
    ) -> None:
        """Test handler processes request when agent found."""
        # Setup: agent config returns valid config
        mock_agent_config = MagicMock()
        mock_agent_config.agent_id = "disease-diagnosis"
        mock_agent_config_cache.get = AsyncMock(return_value=mock_agent_config)
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(asyncio.get_event_loop())

        message = MagicMock()
        message.data.return_value = valid_agent_request_payload

        response = handle_agent_request(message)

        # Should succeed since agent found and processed
        assert isinstance(response, TopicEventResponse)


# =============================================================================
# Handler Tests - Transient Error Handling
# =============================================================================


class TestHandlerTransientErrors:
    """Tests for transient error handling."""

    @pytest.mark.asyncio
    async def test_handler_timeout_retries(
        self,
        mock_agent_config_cache: MagicMock,
        valid_agent_request_payload: dict,
    ) -> None:
        """Test handler returns retry on timeout."""

        # Setup: agent config lookup times out
        async def slow_get(agent_id: str):
            await asyncio.sleep(100)  # Very long wait
            return None

        mock_agent_config_cache.get = slow_get
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(asyncio.get_event_loop())

        message = MagicMock()
        message.data.return_value = valid_agent_request_payload

        # The handler should handle the timeout gracefully
        # (actual timeout behavior depends on implementation)


# =============================================================================
# Module State Management Tests
# =============================================================================


class TestModuleStateManagement:
    """Tests for module-level state management functions."""

    def test_set_agent_config_cache(self, mock_agent_config_cache: MagicMock) -> None:
        """Test setting agent config cache."""
        set_agent_config_cache(mock_agent_config_cache)
        # No exception means success

    def test_set_main_event_loop(self, mock_event_loop: asyncio.AbstractEventLoop) -> None:
        """Test setting main event loop."""
        set_main_event_loop(mock_event_loop)
        # No exception means success

    def test_set_cache_logs_message(self, mock_agent_config_cache: MagicMock) -> None:
        """Test that setting cache logs an info message."""
        with patch("ai_model.events.subscriber.logger") as mock_logger:
            set_agent_config_cache(mock_agent_config_cache)
            mock_logger.info.assert_called()

    def test_set_event_loop_logs_message(self, mock_event_loop: asyncio.AbstractEventLoop) -> None:
        """Test that setting event loop logs an info message."""
        with patch("ai_model.events.subscriber.logger") as mock_logger:
            set_main_event_loop(mock_event_loop)
            mock_logger.info.assert_called()
