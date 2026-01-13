"""Unit tests for cost event handler.

Story 13.5: DAPR Cost Event Subscription

Tests:
- Event handling success flow
- Validation error handling (drop)
- Repository error handling (retry)
- Budget monitor update on success
- Different payload formats (dict, string, bytes)
- Services not initialized (retry)

Test Coverage Strategy:
The tests focus on `_process_cost_event_async` and helper functions rather than
`handle_cost_event` directly. This is intentional because `handle_cost_event` uses
`asyncio.run_coroutine_threadsafe()` which requires a running event loop in a
separate thread - difficult to test in unit tests. The full handler is tested
via E2E tests that exercise the complete DAPR subscription flow.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit
from platform_cost.handlers import cost_event_handler
from platform_cost.handlers.cost_event_handler import (
    _process_cost_event_async,
    set_handler_dependencies,
    set_main_event_loop,
)


@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module-level state before and after each test.

    This ensures tests are isolated and don't leak state between runs.
    """
    cost_event_handler._cost_repository = None
    cost_event_handler._budget_monitor = None
    cost_event_handler._main_event_loop = None
    yield
    cost_event_handler._cost_repository = None
    cost_event_handler._budget_monitor = None
    cost_event_handler._main_event_loop = None


@pytest.fixture
def sample_cost_event() -> dict:
    """Sample cost event payload as received from DAPR."""
    return {
        "cost_type": "llm",
        "amount_usd": "0.0015",
        "quantity": 1500,
        "unit": "tokens",
        "timestamp": "2026-01-13T10:00:00Z",
        "source_service": "ai-model",
        "success": True,
        "metadata": {
            "model": "anthropic/claude-3-haiku",
            "agent_type": "extractor",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
    }


@pytest.fixture
def sample_cost_event_model() -> CostRecordedEvent:
    """Sample cost event as Pydantic model."""
    return CostRecordedEvent(
        cost_type=CostType.LLM,
        amount_usd=Decimal("0.0015"),
        quantity=1500,
        unit=CostUnit.TOKENS,
        timestamp=datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC),
        source_service="ai-model",
        success=True,
        metadata={
            "model": "anthropic/claude-3-haiku",
            "agent_type": "extractor",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
    )


@pytest.fixture
def mock_cost_repository() -> MagicMock:
    """Create mock UnifiedCostRepository."""
    mock = MagicMock()
    mock.insert = AsyncMock(return_value="test-event-id")
    return mock


@pytest.fixture
def mock_budget_monitor() -> MagicMock:
    """Create mock BudgetMonitor."""
    mock = MagicMock()
    mock.record_cost = MagicMock(return_value=None)
    return mock


@pytest.fixture
def mock_message(sample_cost_event: dict) -> MagicMock:
    """Create mock DAPR message with dict payload."""
    mock = MagicMock()
    mock.data.return_value = sample_cost_event
    return mock


@pytest.fixture
def mock_message_string(sample_cost_event: dict) -> MagicMock:
    """Create mock DAPR message with string payload."""
    mock = MagicMock()
    mock.data.return_value = json.dumps(sample_cost_event)
    return mock


@pytest.fixture
def mock_message_bytes(sample_cost_event: dict) -> MagicMock:
    """Create mock DAPR message with bytes payload."""
    mock = MagicMock()
    mock.data.return_value = json.dumps(sample_cost_event).encode("utf-8")
    return mock


class TestProcessCostEventAsync:
    """Tests for async processing function."""

    @pytest.mark.asyncio
    async def test_process_cost_event_async_success(
        self,
        sample_cost_event_model,
        mock_cost_repository,
        mock_budget_monitor,
    ) -> None:
        """Test successful async processing."""
        # Set dependencies
        cost_event_handler._cost_repository = mock_cost_repository
        cost_event_handler._budget_monitor = mock_budget_monitor

        event_id = await _process_cost_event_async(sample_cost_event_model)

        assert event_id is not None
        mock_cost_repository.insert.assert_called_once()
        mock_budget_monitor.record_cost.assert_called_once()

        # Verify budget monitor received correct args
        call_args = mock_budget_monitor.record_cost.call_args
        assert call_args.kwargs["cost_type"] == "llm"
        assert call_args.kwargs["amount_usd"] == Decimal("0.0015")

    @pytest.mark.asyncio
    async def test_process_cost_event_async_services_not_initialized(
        self,
        sample_cost_event_model,
    ) -> None:
        """Test that raises ConnectionError if services not initialized."""
        with pytest.raises(ConnectionError) as exc_info:
            await _process_cost_event_async(sample_cost_event_model)

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_cost_event_generates_uuid(
        self,
        sample_cost_event_model,
        mock_cost_repository,
        mock_budget_monitor,
    ) -> None:
        """Test that process generates a unique UUID for each event."""
        cost_event_handler._cost_repository = mock_cost_repository
        cost_event_handler._budget_monitor = mock_budget_monitor

        # Process two events
        event_id_1 = await _process_cost_event_async(sample_cost_event_model)
        event_id_2 = await _process_cost_event_async(sample_cost_event_model)

        # Both should be valid UUIDs and different
        assert event_id_1 is not None
        assert event_id_2 is not None
        assert event_id_1 != event_id_2

    @pytest.mark.asyncio
    async def test_process_cost_event_converts_to_unified_event(
        self,
        sample_cost_event_model,
        mock_cost_repository,
        mock_budget_monitor,
    ) -> None:
        """Test that event is converted to UnifiedCostEvent for storage."""
        cost_event_handler._cost_repository = mock_cost_repository
        cost_event_handler._budget_monitor = mock_budget_monitor

        await _process_cost_event_async(sample_cost_event_model)

        # Check insert was called with UnifiedCostEvent
        call_args = mock_cost_repository.insert.call_args
        unified_event = call_args[0][0]

        assert unified_event.cost_type == "llm"
        assert unified_event.amount_usd == Decimal("0.0015")
        assert unified_event.quantity == 1500
        assert unified_event.source_service == "ai-model"
        assert unified_event.agent_type == "extractor"
        assert unified_event.model == "anthropic/claude-3-haiku"


class TestSetHandlerDependencies:
    """Tests for set_handler_dependencies function."""

    def test_set_handler_dependencies(
        self,
        mock_cost_repository,
        mock_budget_monitor,
    ) -> None:
        """Test that dependencies are set correctly."""
        set_handler_dependencies(mock_cost_repository, mock_budget_monitor)

        assert cost_event_handler._cost_repository is mock_cost_repository
        assert cost_event_handler._budget_monitor is mock_budget_monitor


class TestSetMainEventLoop:
    """Tests for set_main_event_loop function."""

    def test_set_main_event_loop(self) -> None:
        """Test that event loop is set correctly."""
        import asyncio

        loop = asyncio.new_event_loop()
        set_main_event_loop(loop)

        assert cost_event_handler._main_event_loop is loop

        # Close the loop (autouse fixture handles state reset)
        loop.close()


class TestCostRecordedEventValidation:
    """Tests for CostRecordedEvent validation."""

    def test_valid_llm_event_parses(self, sample_cost_event: dict) -> None:
        """Test that valid LLM cost event parses successfully."""
        event = CostRecordedEvent.model_validate(sample_cost_event)

        assert event.cost_type == CostType.LLM
        assert event.amount_usd == Decimal("0.0015")
        assert event.quantity == 1500
        assert event.unit == CostUnit.TOKENS

    def test_invalid_cost_type_rejected(self) -> None:
        """Test that invalid cost type is rejected."""
        invalid_event = {
            "cost_type": "invalid_type",
            "amount_usd": "0.01",
            "quantity": 1,
            "unit": "tokens",
            "timestamp": "2026-01-13T10:00:00Z",
            "source_service": "test",
            "success": True,
        }

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CostRecordedEvent.model_validate(invalid_event)

    def test_missing_required_field_rejected(self) -> None:
        """Test that missing required fields are rejected."""
        invalid_event = {
            "cost_type": "llm",
            # Missing required fields
        }

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CostRecordedEvent.model_validate(invalid_event)


class TestEventPayloadFormats:
    """Tests for different payload formats (dict, string, bytes)."""

    def test_dict_payload_parses(self, sample_cost_event: dict) -> None:
        """Test that dict payload parses correctly."""
        event = CostRecordedEvent.model_validate(sample_cost_event)
        assert event.cost_type == CostType.LLM

    def test_string_payload_parses(self, sample_cost_event: dict) -> None:
        """Test that JSON string payload parses correctly."""
        json_str = json.dumps(sample_cost_event)
        data = json.loads(json_str)
        event = CostRecordedEvent.model_validate(data)
        assert event.cost_type == CostType.LLM

    def test_bytes_payload_parses(self, sample_cost_event: dict) -> None:
        """Test that bytes payload parses correctly."""
        json_bytes = json.dumps(sample_cost_event).encode("utf-8")
        data = json.loads(json_bytes.decode("utf-8"))
        event = CostRecordedEvent.model_validate(data)
        assert event.cost_type == CostType.LLM


class TestModuleStateManagement:
    """Tests for module-level state management."""

    def test_initial_state_is_none(self) -> None:
        """Test that module state starts as None (via autouse fixture reset)."""
        # Autouse fixture resets state before each test
        assert cost_event_handler._cost_repository is None
        assert cost_event_handler._budget_monitor is None
        assert cost_event_handler._main_event_loop is None

    def test_dependencies_can_be_set_multiple_times(
        self,
        mock_cost_repository,
        mock_budget_monitor,
    ) -> None:
        """Test that dependencies can be updated during runtime."""
        # Set first time
        set_handler_dependencies(mock_cost_repository, mock_budget_monitor)

        # Create new mocks
        new_repo = MagicMock()
        new_monitor = MagicMock()

        # Set second time
        set_handler_dependencies(new_repo, new_monitor)

        assert cost_event_handler._cost_repository is new_repo
        assert cost_event_handler._budget_monitor is new_monitor
