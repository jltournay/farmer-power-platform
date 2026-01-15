"""BFF FastAPI application entrypoint.

Backend for Frontend service for Farmer Power Platform.
Per ADR-002, this is the only external-facing API.
"""

from contextlib import asynccontextmanager

import structlog
from bff.api.routes import farmers, health
from bff.api.routes.admin import router as admin_router
from bff.config import get_settings
from bff.infrastructure.tracing import instrument_fastapi, setup_tracing
from fastapi import FastAPI
from fp_common import configure_logging, create_admin_router

# Configure structured logging via fp_common (ADR-009, Story 0.6.15)
configure_logging("bff")

logger = structlog.get_logger("bff.main")


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
    app.include_router(admin_router)  # Story 9.1c: Admin portal BFF endpoints
    app.include_router(create_admin_router())  # Story 0.6.15: Runtime log level control

    return app


# Create application instance for uvicorn
app = create_app()
