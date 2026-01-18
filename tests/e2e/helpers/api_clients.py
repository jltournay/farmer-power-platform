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
E2E_JWT_SECRET = "default-test-secret-for-development-32-chars"


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
        # 180s timeout: Open-Meteo API can be very slow/rate-limited in CI environments
        # The pull job endpoint waits synchronously for external API calls
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=180.0)
        self._dapr_client = httpx.AsyncClient(base_url=self.dapr_base_url, timeout=180.0)
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
            "aud": "farmer-power-bff",  # Required by auth middleware
            "iss": "mock-auth",  # Required by auth middleware
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

    # =========================================================================
    # Admin API Endpoints (Story 9.1c)
    # =========================================================================

    async def admin_list_regions(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """List regions (admin endpoint).

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            is_active: Filter by active status

        Returns:
            Paginated list of regions
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if is_active is not None:
            params["is_active"] = is_active

        response = await self.client.get(
            "/api/admin/regions",
            params=params,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_get_region(self, region_id: str) -> dict[str, Any]:
        """Get region details (admin endpoint).

        Args:
            region_id: Region ID to retrieve

        Returns:
            Region detail with factories
        """
        response = await self.client.get(
            f"/api/admin/regions/{region_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_create_region(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new region (admin endpoint).

        Args:
            data: Region creation data

        Returns:
            Created region
        """
        response = await self.client.post(
            "/api/admin/regions",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_update_region(self, region_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a region (admin endpoint).

        Args:
            region_id: Region ID to update
            data: Region update data

        Returns:
            Updated region
        """
        response = await self.client.put(
            f"/api/admin/regions/{region_id}",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_list_factories(
        self,
        page: int = 1,
        page_size: int = 50,
        region_id: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """List factories (admin endpoint).

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            region_id: Filter by region
            is_active: Filter by active status

        Returns:
            Paginated list of factories
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if region_id is not None:
            params["region_id"] = region_id
        if is_active is not None:
            params["is_active"] = is_active

        response = await self.client.get(
            "/api/admin/factories",
            params=params,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_get_factory(self, factory_id: str) -> dict[str, Any]:
        """Get factory details (admin endpoint).

        Args:
            factory_id: Factory ID to retrieve

        Returns:
            Factory detail with collection points
        """
        response = await self.client.get(
            f"/api/admin/factories/{factory_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_create_factory(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new factory (admin endpoint).

        Args:
            data: Factory creation data

        Returns:
            Created factory
        """
        response = await self.client.post(
            "/api/admin/factories",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_update_factory(self, factory_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a factory (admin endpoint).

        Args:
            factory_id: Factory ID to update
            data: Factory update data

        Returns:
            Updated factory
        """
        response = await self.client.put(
            f"/api/admin/factories/{factory_id}",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_list_collection_points(
        self,
        factory_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool | None = None,
    ) -> dict[str, Any]:
        """List collection points for a factory (admin endpoint).

        Args:
            factory_id: Factory ID to list collection points for
            page_size: Number of items per page
            page_token: Pagination token
            active_only: Filter to active collection points only

        Returns:
            Paginated list of collection point summaries
        """
        params: dict[str, Any] = {"factory_id": factory_id, "page_size": page_size}
        if page_token is not None:
            params["page_token"] = page_token
        if active_only is not None:
            params["active_only"] = active_only

        response = await self.client.get(
            "/api/admin/collection-points",
            params=params,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_get_collection_point(self, collection_point_id: str) -> dict[str, Any]:
        """Get collection point details (admin endpoint).

        Args:
            collection_point_id: Collection point ID to retrieve

        Returns:
            Collection point detail with farmers
        """
        response = await self.client.get(
            f"/api/admin/collection-points/{collection_point_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_update_collection_point(self, collection_point_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a collection point (admin endpoint).

        Args:
            collection_point_id: Collection point ID to update
            data: Collection point update data

        Returns:
            Updated collection point
        """
        response = await self.client.put(
            f"/api/admin/collection-points/{collection_point_id}",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_assign_farmer_to_cp(self, collection_point_id: str, farmer_id: str) -> dict[str, Any]:
        """Assign a farmer to a collection point (Story 9.5a).

        Args:
            collection_point_id: Collection point ID
            farmer_id: Farmer ID to assign

        Returns:
            Updated collection point with farmer_ids
        """
        response = await self.client.post(
            f"/api/admin/collection-points/{collection_point_id}/farmers/{farmer_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_unassign_farmer_from_cp(self, collection_point_id: str, farmer_id: str) -> dict[str, Any]:
        """Unassign a farmer from a collection point (Story 9.5a).

        Args:
            collection_point_id: Collection point ID
            farmer_id: Farmer ID to unassign

        Returns:
            Updated collection point with farmer_ids
        """
        response = await self.client.delete(
            f"/api/admin/collection-points/{collection_point_id}/farmers/{farmer_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_list_farmers(
        self,
        page: int = 1,
        page_size: int = 50,
        factory_id: str | None = None,
        collection_point_id: str | None = None,
        is_active: bool | None = None,
        farm_scale: str | None = None,
        tier: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List farmers (admin endpoint).

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            factory_id: Filter by factory
            collection_point_id: Filter by collection point
            is_active: Filter by active status
            farm_scale: Filter by farm scale (smallholder, medium, estate)
            tier: Filter by quality tier (tier_1, tier_2, tier_3, below_tier_3)
            search: Search by name, phone, or farmer ID

        Returns:
            Paginated list of farmers
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if factory_id is not None:
            params["factory_id"] = factory_id
        if collection_point_id is not None:
            params["collection_point_id"] = collection_point_id
        if is_active is not None:
            params["is_active"] = is_active
        if farm_scale is not None:
            params["farm_scale"] = farm_scale
        if tier is not None:
            params["tier"] = tier
        if search is not None:
            params["search"] = search

        response = await self.client.get(
            "/api/admin/farmers",
            params=params,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_get_farmer(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer details (admin endpoint).

        Args:
            farmer_id: Farmer ID to retrieve

        Returns:
            Farmer detail
        """
        response = await self.client.get(
            f"/api/admin/farmers/{farmer_id}",
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_create_farmer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new farmer (admin endpoint).

        Args:
            data: Farmer creation data

        Returns:
            Created farmer
        """
        response = await self.client.post(
            "/api/admin/farmers",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_update_farmer(self, farmer_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a farmer (admin endpoint).

        Args:
            farmer_id: Farmer ID to update
            data: Farmer update data

        Returns:
            Updated farmer
        """
        response = await self.client.put(
            f"/api/admin/farmers/{farmer_id}",
            json=data,
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_import_farmers(self, csv_content: bytes, factory_id: str) -> dict[str, Any]:
        """Import farmers from CSV (admin endpoint).

        Args:
            csv_content: CSV file content
            factory_id: Factory ID to import farmers to

        Returns:
            Import result with success/failure counts
        """
        files = {"file": ("farmers.csv", csv_content, "text/csv")}
        response = await self.client.post(
            "/api/admin/farmers/import",
            files=files,
            params={"factory_id": factory_id},
            headers=self._get_auth_headers(role="platform_admin"),
        )
        response.raise_for_status()
        return response.json()

    async def admin_request_raw(
        self,
        method: str,
        path: str,
        role: str = "platform_admin",
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a raw admin request for error testing.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            path: Request path
            role: User role for authorization
            **kwargs: Additional request arguments

        Returns:
            Raw httpx.Response for status code inspection
        """
        return await self.client.request(
            method,
            path,
            headers=self._get_auth_headers(role=role),
            **kwargs,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Platform Cost API Client (Story 13.8)
# Used for publishing cost events via DAPR and health checks
# ═══════════════════════════════════════════════════════════════════════════════

# DAPR HTTP port for platform-cost sidecar (not exposed in docker-compose, use AI model's)
# Since platform-cost only subscribes (doesn't publish), we'll publish via ai-model's DAPR sidecar
AI_MODEL_DAPR_HTTP_PORT = 3500  # ai-model's DAPR sidecar at localhost:3500 on port 8091


class PlatformCostApiClient:
    """HTTP client for Platform Cost service and DAPR event publishing.

    This client provides:
    - Health check endpoints
    - DAPR pub/sub to platform.cost.recorded topic (via ai-model's DAPR sidecar)

    Story 13.8: E2E Integration Tests for Platform Cost Service
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8084",
        dapr_http_port: int = AI_MODEL_DAPR_HTTP_PORT,
    ):
        """Initialize Platform Cost API client.

        Args:
            base_url: Platform Cost FastAPI URL (for health checks)
            dapr_http_port: DAPR sidecar HTTP port for publishing events
        """
        self.base_url = base_url
        # ai-model container exposes DAPR at port 8091 (mapped from 3500)
        # Actually we need to use the internal Docker network for ai-model's DAPR
        # Since we're running tests from host, we can publish via ai-model's exposed port
        self.dapr_base_url = "http://localhost:8091"  # ai-model HTTP
        self._client: httpx.AsyncClient | None = None
        self._dapr_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PlatformCostApiClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        # Connect to ai-model's DAPR sidecar for publishing
        # The sidecar is at localhost:3500 inside container, mapped to port exposed with container
        self._dapr_client = httpx.AsyncClient(
            base_url="http://localhost:3502",  # Collection model DAPR (exposed)
            timeout=30.0,
        )
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
        """Check Platform Cost service health."""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def ready(self) -> dict[str, Any]:
        """Check Platform Cost service readiness."""
        response = await self.client.get("/ready")
        response.raise_for_status()
        return response.json()

    async def publish_cost_event(
        self,
        request_id: str,
        cost_type: str,
        amount_usd: str,
        quantity: int = 1,
        unit: str | None = None,
        agent_type: str = "extractor",
        metadata: dict[str, Any] | None = None,
        success: bool = True,
    ) -> bool:
        """Publish a CostRecordedEvent to platform.cost.recorded topic via DAPR.

        Args:
            request_id: Unique request ID for idempotency
            cost_type: Type of cost (llm, document, embedding, sms)
            amount_usd: Cost amount as string (Decimal)
            quantity: Number of units consumed
            unit: Unit type (auto-mapped from cost_type if not provided)
            agent_type: Agent type for LLM costs (stored in metadata)
            metadata: Additional metadata (model, tokens_in, tokens_out, etc.)
            success: Whether the operation succeeded

        Returns:
            True if event was published successfully
        """
        from datetime import UTC, datetime

        # Auto-map cost_type to correct unit per CostRecordedEvent schema
        unit_map = {
            "llm": "tokens",
            "document": "pages",
            "embedding": "queries",
            "sms": "messages",
        }
        resolved_unit = unit if unit else unit_map.get(cost_type, "tokens")

        # Build metadata with agent_type for LLM costs
        full_metadata = metadata.copy() if metadata else {}
        if cost_type == "llm" and agent_type:
            full_metadata["agent_type"] = agent_type

        # Build CostRecordedEvent matching fp_common/events/cost_recorded.py
        event = {
            "cost_type": cost_type,
            "amount_usd": amount_usd,
            "quantity": quantity,
            "unit": resolved_unit,
            "timestamp": datetime.now(UTC).isoformat(),
            "source_service": "ai-model",  # Simulating ai-model publishing
            "success": success,
            "metadata": full_metadata,
            "request_id": request_id,
        }

        # Publish to DAPR pub/sub topic 'platform.cost.recorded'
        # DAPR HTTP API: POST /v1.0/publish/{pubsub-name}/{topic}
        response = await self.dapr_client.post(
            "/v1.0/publish/pubsub/platform.cost.recorded",
            json=event,
            headers={"Content-Type": "application/json"},
        )

        # DAPR returns 204 No Content on successful publish
        return response.status_code in (200, 204)
