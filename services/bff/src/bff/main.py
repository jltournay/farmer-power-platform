"""BFF FastAPI application entrypoint.

Backend for Frontend service for Farmer Power Platform.
Per ADR-002, this is the only external-facing API.
"""

from contextlib import asynccontextmanager

import structlog
from bff.api.routes import farmers, health
from bff.config import get_settings
from bff.infrastructure.tracing import instrument_fastapi, setup_tracing
from fastapi import FastAPI

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Handles startup and shutdown events for the BFF service.

    Startup:
    - Configure OpenTelemetry tracing
    - Initialize logging

    Shutdown:
    - Clean up resources (if any)

    Args:
        app: The FastAPI application instance.
    """
    settings = get_settings()
    logger.info(
        "BFF service starting",
        app_env=settings.app_env,
        auth_provider=settings.auth_provider,
    )

    # Configure tracing
    setup_tracing()
    instrument_fastapi(app)

    yield

    # Shutdown
    logger.info("BFF service shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Farmer Power BFF",
        description="Backend for Frontend API gateway for Farmer Power Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(farmers.router)

    return app


# Create application instance for uvicorn
app = create_app()
