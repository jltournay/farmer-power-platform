"""Health check endpoints for Kubernetes probes.

Story 13.2: Platform Cost Service scaffold.
"""

from typing import Any

import httpx
import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from platform_cost.config import settings

logger = structlog.get_logger(__name__)

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


async def check_dapr_sidecar() -> bool:
    """Check if DAPR sidecar is healthy.

    Makes HTTP request to DAPR sidecar health endpoint.

    Returns:
        bool: True if DAPR sidecar is healthy, False otherwise.
    """
    dapr_health_url = f"http://{settings.dapr_host}:{settings.dapr_http_port}/v1.0/healthz"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(dapr_health_url)
            return response.status_code == 204 or response.status_code == 200
    except httpx.RequestError as e:
        logger.debug("DAPR sidecar health check failed", error=str(e))
        return False
    except Exception as e:
        logger.warning("Unexpected error checking DAPR sidecar", error=str(e))
        return False


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
    description="Returns 200 if the service can accept traffic. Checks MongoDB and DAPR connectivity.",
)
async def ready() -> JSONResponse:
    """Readiness probe - service can accept traffic.

    Checks:
    - MongoDB connection is established
    - DAPR sidecar is healthy
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
        # MongoDB not configured yet - service not ready to accept traffic
        checks["mongodb"] = "not_configured"
        all_healthy = False

    # Check DAPR sidecar
    dapr_ok = await check_dapr_sidecar()
    checks["dapr"] = "healthy" if dapr_ok else "unavailable"
    # DAPR check is informational - service can start without DAPR in development
    # In production, DAPR should be healthy for full functionality

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
