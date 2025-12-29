"""Plantation Model Service - FastAPI entrypoint.

Master data registry for the Farmer Power Platform.
Stores core entities (regions, farmers, factories), configuration,
and pre-computed performance summaries.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from plantation_model.api import health
from plantation_model.api.event_handlers import (
    quality_result_router,
    weather_updated_router,
)
from plantation_model.api.grpc_server import start_grpc_server, stop_grpc_server
from plantation_model.config import settings
from plantation_model.domain.services import QualityEventProcessor
from plantation_model.infrastructure.collection_client import CollectionClient
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from plantation_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)
from plantation_model.infrastructure.tracing import (
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
        "Starting Plantation Model service",
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

        # Initialize repositories and services (Story 1.7)
        db = await get_database()
        grading_model_repo = GradingModelRepository(db)
        farmer_performance_repo = FarmerPerformanceRepository(db)

        # Initialize Collection client for fetching quality documents
        collection_client = CollectionClient()
        app.state.collection_client = collection_client

        # Initialize DAPR pub/sub client for event emission
        event_publisher = DaprPubSubClient()

        # Initialize QualityEventProcessor (Story 1.7)
        app.state.quality_event_processor = QualityEventProcessor(
            collection_client=collection_client,
            grading_model_repo=grading_model_repo,
            farmer_performance_repo=farmer_performance_repo,
            event_publisher=event_publisher,
        )
        logger.info("QualityEventProcessor initialized")

    except Exception as e:
        logger.warning("MongoDB connection failed at startup", error=str(e))
        # Service can still start - readiness probe will report not ready

    # Start gRPC server
    try:
        await start_grpc_server()
        logger.info("gRPC server started", port=settings.grpc_port)
    except Exception as e:
        logger.warning("gRPC server failed to start", error=str(e))

    logger.info("Service startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Plantation Model service")
    await stop_grpc_server()

    # Close Collection client (Story 1.7)
    if hasattr(app.state, "collection_client"):
        await app.state.collection_client.close()

    await close_mongodb_connection()
    shutdown_tracing()
    logger.info("Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Plantation Model Service",
    description="Master data registry for the Farmer Power Platform. "
    "Stores core entities (regions, farmers, factories), configuration, "
    "and pre-computed performance summaries.",
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
app.include_router(health.router)
app.include_router(quality_result_router)
app.include_router(weather_updated_router)

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
        "plantation_model.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
