"""Collection Model Service - FastAPI entrypoint.

Quality data ingestion gateway for the Farmer Power Platform.
Collects, validates, transforms, links, stores, and serves documents
related to quality events from various sources.

Story 0.6.6: Added DAPR streaming subscriptions for blob events (ADR-010/ADR-011).
"""

import asyncio
import contextlib
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

# Import processors to register them
import collection_model.processors  # noqa: F401
import structlog
from collection_model.api import events, health
from collection_model.config import settings
from collection_model.events.subscriber import (
    run_streaming_subscriptions,
    set_blob_processor,
    set_main_event_loop,
)
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
from collection_model.infrastructure.dapr_jobs_client import DaprJobsClient
from collection_model.infrastructure.dapr_secret_client import DaprSecretClient
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.infrastructure.iteration_resolver import IterationResolver
from collection_model.infrastructure.metrics import setup_metrics, shutdown_metrics
from collection_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from collection_model.infrastructure.pull_data_fetcher import PullDataFetcher
from collection_model.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)
from collection_model.services.content_processor_worker import ContentProcessorWorker
from collection_model.services.job_registration_service import JobRegistrationService
from collection_model.services.pull_job_handler import PullJobHandler
from collection_model.services.source_config_service import SourceConfigService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Initialize OpenTelemetry tracing and metrics (must be early for other instrumentation)
    setup_tracing()
    metrics_service = setup_metrics()

    # Store metrics in app.state for dependency injection
    if metrics_service:
        app.state.event_metrics = metrics_service.events
        app.state.processing_metrics = metrics_service.processing
    else:
        app.state.event_metrics = None
        app.state.processing_metrics = None

    # Initialize DaprEventPublisher (no singleton - stored in app.state)
    app.state.event_publisher = DaprEventPublisher()

    # Initialize MongoDB connection and services
    worker_task = None
    try:
        await get_mongodb_client()
        db = await get_database()

        # Initialize SourceConfigService and IngestionQueue (Story 2.3)
        app.state.source_config_service = SourceConfigService(db)
        app.state.ingestion_queue = IngestionQueue(db)

        # Ensure indexes for ingestion queue
        await app.state.ingestion_queue.ensure_indexes()

        # Initialize Content Processor Worker (Story 2.4)
        app.state.content_processor_worker = ContentProcessorWorker(
            db=db,
            ingestion_queue=app.state.ingestion_queue,
            source_config_service=app.state.source_config_service,
            processing_metrics=app.state.processing_metrics,
        )

        # Start worker as background task
        worker_task = asyncio.create_task(app.state.content_processor_worker.start())
        app.state.worker_task = worker_task

        # Initialize DAPR Jobs Client and Job Registration Service (Story 2.7)
        app.state.dapr_jobs_client = DaprJobsClient()
        app.state.job_registration_service = JobRegistrationService(
            dapr_jobs_client=app.state.dapr_jobs_client,
            source_config_service=app.state.source_config_service,
        )

        # Sync DAPR Jobs for all scheduled_pull sources on startup
        job_sync_result = await app.state.job_registration_service.sync_all_jobs()
        logger.info(
            "DAPR Jobs synced on startup",
            registered=job_sync_result["registered"],
            skipped=job_sync_result["skipped"],
            failed=job_sync_result["failed"],
        )

        # Initialize Pull Job Handler (Story 2.7)
        # Note: The processor is obtained from worker when handling jobs
        # since it needs infrastructure dependencies set
        app.state.dapr_secret_client = DaprSecretClient()
        app.state.pull_data_fetcher = PullDataFetcher(
            dapr_secret_client=app.state.dapr_secret_client,
        )
        app.state.iteration_resolver = IterationResolver()
        app.state.pull_job_handler = PullJobHandler(
            source_config_service=app.state.source_config_service,
            pull_data_fetcher=app.state.pull_data_fetcher,
            iteration_resolver=app.state.iteration_resolver,
            processor=None,  # Processor set via set_processor after worker init
            ingestion_queue=app.state.ingestion_queue,
        )
        # Link handler to worker for processor access
        app.state.pull_job_handler.set_worker(app.state.content_processor_worker)

        health.set_mongodb_check(check_mongodb_connection)
        logger.info(
            "MongoDB connection and services initialized",
            services=[
                "SourceConfigService",
                "IngestionQueue",
                "ContentProcessorWorker",
                "JobRegistrationService",
                "PullJobHandler",
            ],
        )

        # Story 0.6.6: Set up streaming subscriptions (ADR-010/ADR-011)
        # Set the main event loop for async operations in subscription handlers
        set_main_event_loop(asyncio.get_running_loop())

        # Set blob processor services for the subscription handler
        set_blob_processor(
            source_config_service=app.state.source_config_service,
            ingestion_queue=app.state.ingestion_queue,
            event_metrics=app.state.event_metrics,
        )

        # Start streaming subscriptions in daemon thread
        subscription_thread = threading.Thread(
            target=run_streaming_subscriptions,
            name="dapr-subscriptions",
            daemon=True,
        )
        subscription_thread.start()
        app.state.subscription_thread = subscription_thread
        logger.info("DAPR streaming subscriptions thread started")

    except Exception as e:
        logger.warning("MongoDB connection failed at startup", error=str(e))
        # Service can still start - readiness probe will report not ready

    # Set up pub/sub health check using app.state.event_publisher
    health.set_pubsub_check(app.state.event_publisher.check_health)

    logger.info("Service startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Collection Model service")

    # Stop the worker
    if hasattr(app.state, "content_processor_worker"):
        await app.state.content_processor_worker.stop()
    if worker_task:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task

    await close_mongodb_connection()
    shutdown_metrics()
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
