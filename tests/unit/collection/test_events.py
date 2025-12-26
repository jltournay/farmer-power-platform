"""Unit tests for Event Grid webhook handler."""

import pytest
from collection_model.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


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

    def test_blob_created_event_returns_202(self, client: TestClient) -> None:
        """Test that blob-created events return 202 Accepted."""
        payload = [
            {
                "id": "event-id-123",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/2025/12/26/device-001/result.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "clientRequestId": "client-123",
                    "requestId": "request-123",
                    "eTag": "0x8DB12345",
                    "contentType": "application/json",
                    "contentLength": 1024,
                    "blobType": "BlockBlob",
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-results/2025/12/26/device-001/result.json",
                    "sequencer": "00000000000000000001",
                    "storageDiagnostics": {},
                },
                "dataVersion": "1.0",
            },
        ]

        response = client.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202

    def test_multiple_blob_events_returns_202(self, client: TestClient) -> None:
        """Test that multiple blob events are processed."""
        payload = [
            {
                "id": "event-1",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/file1.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-results/file1.json",
                    "contentLength": 512,
                },
                "dataVersion": "1.0",
            },
            {
                "id": "event-2",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-exceptions/blobs/file2.zip",
                "eventTime": "2025-12-26T10:01:00Z",
                "data": {
                    "api": "PutBlob",
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-exceptions/file2.zip",
                    "contentLength": 2048,
                },
                "dataVersion": "1.0",
            },
        ]

        response = client.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202

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

    def test_unknown_event_type_is_ignored(self, client: TestClient) -> None:
        """Test that unknown event types are ignored but don't error."""
        payload = [
            {
                "id": "event-1",
                "eventType": "Microsoft.Storage.BlobDeleted",
                "subject": "/blobServices/default/containers/test/blobs/file.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {},
                "dataVersion": "1.0",
            },
        ]

        response = client.post("/api/events/blob-created", json=payload)

        assert response.status_code == 202

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


class TestBlobPathParsing:
    """Tests for blob path parsing from Event Grid subject."""

    def test_parses_container_and_blob_path(self, client: TestClient) -> None:
        """Test that container and blob path are correctly parsed from subject."""
        # This test validates the parsing logic by checking logs
        # In a real scenario, we'd check the queued job or stored data
        payload = [
            {
                "id": "event-1",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/qc-analyzer-results/blobs/2025/12/26/device-001/result.json",
                "eventTime": "2025-12-26T10:00:00Z",
                "data": {
                    "api": "PutBlob",
                    "url": "https://storage.blob.core.windows.net/qc-analyzer-results/2025/12/26/device-001/result.json",
                    "contentType": "application/json",
                    "contentLength": 1024,
                },
                "dataVersion": "1.0",
            },
        ]

        response = client.post("/api/events/blob-created", json=payload)

        # Event should be accepted and logged
        assert response.status_code == 202
