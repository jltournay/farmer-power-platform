"""Unit tests for Dead Letter Queue handler.

Story 0.6.8: Dead Letter Queue Handler (ADR-006)

Tests:
- DLQHandler stores events correctly in MongoDB
- DLQHandler increments OpenTelemetry metrics
- DLQHandler extracts original topic from message
- handle_dead_letter function uses module-level state correctly
- DLQRepository stores and queries events correctly
"""

import asyncio
import threading
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events.dlq_handler import (
    DLQHandler,
    handle_dead_letter,
)
from fp_common.events.dlq_repository import DLQRecord, DLQRepository


def _is_success_response(response: TopicEventResponse) -> bool:
    """Check if TopicEventResponse indicates success."""
    # Handle both string comparison and enum comparison
    status = response.status
    if hasattr(status, "name"):
        return status.name.lower() == "success"
    return str(status).lower() == "success"


def _is_retry_response(response: TopicEventResponse) -> bool:
    """Check if TopicEventResponse indicates retry."""
    status = response.status
    if hasattr(status, "name"):
        return status.name.lower() == "retry"
    return str(status).lower() == "retry"


class TestDLQHandler:
    """Tests for DLQHandler class."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock DLQ repository."""
        repo = MagicMock(spec=DLQRepository)
        repo.store_failed_event = AsyncMock(return_value="mock-doc-id-123")
        return repo

    @pytest.fixture
    def running_event_loop(self):
        """Create and run an event loop in a background thread for testing."""
        loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

        yield loop

        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=1)
        loop.close()

    @pytest.fixture
    def handler(self, mock_repository, running_event_loop):
        """Create a DLQHandler with mocked dependencies."""
        return DLQHandler(
            repository=mock_repository,
            event_loop=running_event_loop,
        )

    def test_handler_stores_event_in_mongodb(self, handler, mock_repository):
        """Handler stores failed event in MongoDB."""
        # Arrange
        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "error": "validation_failed",
        }
        message.topic.return_value = "collection.quality_result.received"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter") as mock_counter:
            result = handler.handle(message)

        # Assert
        assert _is_success_response(result)
        mock_repository.store_failed_event.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_repository.store_failed_event.call_args[1]
        assert call_kwargs["event_data"]["document_id"] == "doc-123"
        assert call_kwargs["original_topic"] == "collection.quality_result.received"

    def test_handler_increments_metric(self, handler, mock_repository):
        """Handler increments DLQ counter metric."""
        # Arrange
        message = MagicMock()
        message.data.return_value = {"test": "data"}
        message.topic.return_value = "test.topic"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter") as mock_counter:
            result = handler.handle(message)

        # Assert
        mock_counter.add.assert_called_once_with(1, {"topic": "test.topic"})

    def test_handler_extracts_original_topic(self, handler, mock_repository):
        """Handler extracts original topic from message."""
        # Arrange
        message = MagicMock()
        message.data.return_value = {"data": "value"}
        message.topic.return_value = "original.topic.name"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter"):
            handler.handle(message)

        # Verify call arguments
        call_kwargs = mock_repository.store_failed_event.call_args[1]
        assert call_kwargs["original_topic"] == "original.topic.name"

    def test_handler_handles_string_data(self, handler, mock_repository):
        """Handler handles message.data() returning a JSON string."""
        # Arrange
        message = MagicMock()
        message.data.return_value = '{"document_id": "doc-456"}'
        message.topic.return_value = "test.topic"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter"):
            result = handler.handle(message)

        # Assert
        assert _is_success_response(result)
        call_kwargs = mock_repository.store_failed_event.call_args[1]
        assert call_kwargs["event_data"]["document_id"] == "doc-456"

    def test_handler_handles_bytes_data(self, handler, mock_repository):
        """Handler handles message.data() returning bytes."""
        # Arrange
        message = MagicMock()
        message.data.return_value = b'{"document_id": "doc-789"}'
        message.topic.return_value = "test.topic"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter"):
            result = handler.handle(message)

        # Assert
        assert _is_success_response(result)
        call_kwargs = mock_repository.store_failed_event.call_args[1]
        assert call_kwargs["event_data"]["document_id"] == "doc-789"

    def test_handler_handles_topic_not_callable(self, handler, mock_repository):
        """Handler handles message without callable topic() method."""
        # Arrange
        message = MagicMock()
        message.data.return_value = {"test": "data"}
        # topic is an attribute, not a method
        message.topic = "not-callable"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter"):
            result = handler.handle(message)

        # Assert
        assert _is_success_response(result)
        call_kwargs = mock_repository.store_failed_event.call_args[1]
        # Should fallback to "unknown"
        assert call_kwargs["original_topic"] == "unknown"

    def test_handler_continues_on_storage_failure(self, mock_repository, running_event_loop):
        """Handler returns success even if storage fails."""
        # Arrange
        mock_repository.store_failed_event = AsyncMock(side_effect=Exception("MongoDB connection failed"))
        handler = DLQHandler(repository=mock_repository, event_loop=running_event_loop)

        message = MagicMock()
        message.data.return_value = {"test": "data"}
        message.topic.return_value = "test.topic"

        # Act
        with patch("fp_common.events.dlq_handler.dlq_counter"):
            result = handler.handle(message)

        # Assert - still returns success (we don't retry DLQ forever)
        assert _is_success_response(result)


class TestHandleDeadLetterFunction:
    """Tests for module-level handle_dead_letter function."""

    def test_returns_retry_when_repository_not_set(self):
        """Function returns retry when repository is not initialized."""
        # Reset module state
        import fp_common.events.dlq_handler as dlq_module

        original_repo = dlq_module._dlq_repository
        dlq_module._dlq_repository = None

        try:
            message = MagicMock()
            message.data.return_value = {"test": "data"}

            with patch("fp_common.events.dlq_handler.dlq_counter"):
                result = handle_dead_letter(message)

            assert _is_retry_response(result)
        finally:
            dlq_module._dlq_repository = original_repo

    def test_returns_retry_when_event_loop_not_set(self):
        """Function returns retry when event loop is not initialized."""
        import fp_common.events.dlq_handler as dlq_module

        original_repo = dlq_module._dlq_repository
        original_loop = dlq_module._main_event_loop
        dlq_module._dlq_repository = MagicMock()
        dlq_module._main_event_loop = None

        try:
            message = MagicMock()
            message.data.return_value = {"test": "data"}

            with patch("fp_common.events.dlq_handler.dlq_counter"):
                result = handle_dead_letter(message)

            assert _is_retry_response(result)
        finally:
            dlq_module._dlq_repository = original_repo
            dlq_module._main_event_loop = original_loop


class TestDLQRepository:
    """Tests for DLQRepository class."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock MongoDB collection."""
        collection = AsyncMock()
        collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock-id-123"))
        collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        collection.find = MagicMock()
        collection.aggregate = MagicMock()
        return collection

    @pytest.fixture
    def repository(self, mock_collection):
        """Create a DLQRepository with mock collection."""
        return DLQRepository(mock_collection)

    @pytest.mark.asyncio
    async def test_store_failed_event_creates_document(self, repository, mock_collection):
        """store_failed_event creates MongoDB document with correct schema."""
        # Act
        doc_id = await repository.store_failed_event(
            event_data={"document_id": "doc-123"},
            original_topic="collection.quality_result.received",
        )

        # Assert
        assert doc_id == "mock-id-123"
        mock_collection.insert_one.assert_called_once()

        # Verify document structure
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["event"]["document_id"] == "doc-123"
        assert call_args["original_topic"] == "collection.quality_result.received"
        assert call_args["status"] == "pending_review"
        assert "received_at" in call_args
        assert call_args["replayed_at"] is None
        assert call_args["discard_reason"] is None

    @pytest.mark.asyncio
    async def test_mark_replayed_updates_status(self, repository, mock_collection):
        """mark_replayed updates status and timestamp."""
        # Use a valid ObjectId hex string (24 chars)
        valid_object_id = "507f1f77bcf86cd799439011"

        # Act
        result = await repository.mark_replayed(valid_object_id)

        # Assert
        assert result is True
        mock_collection.update_one.assert_called_once()

        # Verify update operation
        call_args = mock_collection.update_one.call_args
        update_doc = call_args[0][1]["$set"]
        assert update_doc["status"] == "replayed"
        assert "replayed_at" in update_doc

    @pytest.mark.asyncio
    async def test_mark_discarded_updates_status_and_reason(self, repository, mock_collection):
        """mark_discarded updates status and sets reason."""
        # Use a valid ObjectId hex string (24 chars)
        valid_object_id = "507f1f77bcf86cd799439012"

        # Act
        result = await repository.mark_discarded(valid_object_id, "Data too old")

        # Assert
        assert result is True
        mock_collection.update_one.assert_called_once()

        # Verify update operation
        call_args = mock_collection.update_one.call_args
        update_doc = call_args[0][1]["$set"]
        assert update_doc["status"] == "discarded"
        assert update_doc["discard_reason"] == "Data too old"

    @pytest.mark.asyncio
    async def test_mark_replayed_returns_false_when_not_found(self, repository, mock_collection):
        """mark_replayed returns False when document not found."""
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=0))
        # Use a valid ObjectId hex string (24 chars)
        valid_object_id = "507f1f77bcf86cd799439013"

        result = await repository.mark_replayed(valid_object_id)

        assert result is False


class TestDLQRecord:
    """Tests for DLQRecord Pydantic model."""

    def test_creates_with_defaults(self):
        """DLQRecord creates with default values."""
        record = DLQRecord(
            event={"key": "value"},
            original_topic="test.topic",
        )

        assert record.event == {"key": "value"}
        assert record.original_topic == "test.topic"
        assert record.status == "pending_review"
        assert record.replayed_at is None
        assert record.discard_reason is None
        assert isinstance(record.received_at, datetime)

    def test_model_dump_produces_correct_structure(self):
        """model_dump produces MongoDB-compatible structure."""
        record = DLQRecord(
            event={"document_id": "doc-123"},
            original_topic="test.topic",
            received_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        dumped = record.model_dump()

        assert dumped["event"] == {"document_id": "doc-123"}
        assert dumped["original_topic"] == "test.topic"
        assert dumped["status"] == "pending_review"
        assert dumped["received_at"] == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class TestDLQRepositoryQueries:
    """Tests for DLQRepository query methods."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock MongoDB collection with proper Motor cursor behavior."""
        collection = MagicMock()
        collection.create_index = AsyncMock()
        return collection

    @pytest.fixture
    def repository(self, mock_collection):
        """Create a DLQRepository with mock collection."""
        return DLQRepository(mock_collection)

    @pytest.mark.asyncio
    async def test_get_pending_events_returns_pending_records(self, repository, mock_collection):
        """get_pending_events returns records with pending_review status."""
        # Arrange - Motor find() returns cursor synchronously, to_list() is async
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {"_id": "id1", "status": "pending_review", "original_topic": "topic1"},
                {"_id": "id2", "status": "pending_review", "original_topic": "topic2"},
            ]
        )
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor

        # Act
        result = await repository.get_pending_events(limit=10)

        # Assert
        assert len(result) == 2
        mock_collection.find.assert_called_once_with({"status": "pending_review"})

    @pytest.mark.asyncio
    async def test_get_pending_events_with_topic_filter(self, repository, mock_collection):
        """get_pending_events filters by topic when provided."""
        # Arrange - Motor find() returns cursor synchronously
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor

        # Act
        await repository.get_pending_events(limit=10, topic_filter="collection.quality_result.received")

        # Assert
        mock_collection.find.assert_called_once_with(
            {
                "status": "pending_review",
                "original_topic": "collection.quality_result.received",
            }
        )

    @pytest.mark.asyncio
    async def test_count_by_status_aggregates_correctly(self, repository, mock_collection):
        """count_by_status returns counts grouped by status."""

        # Arrange - Motor aggregate() returns async iterator
        async def mock_aiter():
            for doc in [
                {"_id": "pending_review", "count": 5},
                {"_id": "replayed", "count": 3},
                {"_id": "discarded", "count": 1},
            ]:
                yield doc

        mock_collection.aggregate.return_value = mock_aiter()

        # Act
        result = await repository.count_by_status()

        # Assert
        assert result == {"pending_review": 5, "replayed": 3, "discarded": 1}

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_required_indexes(self, repository, mock_collection):
        """ensure_indexes creates indexes for efficient queries."""
        # Act
        await repository.ensure_indexes()

        # Assert - verify all 3 indexes are created
        assert mock_collection.create_index.call_count == 3
        call_args_list = [call[0][0] for call in mock_collection.create_index.call_args_list]
        assert "original_topic" in call_args_list
        assert "status" in call_args_list
        assert [("received_at", -1)] in call_args_list or "received_at" in str(call_args_list)
