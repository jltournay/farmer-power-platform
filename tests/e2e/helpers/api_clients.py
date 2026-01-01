"""HTTP API clients for E2E testing.

Note: Most Plantation Model operations are gRPC-only. Use PlantationMCPClient
from mcp_clients.py for factory/farmer/region operations.

Story 0.6.6: Updated to use DAPR pub/sub for blob events (streaming subscriptions).
"""

from typing import Any

import httpx

# Default DAPR HTTP port for Collection Model sidecar (exposed via docker-compose)
COLLECTION_DAPR_HTTP_PORT = 3502


class PlantationClient:
    """HTTP client for Plantation Model health endpoints.

    The Plantation Model only exposes HTTP endpoints for:
    - /health - Kubernetes liveness probe
    - /ready - Kubernetes readiness probe
    - /api/v1/events/* - DAPR Pub/Sub event handlers

    All data operations (factories, farmers, regions) are gRPC-only.
    Use PlantationMCPClient for MCP tool access to this data.
    """

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PlantationClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    async def health(self) -> dict[str, Any]:
        """Check service health (Kubernetes liveness probe)."""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def ready(self) -> dict[str, Any]:
        """Check service readiness (Kubernetes readiness probe)."""
        response = await self.client.get("/ready")
        response.raise_for_status()
        return response.json()


class CollectionClient:
    """HTTP client for Collection Model API.

    The Collection Model exposes HTTP endpoints for:
    - /health - Kubernetes liveness probe
    - /ready - Kubernetes readiness probe
    - /api/events/blob-created - Azure Event Grid blob trigger (kept for backward compat)
    - /api/v1/triggers/job/{source_id} - Manual job trigger

    Story 0.6.6: Blob events are now primarily delivered via DAPR pub/sub
    streaming subscriptions. The trigger_blob_event method publishes to
    DAPR's 'blob.created' topic.

    Documents are created through events, NOT direct CRUD APIs.
    Use MongoDBDirectClient to query documents directly, or
    CollectionMCPClient for MCP tool access.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        dapr_http_port: int = COLLECTION_DAPR_HTTP_PORT,
    ):
        self.base_url = base_url
        self.dapr_base_url = f"http://localhost:{dapr_http_port}"
        self._client: httpx.AsyncClient | None = None
        self._dapr_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CollectionClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        self._dapr_client = httpx.AsyncClient(base_url=self.dapr_base_url, timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
        if self._dapr_client:
            await self._dapr_client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    @property
    def dapr_client(self) -> httpx.AsyncClient:
        if self._dapr_client is None:
            raise RuntimeError("DAPR client not initialized. Use async context manager.")
        return self._dapr_client

    async def health(self) -> dict[str, Any]:
        """Check service health (Kubernetes liveness probe)."""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def ready(self) -> dict[str, Any]:
        """Check service readiness (Kubernetes readiness probe)."""
        response = await self.client.get("/ready")
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Blob Event Trigger via DAPR Pub/Sub (Story 0.6.6)
    # =========================================================================

    async def trigger_blob_event(
        self,
        container: str,
        blob_path: str,
        content_length: int = 1024,
        etag: str | None = None,
        event_id: str | None = None,
    ) -> bool:
        """Trigger a blob-created event via DAPR pub/sub.

        Story 0.6.6: This now publishes to DAPR's 'blob.created' topic
        instead of calling the HTTP endpoint. Collection Model receives
        the event via streaming subscription.

        The event format matches Azure Event Grid blob-created events.

        Args:
            container: The blob container name (must match a source_config landing_container)
            blob_path: The path to the blob within the container
            content_length: Size of the blob in bytes
            etag: Optional blob ETag for idempotency
            event_id: Optional event ID

        Returns:
            True if the event was published successfully
        """
        import uuid

        # Create Azure Event Grid format event
        event = {
            "id": event_id or str(uuid.uuid4()),
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": f"/blobServices/default/containers/{container}/blobs/{blob_path}",
            "eventTime": "2025-01-01T00:00:00Z",
            "data": {
                "contentLength": content_length,
                "eTag": etag or f'"0x{uuid.uuid4().hex[:16].upper()}"',
                "contentType": "application/json",
                "blobType": "BlockBlob",
                "url": f"http://azurite:10000/devstoreaccount1/{container}/{blob_path}",
            },
            "dataVersion": "",
            "metadataVersion": "1",
        }

        # Publish to DAPR pub/sub topic 'blob.created'
        # DAPR HTTP API: POST /v1.0/publish/{pubsub-name}/{topic}
        response = await self.dapr_client.post(
            "/v1.0/publish/pubsub/blob.created",
            json=event,
            headers={"Content-Type": "application/json"},
        )

        # DAPR returns 204 No Content on successful publish
        return response.status_code in (200, 204)

    # =========================================================================
    # DAPR Pull Job Trigger API
    # =========================================================================

    async def trigger_pull_job(self, source_id: str) -> dict[str, Any]:
        """Trigger a pull job manually (simulates DAPR scheduled job callback).

        Args:
            source_id: The source configuration ID to trigger

        Returns:
            JobTriggerResponse with success, fetched, failed counts
        """
        response = await self.client.post(f"/api/v1/triggers/job/{source_id}")
        response.raise_for_status()
        return response.json()
