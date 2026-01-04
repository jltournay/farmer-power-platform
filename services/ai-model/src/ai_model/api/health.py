"""Health check endpoints for Kubernetes probes."""

from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


# Global reference to MongoDB check function (set by main.py)
_mongodb_check_fn: Any = None


def set_mongodb_check(check_fn: Any) -> None:
    """Set the MongoDB connection check function.

    This allows the health module to check MongoDB connectivity
    without creating circular imports.
    """
    global _mongodb_check_fn
    _mongodb_check_fn = check_fn


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
    description="Returns 200 if the service can accept traffic. Checks MongoDB connectivity.",
)
async def ready() -> JSONResponse:
    """Readiness probe - service can accept traffic.

    Checks:
    - MongoDB connection is established
    """
    checks: dict[str, str] = {}
    all_healthy = True

    # Check MongoDB connection
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
        # MongoDB not configured yet - still starting up
        checks["mongodb"] = "not_configured"

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
