"""Platform Cost Service - FastAPI + gRPC + DAPR Streaming entrypoint.

Unified cost aggregation service for the Farmer Power Platform.
Receives cost events from other services via DAPR pub/sub and provides
cost query APIs via gRPC.

Architecture (ADR-011, ADR-016):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50054: gRPC server (via DAPR sidecar)
- Pub/sub: DAPR streaming subscriptions (outbound, no extra port)

Story 13.2: Service scaffold with FastAPI + DAPR + gRPC.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fp_common import configure_logging, create_admin_router

from platform_cost.api import health_router
from platform_cost.api.health import set_mongodb_check
from platform_cost.config import settings
from platform_cost.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_mongodb_client,
)
from platform_cost.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)

# Configure structured logging via fp_common (ADR-009)
configure_logging("platform-cost")

logger = structlog.get_logger("platform_cost.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    Story 13.2: Basic scaffold lifespan - MongoDB connection only.
    Story 13.3: Will add BudgetMonitor initialization.
    Story 13.4: Will add gRPC server initialization.
    Story 13.5: Will add DAPR streaming subscriptions.
    """
    # Startup
    logger.info(
        "Starting Platform Cost service",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )

    # Initialize OpenTelemetry tracing (must be early for other instrumentation)
    setup_tracing()

    # Initialize MongoDB connection
    try:
        await get_mongodb_client()
        set_mongodb_check(check_mongodb_connection)
        logger.info("MongoDB connection initialized")

    except Exception as e:
        logger.warning("MongoDB initialization failed at startup", error=str(e))
        # Service can still start - readiness probe will report not ready

    logger.info("Service startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Platform Cost service")

    await close_mongodb_connection()
    shutdown_tracing()

    logger.info("Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Platform Cost Service",
    description="Unified cost aggregation service for the Farmer Power Platform. "
    "Receives cost events from services via DAPR pub/sub and provides "
    "cost query APIs via gRPC (ADR-016).",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(create_admin_router())  # Runtime log level control (ADR-009)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint - service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "platform_cost.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
