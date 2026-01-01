"""Admin endpoints for runtime service configuration.

Provides endpoints for runtime log level control without pod restart.
See ADR-009 for logging standards and runtime configuration patterns.

Usage:
    from fastapi import FastAPI
    from fp_common.admin import create_admin_router

    app = FastAPI()
    app.include_router(create_admin_router())

    # Then at runtime:
    # POST /admin/logging/plantation_model.domain?level=DEBUG
    # DELETE /admin/logging/plantation_model.domain
    # GET /admin/logging
"""

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel


class LogLevelUpdateResponse(BaseModel):
    """Response model for log level update operations."""

    logger: str
    level: str
    status: str


class LogLevelResetResponse(BaseModel):
    """Response model for log level reset operations."""

    logger: str
    status: str


class LogLevelListResponse(BaseModel):
    """Response model for listing configured log levels."""

    loggers: dict[str, str]


def create_admin_router(prefix: str = "/admin") -> APIRouter:
    """Create admin router with logging endpoints.

    Args:
        prefix: URL prefix for admin endpoints (default: "/admin")

    Returns:
        FastAPI router with logging management endpoints
    """
    router = APIRouter(prefix=prefix, tags=["admin"])

    @router.post("/logging/{logger_name}", response_model=LogLevelUpdateResponse)
    async def set_log_level(
        logger_name: str,
        level: str = Query(..., description="Log level (DEBUG, INFO, WARNING, ERROR)"),
    ) -> dict[str, Any]:
        """Set log level for a specific logger at runtime.

        This affects the logger and all its children. The change persists
        until the pod restarts or the level is reset.

        Args:
            logger_name: Fully qualified logger name (e.g., "plantation_model.domain")
            level: Log level to set (DEBUG, INFO, WARNING, ERROR)

        Returns:
            Confirmation of the level change
        """
        normalized_level = level.upper()

        # Validate level is valid
        if not hasattr(logging, normalized_level):
            return {
                "logger": logger_name,
                "level": level,
                "status": f"error: invalid level '{level}'",
            }

        logging.getLogger(logger_name).setLevel(normalized_level)
        return {"logger": logger_name, "level": normalized_level, "status": "updated"}

    @router.delete("/logging/{logger_name}", response_model=LogLevelResetResponse)
    async def reset_log_level(logger_name: str) -> dict[str, Any]:
        """Reset logger to default level (inherit from parent).

        Args:
            logger_name: Fully qualified logger name to reset

        Returns:
            Confirmation of the reset
        """
        logging.getLogger(logger_name).setLevel(logging.NOTSET)
        return {"logger": logger_name, "status": "reset"}

    @router.get("/logging", response_model=LogLevelListResponse)
    async def list_log_levels() -> dict[str, Any]:
        """List all loggers with non-default levels.

        Returns:
            Dictionary mapping logger names to their configured levels
        """
        loggers: dict[str, str] = {}
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and logger.level != logging.NOTSET:
                loggers[name] = logging.getLevelName(logger.level)
        return {"loggers": loggers}

    return router
