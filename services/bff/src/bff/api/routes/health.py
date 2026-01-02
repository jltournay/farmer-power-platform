"""BFF health and readiness endpoints.

Provides health check endpoints for Kubernetes probes per ADR-002.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Health check endpoint.

    Returns 200 if the service is running.
    Used by Kubernetes liveness probe.

    Returns:
        Health status response.
    """
    return {
        "status": "healthy",
        "service": "bff",
    }


@router.get("/ready")
async def ready() -> dict:
    """Readiness check endpoint.

    Returns 200 if the service is ready to accept traffic.
    Used by Kubernetes readiness probe.

    In a production implementation, this would check:
    - DAPR sidecar connectivity
    - Backend service availability (plantation-model, collection-model)

    Returns:
        Readiness status response with dependency checks.
    """
    # For now, return ready status with placeholder dependencies
    # Actual dependency checks will be implemented in Story 0.5.3/0.5.4
    return {
        "status": "ready",
        "dependencies": {
            "dapr": "connected",
        },
    }
