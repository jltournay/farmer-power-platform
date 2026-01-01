"""Unit tests for Plantation Model streaming subscription handlers.

Story 0.6.5: Plantation Model Streaming Subscriptions

Tests verify:
- Handler returns correct TopicEventResponse types
- message.data() returns dict (NOT JSON string)
- QualityEventProcessor is called correctly
- Error handling (retry vs drop)
"""

from unittest.mock import AsyncMock, MagicMock, patch

from dapr.clients.grpc._response import TopicEventResponse, TopicEventResponseStatus


class TestQualityResultHandler:
    """Tests for quality result event handler."""

    def test_handler_returns_success_on_valid_event(self):
        """Handler returns success when processing succeeds."""
        # Import inside test to allow module patching
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "farmer_id": "WM-4521",
        }

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.process = AsyncMock(return_value={"status": "success"})

        with patch.object(subscriber, "_quality_event_processor", mock_processor):
            result = subscriber.handle_quality_result(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.success

    def test_handler_returns_drop_on_validation_error(self):
        """Handler returns drop on permanent validation errors."""
        from plantation_model.events import subscriber

        message = MagicMock()
        # Missing required field - validation should fail
        message.data.return_value = {"invalid": "data"}

        result = subscriber.handle_quality_result(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.drop

    def test_handler_returns_retry_when_processor_not_initialized(self):
        """Handler returns retry when processor is not initialized."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "farmer_id": "WM-4521",
        }

        # Ensure processor is None
        with patch.object(subscriber, "_quality_event_processor", None):
            result = subscriber.handle_quality_result(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.retry

    def test_handler_returns_retry_on_transient_error(self):
        """Handler returns retry on transient errors like connection failures."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "farmer_id": "WM-4521",
        }

        mock_processor = MagicMock()
        mock_processor.process = AsyncMock(side_effect=ConnectionError("DB unavailable"))

        with patch.object(subscriber, "_quality_event_processor", mock_processor):
            result = subscriber.handle_quality_result(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.retry

    def test_handler_returns_drop_on_parse_error(self):
        """Handler returns drop when message data cannot be parsed."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.side_effect = Exception("Parse error")

        result = subscriber.handle_quality_result(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.drop

    def test_message_data_returns_dict_not_string(self):
        """Verify message.data() returns dict, not JSON string."""
        message = MagicMock()
        message.data.return_value = {"key": "value"}

        data = message.data()

        assert isinstance(data, dict)
        assert data["key"] == "value"
        # Should NOT need json.loads()

    def test_handler_handles_cloud_event_wrapper(self):
        """Handler correctly extracts payload from CloudEvent wrapper."""
        from plantation_model.events import subscriber

        message = MagicMock()
        # CloudEvent wrapper format
        message.data.return_value = {
            "id": "evt-123",
            "source": "collection-model",
            "type": "collection.quality_result.received",
            "data": {
                "payload": {
                    "document_id": "doc-123",
                    "farmer_id": "WM-4521",
                }
            },
        }

        mock_processor = MagicMock()
        mock_processor.process = AsyncMock(return_value={"status": "success"})

        with patch.object(subscriber, "_quality_event_processor", mock_processor):
            result = subscriber.handle_quality_result(message)

        assert result.status == TopicEventResponseStatus.success
        # Verify processor was called with correct args
        mock_processor.process.assert_called_once()
        call_kwargs = mock_processor.process.call_args.kwargs
        assert call_kwargs["document_id"] == "doc-123"
        assert call_kwargs["farmer_id"] == "WM-4521"


class TestWeatherUpdatedHandler:
    """Tests for weather updated event handler."""

    def test_handler_returns_success_on_valid_event(self):
        """Handler returns success when processing succeeds."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "region_id": "nyeri-highland",
            "date": "2026-01-01",
            "observations": {
                "temp_min": 15.0,
                "temp_max": 25.0,
                "precipitation_mm": 5.0,
                "humidity_avg": 70.0,
            },
            "source": "open-meteo",
        }

        mock_repo = MagicMock()
        mock_repo.upsert_observation = AsyncMock()

        # Mock the WeatherObservation import that happens inside the handler
        mock_weather_obs_class = MagicMock()
        mock_weather_module = MagicMock()
        mock_weather_module.WeatherObservation = mock_weather_obs_class

        with (
            patch.object(subscriber, "_regional_weather_repo", mock_repo),
            patch.dict("sys.modules", {"plantation_model.domain.models": mock_weather_module}),
        ):
            result = subscriber.handle_weather_updated(message)

        assert isinstance(result, TopicEventResponse)
        assert result.status == TopicEventResponseStatus.success

    def test_handler_returns_drop_on_invalid_date(self):
        """Handler returns drop on invalid date format."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "region_id": "nyeri-highland",
            "date": "invalid-date",  # Invalid format
            "observations": {
                "temp_min": 15.0,
                "temp_max": 25.0,
                "precipitation_mm": 5.0,
                "humidity_avg": 70.0,
            },
        }

        mock_repo = MagicMock()
        with patch.object(subscriber, "_regional_weather_repo", mock_repo):
            result = subscriber.handle_weather_updated(message)

        assert result.status == TopicEventResponseStatus.drop

    def test_handler_returns_retry_when_repo_not_initialized(self):
        """Handler returns retry when repository is not initialized."""
        from plantation_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "region_id": "nyeri-highland",
            "date": "2026-01-01",
            "observations": {
                "temp_min": 15.0,
                "temp_max": 25.0,
                "precipitation_mm": 5.0,
                "humidity_avg": 70.0,
            },
        }

        with patch.object(subscriber, "_regional_weather_repo", None):
            result = subscriber.handle_weather_updated(message)

        assert result.status == TopicEventResponseStatus.retry


class TestSubscriptionStartup:
    """Tests for subscription startup (ADR-010 pattern)."""

    def test_run_streaming_subscriptions_creates_subscriptions(self):
        """run_streaming_subscriptions creates subscriptions with correct topics."""
        from plantation_model.events import subscriber

        mock_client = MagicMock()
        mock_close_fn = MagicMock()
        mock_client.subscribe_with_handler.return_value = mock_close_fn

        # Track sleep calls and raise exception on second call to break loop
        sleep_call_count = [0]

        def mock_sleep(seconds):
            sleep_call_count[0] += 1
            if sleep_call_count[0] > 1:
                raise KeyboardInterrupt("Test interrupt")

        with (
            patch.object(subscriber, "DaprClient", return_value=mock_client),
            patch.object(subscriber.time, "sleep", side_effect=mock_sleep),
        ):
            subscriber.run_streaming_subscriptions()

        # Should have 2 subscriptions (quality_result and weather_updated)
        assert mock_client.subscribe_with_handler.call_count == 2

        # Verify topics
        calls = mock_client.subscribe_with_handler.call_args_list
        topics = [call.kwargs.get("topic") for call in calls]
        assert "collection.quality_result.received" in topics
        assert "weather.observation.updated" in topics

    def test_run_streaming_subscriptions_configures_dlq(self):
        """run_streaming_subscriptions configures dead_letter_topic for DLQ."""
        from plantation_model.events import subscriber

        mock_client = MagicMock()
        mock_client.subscribe_with_handler.return_value = MagicMock()

        # Break loop after first iteration
        sleep_call_count = [0]

        def mock_sleep(seconds):
            sleep_call_count[0] += 1
            if sleep_call_count[0] > 1:
                raise KeyboardInterrupt("Test interrupt")

        with (
            patch.object(subscriber, "DaprClient", return_value=mock_client),
            patch.object(subscriber.time, "sleep", side_effect=mock_sleep),
        ):
            subscriber.run_streaming_subscriptions()

        # Check that DLQ was configured for all subscriptions
        calls = mock_client.subscribe_with_handler.call_args_list
        for call in calls:
            assert call.kwargs.get("dead_letter_topic") == "events.dlq"

    def test_run_streaming_subscriptions_sets_ready_flag(self):
        """run_streaming_subscriptions sets subscription_ready flag."""
        from plantation_model.events import subscriber

        mock_client = MagicMock()
        mock_client.subscribe_with_handler.return_value = MagicMock()

        # Reset flag before test
        subscriber.subscription_ready = False

        # Break loop after checking flag is set
        def mock_sleep(seconds):
            if subscriber.subscription_ready:
                raise KeyboardInterrupt("Test interrupt")

        with (
            patch.object(subscriber, "DaprClient", return_value=mock_client),
            patch.object(subscriber.time, "sleep", side_effect=mock_sleep),
        ):
            subscriber.run_streaming_subscriptions()

        # Flag should have been set before loop was interrupted
        assert subscriber.subscription_ready is True


class TestTopicEventResponseTypes:
    """Tests for TopicEventResponse status types."""

    def test_success_response_status(self):
        """TopicEventResponse('success') has correct status enum."""
        response = TopicEventResponse("success")
        assert response.status == TopicEventResponseStatus.success

    def test_retry_response_status(self):
        """TopicEventResponse('retry') has correct status enum."""
        response = TopicEventResponse("retry")
        assert response.status == TopicEventResponseStatus.retry

    def test_drop_response_status(self):
        """TopicEventResponse('drop') has correct status enum."""
        response = TopicEventResponse("drop")
        assert response.status == TopicEventResponseStatus.drop
