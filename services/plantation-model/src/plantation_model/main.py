"""Plantation Model Service - FastAPI + gRPC + DAPR Streaming entrypoint.

Master data registry for the Farmer Power Platform.
Stores core entities (regions, farmers, factories), configuration,
and pre-computed performance summaries.

Architecture (ADR-011):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50051: gRPC server (via DAPR sidecar)
- Pub/sub: DAPR streaming subscriptions (outbound, no extra port)
"""

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from plantation_model.api import health
from plantation_model.api.grpc_server import start_grpc_server, stop_grpc_server
from plantation_model.config import settings
from plantation_model.domain.services import QualityEventProcessor
from plantation_model.events.subscriber import (
    run_streaming_subscriptions,
    set_quality_event_processor,
    set_regional_weather_repo,
)
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
from plantation_model.infrastructure.repositories.regional_weather_repository import (
    RegionalWeatherRepository,
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
        regional_weather_repo = RegionalWeatherRepository(db)

        # Initialize Collection client for fetching quality documents
        collection_client = CollectionClient()
        app.state.collection_client = collection_client

        # Initialize DAPR pub/sub client for event emission
        event_publisher = DaprPubSubClient()

        # Initialize QualityEventProcessor (Story 1.7)
        quality_event_processor = QualityEventProcessor(
            collection_client=collection_client,
            grading_model_repo=grading_model_repo,
            farmer_performance_repo=farmer_performance_repo,
            event_publisher=event_publisher,
        )
        app.state.quality_event_processor = quality_event_processor
        logger.info("QualityEventProcessor initialized")

        # Set processor references for streaming subscription handlers (Story 0.6.5)
        set_quality_event_processor(quality_event_processor)
        set_regional_weather_repo(regional_weather_repo)
        logger.info("Subscription handler dependencies configured")

        # Start DAPR streaming subscriptions in background thread (Story 0.6.5)
        # ADR-010/011 pattern: run_streaming_subscriptions keeps DaprClient alive
        # Subscriptions are outbound - no extra HTTP port needed
        subscription_thread = threading.Thread(
            target=run_streaming_subscriptions,
            daemon=True,
            name="dapr-subscriptions",
        )
        subscription_thread.start()
        logger.info("DAPR streaming subscriptions thread started")

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

    # Note: Streaming subscriptions run in a daemon thread with its own cleanup
    # The thread will be terminated when the main process exits
    logger.info("Subscriptions will be closed by daemon thread")

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
# Note: HTTP event handlers removed in Story 0.6.5 - using DAPR streaming subscriptions
app.include_router(health.router)

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
