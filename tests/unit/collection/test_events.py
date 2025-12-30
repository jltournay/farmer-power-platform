"""Unit tests for Event Grid webhook handler."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.api.events import (
    _parse_event_subject,
    _process_blob_created_event,
)
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.main import app
from collection_model.services.source_config_service import SourceConfigService
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collection_model.domain.ingestion_job import IngestionJob


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_source_config_service() -> MagicMock:
    """Create a mock SourceConfigService."""
    service = MagicMock(spec=SourceConfigService)
    service.get_config_by_container = AsyncMock(return_value=None)
    service.extract_path_metadata = MagicMock(return_value={})
    return service


@pytest.fixture
def mock_ingestion_queue() -> MagicMock:
    """Create a mock IngestionQueue."""
    queue = MagicMock(spec=IngestionQueue)
    queue.queue_job = AsyncMock(return_value=True)
    return queue


@pytest.fixture
def client_with_services(
    mock_source_config_service: MagicMock,
    mock_ingestion_queue: MagicMock,
) -> TestClient:
    """Create a test client with mocked services in app state."""
    app.state.source_config_service = mock_source_config_service
    app.state.ingestion_queue = mock_ingestion_queue
    yield TestClient(app)
    # Cleanup
    if hasattr(app.state, "source_config_service"):
        delattr(app.state, "source_config_service")
    if hasattr(app.state, "ingestion_queue"):
        delattr(app.state, "ingestion_queue")


class TestEventGridWebhook:
    """Tests for the /api/events/blob-created endpoint."""

    def test_subscription_validation_returns_validation_response(self, client: TestClient) -> None:
        """Test that subscription validation returns the validation code."""
        validation_code = "test-validation-code-12345"
        payload = [
            {
                "id": "test-id",
                "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
                "subject": "",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "validationCode": validation_code,
                    "validationUrl": None,
                },
                "dataVersion": "1.0",
            },
        ]

        response = client.post("/api/events/blob-created", json=payload)

        assert response.status_code == 200
        assert response.json() == {"validationResponse": validation_code}

    def test_empty_array_returns_202(self, client: TestClient) -> None:
        """Test that empty event array returns 202."""
        response = client.post("/api/events/blob-created", json=[])
        assert response.status_code == 202

    def test_invalid_json_returns_400(self, client: TestClient) -> None:
        """Test that invalid JSON returns 400."""
        response = client.post(
            "/api/events/blob-created",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_non_array_body_returns_400(self, client: TestClient) -> None:
        """Test that non-array body returns 400."""
        response = client.post(
            "/api/events/blob-created",
            json={"single": "object"},
        )
        assert response.status_code == 400

    def test_subscription_validation_missing_code_returns_400(self, client: TestClient) -> None:
        """Test that missing validation code returns 400."""
        payload = [
            {
                "id": "test-id",
                "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
                "subject": "",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {},  # Missing validationCode
                "dataVersion": "1.0",
            },
        ]
        response = client.post("/api/events/blob-created", json=payload)
        assert response.status_code == 400


class TestBlobCreatedEventProcessing:
    """Tests for blob-created event processing with services."""

    def test_blob_created_event_returns_202_with_services(
        self,
        client_with_services: TestClient,
        mock_source_config_service: MagicMock,
    ) -> None:
        """Test that blob-created events return 202 when services are initialized."""
        # Configure mock to return no matching config (unmatched event)
        mock_source_config_service.get_config_by_container.return_value = None

        payload = [
            {
                "id": "event-id-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/result.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "eTag": "0x8DB12345",
                    "contentLength": 1024,
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-results/result.json",
                },
                "dataVersion": "1.0",
            },
        ]

        response = client_with_services.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202
        mock_source_config_service.get_config_by_container.assert_called_once_with("qc-analyzer-results")

    def test_blob_created_event_queues_job_when_config_matches(
        self,
        client_with_services: TestClient,
        mock_source_config_service: MagicMock,
        mock_ingestion_queue: MagicMock,
    ) -> None:
        """Test that matching config results in job being queued."""
        # Configure mock to return a matching config
        mock_source_config_service.get_config_by_container.return_value = {
            "source_id": "qc-analyzer",
            "enabled": True,
            "ingestion": {
                "mode": "blob_trigger",
                "landing_container": "qc-analyzer-results",
            },
        }
        mock_source_config_service.extract_path_metadata.return_value = {"batch_id": "batch-001"}

        payload = [
            {
                "id": "event-id-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/batch-001.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "eTag": "0x8DB12345",
                    "contentLength": 1024,
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-results/batch-001.json",
                },
                "dataVersion": "1.0",
            },
        ]

        response = client_with_services.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202
        mock_ingestion_queue.queue_job.assert_called_once()

        # Verify the job that was queued
        queued_job: IngestionJob = mock_ingestion_queue.queue_job.call_args[0][0]
        assert queued_job.blob_path == "batch-001.json"
        assert queued_job.source_id == "qc-analyzer"
        assert queued_job.container == "qc-analyzer-results"
        assert queued_job.metadata == {"batch_id": "batch-001"}

    def test_blob_created_event_skips_disabled_source(
        self,
        client_with_services: TestClient,
        mock_source_config_service: MagicMock,
        mock_ingestion_queue: MagicMock,
    ) -> None:
        """Test that disabled source config doesn't queue job."""
        mock_source_config_service.get_config_by_container.return_value = {
            "source_id": "qc-analyzer",
            "enabled": False,  # Disabled
        }

        payload = [
            {
                "id": "event-id-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/result.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "eTag": "0x8DB12345",
                    "contentLength": 1024,
                },
                "dataVersion": "1.0",
            },
        ]

        response = client_with_services.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202
        mock_ingestion_queue.queue_job.assert_not_called()

    def test_duplicate_event_not_queued_again(
        self,
        client_with_services: TestClient,
        mock_source_config_service: MagicMock,
        mock_ingestion_queue: MagicMock,
    ) -> None:
        """Test that duplicate events are detected (queue returns False)."""
        mock_source_config_service.get_config_by_container.return_value = {
            "source_id": "qc-analyzer",
            "enabled": True,
        }
        # Simulate duplicate - queue_job returns False
        mock_ingestion_queue.queue_job.return_value = False

        payload = [
            {
                "id": "event-id-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/result.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "eTag": "0x8DB12345",
                    "contentLength": 1024,
                },
                "dataVersion": "1.0",
            },
        ]

        response = client_with_services.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202
        # Verify queue_job was called (but returned False for duplicate)
        mock_ingestion_queue.queue_job.assert_called_once()


class TestBlobPathParsing:
    """Tests for blob path parsing from Event Grid subject."""

    def test_parses_container_and_blob_path(self) -> None:
        """Test correct parsing of container and blob path."""
        subject = "/blobServices/default/containers/qc-analyzer-results/blobs/2025/12/26/result.json"
        container, blob_path = _parse_event_subject(subject)

        assert container == "qc-analyzer-results"
        assert blob_path == "2025/12/26/result.json"

    def test_parses_simple_blob_path(self) -> None:
        """Test parsing with simple blob path."""
        subject = "/blobServices/default/containers/test-container/blobs/file.json"
        container, blob_path = _parse_event_subject(subject)

        assert container == "test-container"
        assert blob_path == "file.json"

    def test_returns_empty_for_invalid_format(self) -> None:
        """Test returns empty strings for invalid format."""
        subject = "invalid-format"
        container, blob_path = _parse_event_subject(subject)

        assert container == ""
        assert blob_path == ""

    def test_returns_empty_for_missing_blobs(self) -> None:
        """Test returns empty strings when /blobs/ is missing."""
        subject = "/blobServices/default/containers/test-container/file.json"
        container, blob_path = _parse_event_subject(subject)

        assert container == ""
        assert blob_path == ""


class TestProcessBlobCreatedEvent:
    """Tests for the _process_blob_created_event function."""

    @pytest.mark.asyncio
    async def test_process_event_extracts_trace_id(self) -> None:
        """Test that trace_id is passed to the job."""
        mock_service = MagicMock(spec=SourceConfigService)
        mock_service.get_config_by_container = AsyncMock(
            return_value={
                "source_id": "test",
                "enabled": True,
            }
        )
        mock_service.extract_path_metadata = MagicMock(return_value={})

        mock_queue = MagicMock(spec=IngestionQueue)
        mock_queue.queue_job = AsyncMock(return_value=True)

        event = {
            "id": "event-123",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/test/blobs/file.json",
            "data": {
                "eTag": "0x123",
                "contentLength": 100,
            },
        }

        result = await _process_blob_created_event(
            event=event,
            source_config_service=mock_service,
            ingestion_queue=mock_queue,
            trace_id="00-abc123-def456-01",
        )

        assert result is True

        # Verify trace_id was passed to the job
        queued_job: IngestionJob = mock_queue.queue_job.call_args[0][0]
        assert queued_job.trace_id == "00-abc123-def456-01"

    @pytest.mark.asyncio
    async def test_process_event_unmatched_container(self) -> None:
        """Test processing event with no matching config."""
        mock_service = MagicMock(spec=SourceConfigService)
        mock_service.get_config_by_container = AsyncMock(return_value=None)

        mock_queue = MagicMock(spec=IngestionQueue)

        event = {
            "id": "event-123",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/unknown/blobs/file.json",
            "data": {"eTag": "0x123", "contentLength": 100},
        }

        result = await _process_blob_created_event(
            event=event,
            source_config_service=mock_service,
            ingestion_queue=mock_queue,
            trace_id=None,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_process_event_calls_metrics_on_success(self) -> None:
        """Test that metrics increment functions are called on successful queue."""
        mock_service = MagicMock(spec=SourceConfigService)
        mock_service.get_config_by_container = AsyncMock(
            return_value={
                "source_id": "test-source",
                "enabled": True,
            }
        )
        mock_service.extract_path_metadata = MagicMock(return_value={})

        mock_queue = MagicMock(spec=IngestionQueue)
        mock_queue.queue_job = AsyncMock(return_value=True)

        event = {
            "id": "event-123",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/test/blobs/file.json",
            "data": {"eTag": "0x123", "contentLength": 100},
        }

        mock_metrics = MagicMock()
        result = await _process_blob_created_event(
            event=event,
            source_config_service=mock_service,
            ingestion_queue=mock_queue,
            trace_id=None,
            event_metrics=mock_metrics,
        )

        assert result is True
        mock_metrics.increment_queued.assert_called_once_with("test-source")

    @pytest.mark.asyncio
    async def test_process_event_calls_metrics_on_duplicate(self) -> None:
        """Test that duplicate metric is called when queue returns False."""
        mock_service = MagicMock(spec=SourceConfigService)
        mock_service.get_config_by_container = AsyncMock(
            return_value={
                "source_id": "test-source",
                "enabled": True,
            }
        )
        mock_service.extract_path_metadata = MagicMock(return_value={})

        mock_queue = MagicMock(spec=IngestionQueue)
        mock_queue.queue_job = AsyncMock(return_value=False)  # Duplicate

        event = {
            "id": "event-123",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/test/blobs/file.json",
            "data": {"eTag": "0x123", "contentLength": 100},
        }

        mock_metrics = MagicMock()
        result = await _process_blob_created_event(
            event=event,
            source_config_service=mock_service,
            ingestion_queue=mock_queue,
            trace_id=None,
            event_metrics=mock_metrics,
        )

        assert result is False
        mock_metrics.increment_duplicate.assert_called_once_with("test-source")

    @pytest.mark.asyncio
    async def test_process_event_calls_metrics_on_unmatched(self) -> None:
        """Test that unmatched metric is called when no config found."""
        mock_service = MagicMock(spec=SourceConfigService)
        mock_service.get_config_by_container = AsyncMock(return_value=None)

        mock_queue = MagicMock(spec=IngestionQueue)

        event = {
            "id": "event-123",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/unknown-container/blobs/file.json",
            "data": {"eTag": "0x123", "contentLength": 100},
        }

        mock_metrics = MagicMock()
        result = await _process_blob_created_event(
            event=event,
            source_config_service=mock_service,
            ingestion_queue=mock_queue,
            trace_id=None,
            event_metrics=mock_metrics,
        )

        assert result is False
        mock_metrics.increment_unmatched.assert_called_once_with("unknown-container")
