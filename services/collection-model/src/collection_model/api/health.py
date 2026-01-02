"""Health check endpoints for Kubernetes probes."""

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collection_model.services.source_config_service import SourceConfigService

router = APIRouter(tags=["Health"])


# Global reference to check functions (set by main.py)
_mongodb_check_fn: Callable[[], Coroutine[Any, Any, bool]] | None = None
_pubsub_check_fn: Callable[[], Coroutine[Any, Any, bool]] | None = None


def set_mongodb_check(check_fn: Callable[[], Coroutine[Any, Any, bool]]) -> None:
    """Set the MongoDB connection check function.

    This allows the health module to check MongoDB connectivity
    without creating circular imports.
    """
    global _mongodb_check_fn
    _mongodb_check_fn = check_fn


def set_pubsub_check(check_fn: Callable[[], Coroutine[Any, Any, bool]]) -> None:
    """Set the pub/sub health check function."""
    global _pubsub_check_fn
    _pubsub_check_fn = check_fn


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Returns 200 if the service is running. Used by Kubernetes liveness probe.",
)
async def health() -> dict[str, str]:
    """Liveness probe - service is running."""
    return {"status": "healthy"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Returns 200 if the service can accept traffic. Checks MongoDB and Dapr connectivity.",
)
async def ready() -> JSONResponse:
    """Readiness probe - service can accept traffic.

    Checks:
    - MongoDB connection is established
    - Dapr pub/sub is available (optional - degrades gracefully)
    """
    checks: dict[str, str] = {}
    all_healthy = True

    # Check MongoDB connection (required)
    if _mongodb_check_fn is not None:
        try:
            mongodb_ok = await _mongodb_check_fn()
            checks["mongodb"] = "connected" if mongodb_ok else "disconnected"
            if not mongodb_ok:
                all_healthy = False
        except Exception:
            checks["mongodb"] = "error"
            all_healthy = False
    else:
        checks["mongodb"] = "not_configured"

    # Check Dapr pub/sub (optional - service works without it in dev)
    if _pubsub_check_fn is not None:
        try:
            pubsub_ok = await _pubsub_check_fn()
            checks["pubsub"] = "available" if pubsub_ok else "unavailable"
            # Don't fail readiness if pub/sub is unavailable
        except Exception:
            checks["pubsub"] = "unavailable"
    else:
        checks["pubsub"] = "not_configured"

    if all_healthy:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "checks": checks},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "checks": checks},
    )


@router.get(
    "/health/cache",
    status_code=status.HTTP_200_OK,
    summary="Cache health status",
    description="Returns source config cache status including size, age, and change stream status (Story 0.6.9).",
)
async def cache_health(request: Request) -> dict[str, Any]:
    """Cache health endpoint for observability (Story 0.6.9, ADR-007).

    Returns:
        Dict with cache_size, cache_age_seconds, change_stream_active.
    """
    source_config_service: SourceConfigService | None = getattr(request.app.state, "source_config_service", None)
    if source_config_service is not None:
        return source_config_service.get_cache_status()
    return {
        "cache_size": 0,
        "cache_age_seconds": -1,
        "change_stream_active": False,
        "error": "source_config_service not initialized",
    }


@router.post(
    "/admin/invalidate-cache",
    status_code=status.HTTP_200_OK,
    summary="Invalidate source config cache",
    description="Forces the SourceConfigService to refresh its cache on next request. Used by E2E tests.",
)
async def invalidate_cache(request: Request) -> dict[str, str]:
    """Invalidate the source config cache.

    This endpoint is used by E2E tests to ensure the service
    picks up newly seeded source configurations after database reset.
    """
    source_config_service: SourceConfigService | None = getattr(request.app.state, "source_config_service", None)
    if source_config_service is not None:
        source_config_service.invalidate_cache()
        return {"status": "cache_invalidated"}
    return {"status": "no_cache_configured"}
