"""HTTP API clients for E2E testing.

Note: Most Plantation Model operations are gRPC-only. Use PlantationMCPClient
from mcp_clients.py for factory/farmer/region operations.

Story 0.6.6: Updated to use DAPR pub/sub for blob events (streaming subscriptions).
Story 0.5.4b: Added BFFClient for BFF API routes (farmer endpoints).
"""

from typing import Any

import httpx

# Default DAPR HTTP port for Collection Model sidecar (exposed via docker-compose)
COLLECTION_DAPR_HTTP_PORT = 3502

# Default E2E JWT secret (matches docker-compose.e2e.yaml)
E2E_JWT_SECRET = "test-secret-for-e2e"


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
        # 90s timeout: Open-Meteo API can be slow/unstable in CI environments
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=90.0)
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
        # 90s timeout: Open-Meteo API can be slow/unstable in CI environments
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=90.0)
        self._dapr_client = httpx.AsyncClient(base_url=self.dapr_base_url, timeout=90.0)
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

    async def cache_health(self) -> dict[str, Any]:
        """Check source config cache health (Story 0.6.9).

        Returns cache status including:
        - cache_size: Number of configs in cache
        - cache_age_seconds: How old the cache is
        - change_stream_active: Whether change stream is running
        """
        response = await self.client.get("/health/cache")
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


class BFFClient:
    """HTTP client for BFF API endpoints.

    Story 0.5.4b: BFF provides REST API for React frontends.

    The BFF exposes:
    - /health - Kubernetes liveness probe
    - /ready - Kubernetes readiness probe
    - /api/farmers - Farmer list endpoint
    - /api/farmers/{farmer_id} - Farmer detail endpoint

    All /api/* endpoints require JWT authentication.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        jwt_secret: str = E2E_JWT_SECRET,
    ):
        self.base_url = base_url
        self.jwt_secret = jwt_secret
        self._client: httpx.AsyncClient | None = None
        self._token_cache: dict[str, str] = {}

    async def __aenter__(self) -> "BFFClient":
        # 90s timeout: Open-Meteo API can be slow/unstable in CI environments
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=90.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    def _generate_token(
        self,
        user_id: str = "e2e-test-user",
        role: str = "factory_manager",
        permissions: list[str] | None = None,
        factory_ids: list[str] | None = None,
    ) -> str:
        """Generate a mock JWT token for E2E testing.

        Args:
            user_id: User ID to encode in token
            role: User role (platform_admin, factory_manager, etc.)
            permissions: List of permissions (defaults based on role)
            factory_ids: List of factory IDs user has access to

        Returns:
            Encoded JWT token
        """
        import time

        import jwt

        # Default permissions based on role
        if permissions is None:
            if role == "platform_admin":
                permissions = ["farmers:read", "farmers:write", "factories:read", "factories:write"]
            elif role == "factory_manager":
                permissions = ["farmers:read", "deliveries:read"]
            else:
                permissions = []

        if factory_ids is None:
            factory_ids = ["KEN-FAC-001"]

        payload = {
            "sub": user_id,
            "role": role,
            "permissions": permissions,
            "factory_ids": factory_ids,
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iat": int(time.time()),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def _get_auth_headers(
        self,
        role: str = "factory_manager",
        factory_ids: list[str] | None = None,
    ) -> dict[str, str]:
        """Get authorization headers with JWT token.

        Args:
            role: User role for the token
            factory_ids: Factory IDs for access control

        Returns:
            Headers dict with Authorization header
        """
        cache_key = f"{role}:{','.join(factory_ids or ['KEN-FAC-001'])}"
        if cache_key not in self._token_cache:
            self._token_cache[cache_key] = self._generate_token(role=role, factory_ids=factory_ids)
        return {"Authorization": f"Bearer {self._token_cache[cache_key]}"}

    # =========================================================================
    # Health Endpoints
    # =========================================================================

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
    # Farmer API Endpoints (Story 0.5.4b)
    # =========================================================================

    async def list_farmers(
        self,
        factory_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        role: str = "factory_manager",
    ) -> dict[str, Any]:
        """List farmers for a factory.

        Args:
            factory_id: Factory ID to list farmers for
            page_size: Number of farmers per page (1-100)
            page_token: Pagination token for next page
            role: User role for authorization

        Returns:
            FarmerListResponse with data and pagination
        """
        params: dict[str, Any] = {
            "factory_id": factory_id,
            "page_size": page_size,
        }
        if page_token:
            params["page_token"] = page_token

        response = await self.client.get(
            "/api/farmers",
            params=params,
            headers=self._get_auth_headers(role=role, factory_ids=[factory_id]),
        )
        response.raise_for_status()
        return response.json()

    async def get_farmer(
        self,
        farmer_id: str,
        role: str = "factory_manager",
        factory_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get farmer details.

        Args:
            farmer_id: Farmer ID to retrieve
            role: User role for authorization
            factory_ids: Factory IDs for access control

        Returns:
            FarmerDetailResponse with profile, performance, tier
        """
        response = await self.client.get(
            f"/api/farmers/{farmer_id}",
            headers=self._get_auth_headers(role=role, factory_ids=factory_ids),
        )
        response.raise_for_status()
        return response.json()

    async def list_farmers_raw(
        self,
        factory_id: str,
        role: str = "factory_manager",
        **params: Any,
    ) -> httpx.Response:
        """List farmers returning raw response for error testing.

        Args:
            factory_id: Factory ID to list farmers for
            role: User role for authorization
            **params: Additional query parameters

        Returns:
            Raw httpx.Response for status code inspection
        """
        all_params = {"factory_id": factory_id, **params}
        return await self.client.get(
            "/api/farmers",
            params=all_params,
            headers=self._get_auth_headers(role=role, factory_ids=[factory_id]),
        )

    async def get_farmer_raw(
        self,
        farmer_id: str,
        role: str = "factory_manager",
        factory_ids: list[str] | None = None,
    ) -> httpx.Response:
        """Get farmer returning raw response for error testing.

        Args:
            farmer_id: Farmer ID to retrieve
            role: User role for authorization
            factory_ids: Factory IDs for access control

        Returns:
            Raw httpx.Response for status code inspection
        """
        return await self.client.get(
            f"/api/farmers/{farmer_id}",
            headers=self._get_auth_headers(role=role, factory_ids=factory_ids),
        )
