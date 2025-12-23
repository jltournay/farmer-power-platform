"""OpenTelemetry tracing configuration for Plantation Model service."""

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient, GrpcInstrumentorServer
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from plantation_model.config import settings

logger = structlog.get_logger(__name__)


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing with OTLP exporter.

    Sets up:
    - TracerProvider with service resource attributes
    - OTLP gRPC exporter for Jaeger/Tempo/OTEL Collector
    - Auto-instrumentation for FastAPI, gRPC, and PyMongo
    """
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled")
        return

    logger.info(
        "Configuring OpenTelemetry tracing",
        service=settings.service_name,
        endpoint=settings.otel_exporter_endpoint,
    )

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.service_version,
            "service.namespace": "farmer-power",
            "deployment.environment": settings.environment,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_endpoint,
        insecure=True,  # Use TLS in production
    )

    # Add batch span processor for efficient export
    provider.add_span_processor(
        BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
    )

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument libraries
    _instrument_libraries()

    logger.info("OpenTelemetry tracing configured successfully")


def _instrument_libraries() -> None:
    """Auto-instrument supported libraries."""
    # Instrument PyMongo for database tracing
    try:
        PymongoInstrumentor().instrument()
        logger.debug("PyMongo instrumented")
    except Exception as e:
        logger.warning("Failed to instrument PyMongo", error=str(e))

    # Instrument gRPC client and server
    try:
        GrpcInstrumentorClient().instrument()
        GrpcInstrumentorServer().instrument()
        logger.debug("gRPC instrumented")
    except Exception as e:
        logger.warning("Failed to instrument gRPC", error=str(e))


def instrument_fastapi(app: "FastAPI") -> None:  # noqa: F821
    """Instrument a FastAPI application.

    Must be called after app creation but before startup.

    Args:
        app: The FastAPI application instance.
    """
    if not settings.otel_enabled:
        return

    try:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,ready,metrics",
        )
        logger.debug("FastAPI instrumented")
    except Exception as e:
        logger.warning("Failed to instrument FastAPI", error=str(e))


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for creating spans.

    Args:
        name: The name for the tracer (typically __name__).

    Returns:
        Tracer: An OpenTelemetry tracer instance.
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Shutdown tracing and flush pending spans."""
    if not settings.otel_enabled:
        return

    logger.info("Shutting down OpenTelemetry tracing")
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    logger.info("OpenTelemetry tracing shutdown complete")
