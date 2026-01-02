"""OpenTelemetry tracing setup for BFF service.

Configures distributed tracing per ADR-002 and project-context.md.
"""

import structlog
from bff.config import get_settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing for the BFF service.

    Sets up:
    - TracerProvider with service name
    - OTLP exporter for sending traces to collector
    - FastAPI instrumentation for automatic span creation

    This is called during application lifespan startup.
    """
    settings = get_settings()

    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled")
        return

    logger.info(
        "Configuring OpenTelemetry tracing",
        endpoint=settings.otel_endpoint,
        service_name=settings.otel_service_name,
    )

    # Create resource with service name
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_endpoint,
        insecure=True,
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    logger.info("OpenTelemetry tracing configured")


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application for automatic tracing.

    Args:
        app: The FastAPI application instance.
    """
    settings = get_settings()

    if not settings.otel_enabled:
        return

    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumentation enabled")
