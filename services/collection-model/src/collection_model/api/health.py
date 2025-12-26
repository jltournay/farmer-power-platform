"""Health check endpoints for Kubernetes probes."""

from typing import Any, Callable, Coroutine

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

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
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks},
        )
