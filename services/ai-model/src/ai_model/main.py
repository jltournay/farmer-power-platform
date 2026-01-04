"""AI Model Service - FastAPI + gRPC entrypoint.

Agent orchestration and LLM gateway for the Farmer Power Platform.
Coordinates AI agents (Extractor, Explorer, Generator, Conversational)
and provides centralized access to language models via OpenRouter.

Architecture (ADR-011):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50051: gRPC server (via DAPR sidecar)

Story 0.75.4: Added cache warming and change streams for AgentConfig and Prompt.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from ai_model.api import health
from ai_model.api.grpc_server import start_grpc_server, stop_grpc_server
from ai_model.config import settings
from ai_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from ai_model.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)
from ai_model.services import AgentConfigCache, PromptCache
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
    """Application lifespan handler for startup and shutdown events.

    Story 0.75.4: Added cache warming and change stream management (ADR-013).
    """
    # Startup
    logger.info(
        "Starting AI Model service",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
    )

    # Initialize OpenTelemetry tracing (must be early for other instrumentation)
    setup_tracing()

    # Initialize MongoDB connection
    agent_config_cache: AgentConfigCache | None = None
    prompt_cache: PromptCache | None = None

    try:
        await get_mongodb_client()
        health.set_mongodb_check(check_mongodb_connection)
        logger.info("MongoDB connection initialized")

        # Story 0.75.4: Initialize and warm caches (ADR-013)
        db = await get_database()
        agent_config_cache = AgentConfigCache(db)
        prompt_cache = PromptCache(db)

        # Warm caches before accepting requests
        logger.info("Warming caches...")
        agent_configs = await agent_config_cache.get_all()
        prompts = await prompt_cache.get_all()
        logger.info(
            "Caches warmed",
            agent_config_count=len(agent_configs),
            prompt_count=len(prompts),
        )

        # Start change stream watchers for real-time invalidation
        await agent_config_cache.start_change_stream()
        await prompt_cache.start_change_stream()
        logger.info("Change stream watchers started")

        # Store caches in app.state for dependency injection
        app.state.agent_config_cache = agent_config_cache
        app.state.prompt_cache = prompt_cache

        # Register cache services with health module
        health.set_cache_services(agent_config_cache, prompt_cache)

    except Exception as e:
        logger.warning("MongoDB/cache initialization failed at startup", error=str(e))
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
    logger.info("Shutting down AI Model service")

    # Story 0.75.4: Stop change streams
    if agent_config_cache:
        await agent_config_cache.stop_change_stream()
    if prompt_cache:
        await prompt_cache.stop_change_stream()
    logger.info("Change stream watchers stopped")

    await stop_grpc_server()
    await close_mongodb_connection()
    shutdown_tracing()

    logger.info("Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AI Model Service",
    description="Agent orchestration and LLM gateway for the Farmer Power Platform. "
    "Coordinates AI agents (Extractor, Explorer, Generator, Conversational) "
    "and provides centralized access to language models via OpenRouter.",
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
        "ai_model.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
