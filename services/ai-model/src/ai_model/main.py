"""AI Model Service - FastAPI + gRPC + DAPR Streaming entrypoint.

Agent orchestration and LLM gateway for the Farmer Power Platform.
Coordinates AI agents (Extractor, Explorer, Generator, Conversational)
and provides centralized access to language models via OpenRouter.

Architecture (ADR-011):
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50051: gRPC server (via DAPR sidecar)
- Pub/sub: DAPR streaming subscriptions (outbound, no extra port)

Story 0.75.4: Added cache warming and change streams for AgentConfig and Prompt.
Story 0.75.8: Added DAPR streaming subscriptions and DLQ handling.
Story 0.75.8b: Added MCP integration for agent workflows.
Story 0.75.16b: Wired AgentExecutor and WorkflowExecutionService for event processing.
"""

import asyncio
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from ai_model.api import health
from ai_model.api.grpc_server import start_grpc_server, stop_grpc_server
from ai_model.config import settings
from ai_model.events.publisher import EventPublisher
from ai_model.events.subscriber import (
    run_streaming_subscriptions,
    set_agent_config_cache,
    set_agent_executor,
    set_main_event_loop,
)
from ai_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from ai_model.infrastructure.repositories import LlmCostEventRepository
from ai_model.infrastructure.tracing import (
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)
from ai_model.llm import LLMGateway, RateLimiter
from ai_model.llm.budget_monitor import BudgetMonitor
from ai_model.mcp import AgentToolProvider, McpIntegration
from ai_model.services import AgentConfigCache, AgentExecutor, PromptCache
from ai_model.workflows.execution_service import WorkflowExecutionService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fp_common import configure_logging, create_admin_router
from fp_common.events import (
    DLQRepository,
    set_dlq_event_loop,
    set_dlq_repository,
    start_dlq_subscription,
)

# Configure structured logging via fp_common (ADR-009)
configure_logging("ai-model")

logger = structlog.get_logger("ai_model.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    Story 0.75.4: Added cache warming and change stream management (ADR-013).
    Story 0.75.5: Added LLM Gateway initialization with validate_models().
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
    llm_gateway: LLMGateway | None = None

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

        # Story 0.75.8b: Initialize MCP integration for agent workflows
        mcp_integration = McpIntegration(cache_ttl_seconds=settings.mcp_tool_cache_ttl_seconds)

        # Extract unique servers from all cached agent configs and register
        # Note: agent_configs is a dict[str, AgentConfig], need to pass values as list
        registered_servers = mcp_integration.register_from_agent_configs(list(agent_configs.values()))
        logger.info("Registered MCP servers", servers=list(registered_servers))

        # Discover tools from all servers (graceful failure - startup continues)
        try:
            await mcp_integration.discover_all_tools()
            logger.info("MCP tools discovered from all servers")
        except Exception as e:
            logger.warning(
                "Some MCP servers unavailable at startup - tools will be discovered on first access",
                error=str(e),
            )

        # Create tool provider for agents to resolve mcp_sources
        tool_provider = AgentToolProvider(mcp_integration)

        # Store in app.state for dependency injection
        app.state.mcp_integration = mcp_integration
        app.state.tool_provider = tool_provider

        # Story 0.75.8: Set up DAPR streaming subscriptions (ADR-010, ADR-011)
        # CRITICAL: Pass the main event loop to streaming subscription handlers
        # The handlers run in a separate thread, but Motor (MongoDB) and other
        # async clients are bound to this loop. Handlers use run_coroutine_threadsafe()
        # to schedule async operations on this loop.
        main_loop = asyncio.get_running_loop()
        set_main_event_loop(main_loop)
        set_agent_config_cache(agent_config_cache)
        logger.info("Subscription handler dependencies configured")

        # Initialize DLQ repository and configure DLQ handler (ADR-006)
        dlq_repository = DLQRepository(db["event_dead_letter"])
        set_dlq_repository(dlq_repository)
        set_dlq_event_loop(main_loop)
        logger.info("DLQ handler dependencies configured")

        # Start DAPR streaming subscriptions in background thread
        # ADR-010/011 pattern: run_streaming_subscriptions keeps DaprClient alive
        # Subscriptions are outbound - no extra HTTP port needed
        subscription_thread = threading.Thread(
            target=run_streaming_subscriptions,
            daemon=True,
            name="dapr-ai-subscriptions",
        )
        subscription_thread.start()
        logger.info("DAPR streaming subscriptions thread started")

        # Start DLQ subscription in separate thread
        # DLQ handler stores failed events in MongoDB for inspection and replay
        dlq_thread = threading.Thread(
            target=start_dlq_subscription,
            daemon=True,
            name="dapr-dlq-subscription",
        )
        dlq_thread.start()
        logger.info("DLQ subscription thread started")

        # Story 0.75.5: Initialize LLM Gateway (AC15)
        if settings.openrouter_api_key:
            cost_repository = LlmCostEventRepository(db)
            await cost_repository.ensure_indexes()

            budget_monitor = BudgetMonitor(
                daily_threshold_usd=settings.llm_cost_alert_daily_usd,
                monthly_threshold_usd=settings.llm_cost_alert_monthly_usd,
            )

            rate_limiter = RateLimiter(
                rpm=settings.llm_rate_limit_rpm,
                tpm=settings.llm_rate_limit_tpm,
            )

            llm_gateway = LLMGateway(
                api_key=settings.openrouter_api_key,
                fallback_models=settings.llm_fallback_models,
                rate_limiter=rate_limiter,
                retry_max_attempts=settings.llm_retry_max_attempts,
                retry_backoff_ms=settings.llm_retry_backoff_ms,
                site_url=settings.openrouter_site_url,
                site_name=settings.openrouter_site_name,
                cost_tracking_enabled=settings.llm_cost_tracking_enabled,
                cost_repository=cost_repository,
                budget_monitor=budget_monitor,
            )

            # Validate models at startup (AC5, AC15)
            try:
                available_models = await llm_gateway.validate_models()
                logger.info(
                    "LLM Gateway initialized and models validated",
                    model_count=len(available_models),
                )
            except Exception as e:
                logger.warning(
                    "Failed to validate OpenRouter models at startup",
                    error=str(e),
                )

            # Store in app.state for dependency injection
            app.state.llm_gateway = llm_gateway
            app.state.budget_monitor = budget_monitor

            # Story 0.75.16b: Initialize WorkflowExecutionService
            workflow_service = WorkflowExecutionService(
                mongodb_uri=settings.mongodb_uri,
                mongodb_database=settings.mongodb_database,
                llm_gateway=llm_gateway,
                ranking_service=None,  # TODO: Wire ranking service in Story 0.75.15
                mcp_integration=mcp_integration,
                tool_provider=tool_provider,  # Story 0.75.16b: Wire AgentToolProvider
            )

            # Story 0.75.16b: Create EventPublisher for agent result events
            event_publisher = EventPublisher()

            # Story 0.75.16b: Create AgentExecutor and wire to subscriber
            agent_executor = AgentExecutor(
                agent_config_cache=agent_config_cache,
                prompt_cache=prompt_cache,
                workflow_service=workflow_service,
                event_publisher=event_publisher,
            )
            set_agent_executor(agent_executor)

            # Store in app.state for dependency injection
            app.state.workflow_service = workflow_service
            app.state.event_publisher = event_publisher
            app.state.agent_executor = agent_executor

            logger.info("AgentExecutor wired to subscriber")

        else:
            logger.warning("OpenRouter API key not configured, LLM Gateway not initialized")

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

    # Story 0.75.8: Streaming subscriptions run in daemon threads with own cleanup
    # The threads will be terminated when the main process exits
    logger.info("Subscriptions will be closed by daemon threads")

    # Story 0.75.4: Stop change streams
    if agent_config_cache:
        await agent_config_cache.stop_change_stream()
    if prompt_cache:
        await prompt_cache.stop_change_stream()
    logger.info("Change stream watchers stopped")

    # Story 0.75.5: Close LLM Gateway
    if llm_gateway:
        await llm_gateway.close()
        logger.info("LLM Gateway closed")

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
        "ai_model.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
