"""Plantation Model Service - FastAPI + gRPC + DAPR Streaming entrypoint.

Master data registry for the Farmer Power Platform.
Stores core entities (regions, farmers, factories), configuration,
and pre-computed performance summaries.

Architecture (ADR-011):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50051: gRPC server (via DAPR sidecar)
- Pub/sub: DAPR streaming subscriptions (outbound, no extra port)
"""

import asyncio
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fp_common import configure_logging, create_admin_router
from fp_common.events import (
    DLQRepository,
    set_dlq_event_loop,
    set_dlq_repository,
    start_dlq_subscription,
)
from plantation_model.api import health
from plantation_model.api.grpc_server import start_grpc_server, stop_grpc_server
from plantation_model.config import settings
from plantation_model.domain.services import QualityEventProcessor
from plantation_model.events.subscriber import (
    run_streaming_subscriptions,
    set_main_event_loop,
    set_quality_event_processor,
    set_regional_weather_repo,
)
from plantation_model.infrastructure.collection_grpc_client import CollectionGrpcClient
from plantation_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)
from plantation_model.infrastructure.repositories.region_repository import (
    RegionRepository,
)
from plantation_model.infrastructure.repositories.regional_weather_repository import (
    RegionalWeatherRepository,
)
from plantation_model.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)

# Configure structured logging via fp_common (ADR-009)
configure_logging("plantation-model")

logger = structlog.get_logger("plantation_model.main")


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

        # Initialize repositories and services (Story 1.7 + Story 0.6.10)
        db = await get_database()
        grading_model_repo = GradingModelRepository(db)
        farmer_performance_repo = FarmerPerformanceRepository(db)
        regional_weather_repo = RegionalWeatherRepository(db)

        # Story 0.6.10: Additional repositories for linkage field validation
        farmer_repo = FarmerRepository(db)
        factory_repo = FactoryRepository(db)
        region_repo = RegionRepository(db)

        # Initialize Collection gRPC client for fetching quality documents
        # Story 0.6.13: Uses gRPC via DAPR instead of direct MongoDB
        collection_client = CollectionGrpcClient()
        app.state.collection_client = collection_client

        # Initialize QualityEventProcessor (Story 1.7 + Story 0.6.10)
        # Story 0.6.14: DAPR publishing uses module-level publish_event() per ADR-010
        quality_event_processor = QualityEventProcessor(
            collection_client=collection_client,
            grading_model_repo=grading_model_repo,
            farmer_performance_repo=farmer_performance_repo,
            farmer_repo=farmer_repo,
            factory_repo=factory_repo,
            region_repo=region_repo,
        )
        app.state.quality_event_processor = quality_event_processor
        logger.info("QualityEventProcessor initialized")

        # Set processor references for streaming subscription handlers (Story 0.6.5)
        set_quality_event_processor(quality_event_processor)
        set_regional_weather_repo(regional_weather_repo)
        logger.info("Subscription handler dependencies configured")

        # CRITICAL: Pass the main event loop to streaming subscription handlers
        # The handlers run in a separate thread, but Motor (MongoDB) and other
        # async clients are bound to this loop. Handlers use run_coroutine_threadsafe()
        # to schedule async operations on this loop.
        main_loop = asyncio.get_running_loop()
        set_main_event_loop(main_loop)
        logger.info("Main event loop configured for streaming subscriptions")

        # Initialize DLQ repository and configure DLQ handler (Story 0.6.8, ADR-006)
        dlq_repository = DLQRepository(db["event_dead_letter"])
        set_dlq_repository(dlq_repository)
        set_dlq_event_loop(main_loop)
        logger.info("DLQ handler dependencies configured")

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

        # Start DLQ subscription in separate thread (Story 0.6.8)
        # DLQ handler stores failed events in MongoDB for inspection and replay
        dlq_thread = threading.Thread(
            target=start_dlq_subscription,
            daemon=True,
            name="dapr-dlq-subscription",
        )
        dlq_thread.start()
        logger.info("DLQ subscription thread started")

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
app.include_router(create_admin_router())  # Story 0.6.15: Runtime log level control

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
