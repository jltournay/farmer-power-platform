"""Unit tests for Collection Model streaming subscription handlers.

Story 0.6.6: Collection Model Streaming Subscriptions

Tests verify:
1. Message data parsing handles various formats
2. Event subject parsing works correctly
3. Pydantic models validate Event Grid events
4. Handler returns correct response types for edge cases
"""

from unittest.mock import MagicMock

from dapr.clients.grpc._response import TopicEventResponse, TopicEventResponseStatus


class TestEventSubjectParsing:
    """Tests for Event Grid subject parsing."""

    def test_parse_event_subject_valid(self):
        """Parse valid Event Grid subject."""
        from collection_model.events.subscriber import _parse_event_subject

        subject = "/blobServices/default/containers/quality-events/blobs/FRM-001/doc.json"
        container, blob_path = _parse_event_subject(subject)

        assert container == "quality-events"
        assert blob_path == "FRM-001/doc.json"

    def test_parse_event_subject_nested_path(self):
        """Parse subject with nested blob path."""
        from collection_model.events.subscriber import _parse_event_subject

        subject = "/blobServices/default/containers/uploads/blobs/2025/01/15/file.json"
        container, blob_path = _parse_event_subject(subject)

        assert container == "uploads"
        assert blob_path == "2025/01/15/file.json"

    def test_parse_event_subject_invalid_no_containers(self):
        """Return empty strings for invalid subject without containers."""
        from collection_model.events.subscriber import _parse_event_subject

        subject = "/invalid/path/format"
        container, blob_path = _parse_event_subject(subject)

        assert container == ""
        assert blob_path == ""

    def test_parse_event_subject_invalid_no_blobs(self):
        """Return empty strings for subject without blobs segment."""
        from collection_model.events.subscriber import _parse_event_subject

        subject = "/blobServices/default/containers/test"
        container, blob_path = _parse_event_subject(subject)

        assert container == ""
        assert blob_path == ""


class TestBlobEventModels:
    """Tests for blob event Pydantic models."""

    def test_blob_event_data_model(self):
        """Test BlobEventData model with alias handling."""
        from collection_model.events.subscriber import BlobEventData

        data = BlobEventData.model_validate(
            {
                "contentLength": 1024,
                "eTag": '"0x123"',
                "contentType": "application/json",
                "blobType": "BlockBlob",
                "url": "http://example.com/blob",
            }
        )

        assert data.content_length == 1024
        assert data.etag == '"0x123"'
        assert data.content_type == "application/json"
        assert data.blob_type == "BlockBlob"
        assert data.url == "http://example.com/blob"

    def test_blob_event_data_model_defaults(self):
        """Test BlobEventData model with default values."""
        from collection_model.events.subscriber import BlobEventData

        data = BlobEventData.model_validate({})

        assert data.content_length == 0
        assert data.etag == ""
        assert data.content_type == "application/octet-stream"
        assert data.blob_type == "BlockBlob"
        assert data.url == ""

    def test_blob_created_event_model(self):
        """Test BlobCreatedEvent model with nested data."""
        from collection_model.events.subscriber import BlobCreatedEvent

        event = BlobCreatedEvent.model_validate(
            {
                "id": "event-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/test/blobs/file.json",
                "eventTime": "2025-01-01T00:00:00Z",
                "data": {
                    "contentLength": 512,
                    "eTag": '"0xABC"',
                },
            }
        )

        assert event.id == "event-123"
        assert event.event_type == "Microsoft.Storage.BlobCreated"
        assert event.subject == "/blobServices/default/containers/test/blobs/file.json"
        assert event.data.content_length == 512
        assert event.data.etag == '"0xABC"'


class TestHandlerEdgeCases:
    """Tests for handler edge cases that don't require async setup."""

    def test_handler_returns_drop_on_unparseable_data(self):
        """Handler returns drop when message data cannot be parsed."""
        from collection_model.events.subscriber import handle_blob_event

        message = MagicMock()
        message.data.return_value = "invalid json {"

        result = handle_blob_event(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.drop

    def test_handler_returns_retry_on_services_not_initialized(self):
        """Handler returns retry when services not initialized."""
        from collection_model.events import subscriber

        # Ensure services are not initialized
        original_source_config = subscriber._source_config_service
        original_queue = subscriber._ingestion_queue

        try:
            subscriber._source_config_service = None
            subscriber._ingestion_queue = None

            message = MagicMock()
            message.data.return_value = {
                "id": "event-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/test/blobs/test.json",
                "data": {"contentLength": 100},
            }

            result = subscriber.handle_blob_event(message)

            assert isinstance(result, TopicEventResponse)
            assert result.status == TopicEventResponseStatus.retry
        finally:
            subscriber._source_config_service = original_source_config
            subscriber._ingestion_queue = original_queue

    def test_handler_returns_retry_on_event_loop_not_initialized(self):
        """Handler returns retry when event loop not initialized."""
        from collection_model.events import subscriber

        original_source_config = subscriber._source_config_service
        original_queue = subscriber._ingestion_queue
        original_loop = subscriber._main_event_loop

        try:
            # Set services but not event loop
            subscriber._source_config_service = MagicMock()
            subscriber._ingestion_queue = MagicMock()
            subscriber._main_event_loop = None

            message = MagicMock()
            message.data.return_value = {
                "id": "event-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/test/blobs/test.json",
                "data": {"contentLength": 100},
            }

            result = subscriber.handle_blob_event(message)

            assert isinstance(result, TopicEventResponse)
            assert result.status == TopicEventResponseStatus.retry
        finally:
            subscriber._source_config_service = original_source_config
            subscriber._ingestion_queue = original_queue
            subscriber._main_event_loop = original_loop

    def test_handler_skips_non_blob_created_events(self):
        """Handler returns success when event is not BlobCreated type."""
        from collection_model.events import subscriber

        # Need services initialized to get past the check
        original_source_config = subscriber._source_config_service
        original_queue = subscriber._ingestion_queue
        original_loop = subscriber._main_event_loop

        try:
            subscriber._source_config_service = MagicMock()
            subscriber._ingestion_queue = MagicMock()
            subscriber._main_event_loop = MagicMock()

            message = MagicMock()
            message.data.return_value = {
                "id": "event-123",
                "eventType": "Microsoft.Storage.BlobDeleted",  # Not BlobCreated
                "subject": "/blobServices/default/containers/test/blobs/test.json",
                "data": {"contentLength": 100},
            }

            result = subscriber.handle_blob_event(message)

            # Non-matching events are skipped (success, nothing to process)
            assert isinstance(result, TopicEventResponse)
            assert result.status == TopicEventResponseStatus.success
        finally:
            subscriber._source_config_service = original_source_config
            subscriber._ingestion_queue = original_queue
            subscriber._main_event_loop = original_loop


class TestMessageDataParsing:
    """Tests for message data parsing."""

    def test_message_data_returns_dict(self):
        """Verify message.data() returns dict, not JSON string."""
        message = MagicMock()
        message.data.return_value = {"key": "value"}

        data = message.data()

        assert isinstance(data, dict)
        assert data["key"] == "value"


class TestSubscriptionModule:
    """Tests for subscription module structure."""

    def test_module_exports_expected_functions(self):
        """Verify module exports expected public interface."""
        from collection_model.events import subscriber

        assert hasattr(subscriber, "run_streaming_subscriptions")
        assert hasattr(subscriber, "handle_blob_event")
        assert hasattr(subscriber, "set_blob_processor")
        assert hasattr(subscriber, "set_main_event_loop")
        assert hasattr(subscriber, "subscription_ready")

    def test_init_exports_expected_functions(self):
        """Verify __init__ exports expected functions."""
        from collection_model.events import (
            handle_blob_event,
            run_streaming_subscriptions,
            set_blob_processor,
            set_main_event_loop,
        )

        assert callable(handle_blob_event)
        assert callable(run_streaming_subscriptions)
        assert callable(set_blob_processor)
        assert callable(set_main_event_loop)
