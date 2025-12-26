"""Collection Model Service - FastAPI entrypoint.

Quality data ingestion gateway for the Farmer Power Platform.
Collects, validates, transforms, links, stores, and serves documents
related to quality events from various sources.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from collection_model.api import events, health
from collection_model.config import settings
from collection_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_mongodb_client,
)
from collection_model.infrastructure.pubsub import check_pubsub_health
from collection_model.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(
        "Starting Collection Model service",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )

    # Initialize OpenTelemetry tracing (must be early for other instrumentation)
    setup_tracing()

    # Initialize MongoDB connection
    try:
        await get_mongodb_client()
        health.set_mongodb_check(check_mongodb_connection)
        logger.info("MongoDB connection initialized")
    except Exception as e:
        logger.warning("MongoDB connection failed at startup", error=str(e))
        # Service can still start - readiness probe will report not ready

    # Set up pub/sub health check
    health.set_pubsub_check(check_pubsub_health)

    logger.info("Service startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Collection Model service")
    await close_mongodb_connection()
    shutdown_tracing()
    logger.info("Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Collection Model Service",
    description="Quality data ingestion gateway for the Farmer Power Platform. "
    "Collects, validates, transforms, links, stores, and serves documents "
    "related to quality events from various sources.",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware (configurable via COLLECTION_CORS_* env vars)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(health.router)
app.include_router(events.router)

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
        "collection_model.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
