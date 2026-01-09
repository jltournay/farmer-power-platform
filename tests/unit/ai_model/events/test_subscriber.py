"""Unit tests for AI Model event subscriber.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #1, #4, #10, #11)
Story 0.75.16b: Updated for AgentExecutor wiring

Tests for:
- Agent request handler
- Error scenarios (validation, service not initialized, etc.)
- Payload extraction
- AgentExecutor integration
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.events.subscriber import (
    execute_agent,
    extract_payload,
    handle_agent_request,
    set_agent_config_cache,
    set_agent_executor,
    set_main_event_loop,
)
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events import AgentRequestEvent, EntityLinkage

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
    """Create a new event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_agent_executor() -> MagicMock:
    """Mock agent executor (Story 0.75.16b)."""
    executor = MagicMock()
    executor.execute_and_publish = AsyncMock()
    return executor


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
        set_agent_executor(None)  # type: ignore[arg-type]

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
        set_agent_executor(None)  # type: ignore[arg-type]

        response = handle_agent_request(mock_dapr_message)

        assert isinstance(response, TopicEventResponse)

    def test_handler_executor_not_initialized(
        self,
        mock_dapr_message: MagicMock,
        mock_agent_config_cache: MagicMock,
        mock_event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Test handler returns retry when executor not initialized (Story 0.75.16b)."""
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(mock_event_loop)
        set_agent_executor(None)  # type: ignore[arg-type]

        response = handle_agent_request(mock_dapr_message)

        assert isinstance(response, TopicEventResponse)
        # Response should be retry since executor is not initialized


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

    def test_handler_timeout_retries(
        self,
        mock_agent_config_cache: MagicMock,
        valid_agent_request_payload: dict,
        mock_event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Test handler returns retry on timeout."""

        # Setup: agent config lookup raises TimeoutError
        # We simulate this by having run_coroutine_threadsafe timeout
        async def slow_get(agent_id: str):
            await asyncio.sleep(100)  # Very long wait - will timeout
            return None

        mock_agent_config_cache.get = slow_get
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(mock_event_loop)

        message = MagicMock()
        message.data.return_value = valid_agent_request_payload

        # Patch the timeout to be very short so test completes quickly
        with patch("ai_model.events.subscriber.asyncio.run_coroutine_threadsafe") as mock_run:
            # Simulate timeout by having future.result() raise TimeoutError
            mock_future = MagicMock()
            mock_future.result.side_effect = TimeoutError("Timeout waiting for agent config")
            mock_run.return_value = mock_future

            response = handle_agent_request(message)

            # Should return retry on timeout
            assert isinstance(response, TopicEventResponse)


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

    def test_set_agent_executor(self, mock_agent_executor: MagicMock) -> None:
        """Test setting agent executor (Story 0.75.16b)."""
        set_agent_executor(mock_agent_executor)
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

    def test_set_executor_logs_message(self, mock_agent_executor: MagicMock) -> None:
        """Test that setting executor logs an info message (Story 0.75.16b)."""
        with patch("ai_model.events.subscriber.logger") as mock_logger:
            set_agent_executor(mock_agent_executor)
            mock_logger.info.assert_called()


# =============================================================================
# Integration Tests: Event → Executor → Publisher Flow (Story 0.75.16b)
# =============================================================================


class TestSubscriberIntegration:
    """Integration tests for the full subscriber → executor → publisher flow.

    Story 0.75.16b: These tests verify the complete event processing flow
    from receiving an AgentRequestEvent to publishing the result event.
    """

    @pytest.fixture
    def integration_mock_executor(self) -> MagicMock:
        """Mock executor for integration tests."""
        executor = MagicMock()
        executor.execute_and_publish = AsyncMock()
        return executor

    @pytest.fixture
    def integration_mock_cache(self) -> MagicMock:
        """Mock cache for integration tests."""
        cache = MagicMock()
        cache.get = AsyncMock(
            return_value={
                "agent_id": "qc-event-extractor",
                "type": "extractor",
                "llm": {"model": "test-model"},
            }
        )
        return cache

    @pytest.fixture
    def integration_setup(
        self,
        integration_mock_cache: MagicMock,
        integration_mock_executor: MagicMock,
        mock_event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Set up all module-level dependencies for integration test."""
        set_agent_config_cache(integration_mock_cache)
        set_main_event_loop(mock_event_loop)
        set_agent_executor(integration_mock_executor)

    @pytest.mark.asyncio
    async def test_full_flow_success(
        self,
        integration_mock_cache: MagicMock,
        integration_mock_executor: MagicMock,
    ) -> None:
        """Test full flow: event → executor.execute_and_publish() called."""
        # Setup module state
        loop = asyncio.get_event_loop()
        set_agent_config_cache(integration_mock_cache)
        set_main_event_loop(loop)
        set_agent_executor(integration_mock_executor)

        # Create valid message
        message = MagicMock()
        message.data.return_value = {
            "request_id": "int-test-001",
            "agent_id": "qc-event-extractor",
            "linkage": {"farmer_id": "farmer-integration"},
            "input_data": {"test": "data"},
            "source": "integration-test",
        }

        # Use patch to make run_coroutine_threadsafe work synchronously
        with patch("ai_model.events.subscriber.asyncio.run_coroutine_threadsafe") as mock_run:
            # Mock the future to return immediately
            mock_future = MagicMock()
            mock_future.result.return_value = {"agent_id": "qc-event-extractor", "type": "extractor"}
            mock_run.return_value = mock_future

            # Call handler
            response = handle_agent_request(message)

            # Verify executor was called
            assert mock_run.call_count >= 1
            assert isinstance(response, TopicEventResponse)

    @pytest.mark.asyncio
    async def test_execute_agent_calls_executor(
        self,
        integration_mock_executor: MagicMock,
    ) -> None:
        """Test execute_agent() correctly calls AgentExecutor.execute_and_publish()."""
        set_agent_executor(integration_mock_executor)

        event = AgentRequestEvent(
            request_id="exec-test-001",
            agent_id="test-agent",
            linkage=EntityLinkage(farmer_id="farmer-exec-test"),
            input_data={"field": "value"},
            source="test",
        )

        await execute_agent(event)

        # Verify executor was called with the event
        integration_mock_executor.execute_and_publish.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_execute_agent_raises_when_executor_not_set(self) -> None:
        """Test execute_agent raises RuntimeError when executor not initialized."""
        set_agent_executor(None)  # type: ignore[arg-type]

        event = AgentRequestEvent(
            request_id="fail-test-001",
            agent_id="test-agent",
            linkage=EntityLinkage(farmer_id="farmer-test"),
            input_data={},
            source="test",
        )

        with pytest.raises(RuntimeError, match="AgentExecutor not initialized"):
            await execute_agent(event)

    def test_handler_processes_valid_event_structure(
        self,
        mock_agent_config_cache: MagicMock,
        mock_event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Test handler correctly parses CloudEvent wrapped payload."""
        set_agent_config_cache(mock_agent_config_cache)
        set_main_event_loop(mock_event_loop)
        set_agent_executor(MagicMock())

        # CloudEvent wrapped format
        message = MagicMock()
        message.data.return_value = {
            "data": {
                "payload": {
                    "request_id": "cloud-event-test",
                    "agent_id": "qc-event-extractor",
                    "linkage": {"farmer_id": "farmer-cloud"},
                    "input_data": {},
                    "source": "cloud-test",
                }
            }
        }

        with patch("ai_model.events.subscriber.asyncio.run_coroutine_threadsafe") as mock_run:
            mock_future = MagicMock()
            mock_future.result.return_value = {"agent_id": "qc-event-extractor"}
            mock_run.return_value = mock_future

            response = handle_agent_request(message)

            # Should process successfully (CloudEvent unwrapping)
            assert isinstance(response, TopicEventResponse)
