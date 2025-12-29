"""HTTP API clients for E2E testing.

Note: Most Plantation Model operations are gRPC-only. Use PlantationMCPClient
from mcp_clients.py for factory/farmer/region operations.
"""

from typing import Any

import httpx


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
    - /api/events/blob-created - Azure Event Grid blob trigger
    - /api/v1/triggers/job/{source_id} - Manual job trigger

    Documents are created through events, NOT direct CRUD APIs.
    Use MongoDBDirectClient to query documents directly, or
    CollectionMCPClient for MCP tool access.
    """

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CollectionClient":
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

    # =========================================================================
    # Event Grid Blob Trigger API
    # =========================================================================

    async def trigger_blob_event(
        self,
        container: str,
        blob_path: str,
        content_length: int = 1024,
        etag: str | None = None,
        event_id: str | None = None,
    ) -> bool:
        """Trigger a blob-created event to start ingestion.

        This simulates an Azure Event Grid blob-created event, which is the
        primary way documents enter the Collection Model.

        Args:
            container: The blob container name (must match a source_config landing_container)
            blob_path: The path to the blob within the container
            content_length: Size of the blob in bytes
            etag: Optional blob ETag for idempotency
            event_id: Optional event ID

        Returns:
            True if the event was accepted (202), False otherwise
        """
        import uuid

        event = [
            {
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
        ]

        response = await self.client.post("/api/events/blob-created", json=event)
        return response.status_code == 202

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
