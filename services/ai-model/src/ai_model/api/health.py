"""Health check endpoints for Kubernetes probes.

Story 0.75.4: Added /health/cache endpoint for cache observability (ADR-013).
"""

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from ai_model.services import AgentConfigCache, PromptCache

router = APIRouter(tags=["Health"])


# Global reference to MongoDB check function (set by main.py)
_mongodb_check_fn: Any = None

# Story 0.75.4: Global references to cache services
_agent_config_cache: "AgentConfigCache | None" = None
_prompt_cache: "PromptCache | None" = None


def set_mongodb_check(check_fn: Any) -> None:
    """Set the MongoDB connection check function.

    This allows the health module to check MongoDB connectivity
    without creating circular imports.
    """
    global _mongodb_check_fn
    _mongodb_check_fn = check_fn


def set_cache_services(
    agent_config_cache: "AgentConfigCache",
    prompt_cache: "PromptCache",
) -> None:
    """Set the cache service references for health endpoint.

    Story 0.75.4: Enable /health/cache endpoint (ADR-013).

    Args:
        agent_config_cache: The AgentConfigCache instance.
        prompt_cache: The PromptCache instance.
    """
    global _agent_config_cache, _prompt_cache
    _agent_config_cache = agent_config_cache
    _prompt_cache = prompt_cache


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


@router.get(
    "/health/cache",
    status_code=status.HTTP_200_OK,
    summary="Cache health status",
    description="Returns cache health status for agent configs and prompts. Story 0.75.4: ADR-013 cache observability.",
)
async def cache_health() -> JSONResponse:
    """Cache health status endpoint.

    Story 0.75.4: Returns health status of AgentConfigCache and PromptCache.

    Returns:
        JSON with cache_size, cache_age_seconds, change_stream_active, cache_valid
        for both agent_config and prompt caches.
    """
    result: dict[str, dict] = {}

    if _agent_config_cache is not None:
        result["agent_config"] = _agent_config_cache.get_health_status()
    else:
        result["agent_config"] = {"status": "not_initialized"}

    if _prompt_cache is not None:
        result["prompt"] = _prompt_cache.get_health_status()
    else:
        result["prompt"] = {"status": "not_initialized"}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
    )
