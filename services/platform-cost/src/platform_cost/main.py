"""Platform Cost Service - FastAPI + gRPC + DAPR Streaming entrypoint.

Unified cost aggregation service for the Farmer Power Platform.
Receives cost events from other services via DAPR pub/sub and provides
cost query APIs via gRPC.

Architecture (ADR-011, ADR-016):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50054: gRPC server (via DAPR sidecar)
- Pub/sub: DAPR streaming subscriptions (outbound, no extra port)

Story 13.2: Service scaffold with FastAPI + DAPR + gRPC.
Story 13.3: Add BudgetMonitor initialization with warm-up.
Story 13.4: Add gRPC UnifiedCostService server.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fp_common import configure_logging, create_admin_router

from platform_cost.api import GrpcServer, health_router
from platform_cost.api.health import set_mongodb_check
from platform_cost.config import settings
from platform_cost.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from platform_cost.infrastructure.repositories import (
    ThresholdRepository,
    UnifiedCostRepository,
)
from platform_cost.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)
from platform_cost.services import BudgetMonitor

# Configure structured logging via fp_common (ADR-009)
configure_logging("platform-cost")

logger = structlog.get_logger("platform_cost.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    Story 13.2: Basic scaffold lifespan - MongoDB connection only.
    Story 13.3: Add BudgetMonitor initialization with warm-up from MongoDB.
    Story 13.4: Add gRPC UnifiedCostService server.
    Story 13.5: Will add DAPR streaming subscriptions.
    """
    grpc_server: GrpcServer | None = None

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

        # Story 13.3: Initialize repositories and budget monitor
        db = await get_database()

        # Initialize cost repository with configured retention
        cost_repository = UnifiedCostRepository(
            db=db,
            retention_days=settings.cost_event_retention_days,
        )
        await cost_repository.ensure_indexes()
        logger.info(
            "Cost repository initialized",
            retention_days=settings.cost_event_retention_days,
        )

        # Initialize threshold repository
        threshold_repository = ThresholdRepository(db=db)

        # Load thresholds: MongoDB first, then config defaults
        threshold_config = await threshold_repository.get_thresholds()
        if threshold_config:
            daily_threshold = float(threshold_config.daily_threshold_usd)
            monthly_threshold = float(threshold_config.monthly_threshold_usd)
            logger.info(
                "Loaded thresholds from MongoDB",
                daily_threshold_usd=daily_threshold,
                monthly_threshold_usd=monthly_threshold,
            )
        else:
            daily_threshold = settings.budget_daily_threshold_usd
            monthly_threshold = settings.budget_monthly_threshold_usd
            logger.info(
                "Using config default thresholds",
                daily_threshold_usd=daily_threshold,
                monthly_threshold_usd=monthly_threshold,
            )

        # Initialize budget monitor
        budget_monitor = BudgetMonitor(
            daily_threshold_usd=daily_threshold,
            monthly_threshold_usd=monthly_threshold,
        )

        # Warm up from repository (CRITICAL - fail-fast if this fails)
        try:
            await budget_monitor.warm_up_from_repository(cost_repository)
            logger.info("BudgetMonitor warmed up from MongoDB")
        except Exception as e:
            logger.error("Failed to warm up BudgetMonitor", error=str(e))
            raise  # Fail-fast - better down than wrong metrics

        # Store references in app.state for handlers/servicers
        app.state.cost_repository = cost_repository
        app.state.threshold_repository = threshold_repository
        app.state.budget_monitor = budget_monitor

        # Story 13.4: Start gRPC server
        grpc_server = GrpcServer(
            cost_repository=cost_repository,
            budget_monitor=budget_monitor,
            threshold_repository=threshold_repository,
        )
        await grpc_server.start()
        app.state.grpc_server = grpc_server
        logger.info(
            "gRPC server started",
            port=settings.grpc_port,
        )

        logger.info("Service startup complete")

    except Exception as e:
        logger.error("Service startup failed", error=str(e))
        raise  # Fail-fast on critical startup errors

    yield

    # Shutdown
    logger.info("Shutting down Platform Cost service")

    # Stop gRPC server
    if grpc_server is not None:
        await grpc_server.stop()
        logger.info("gRPC server stopped")

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
