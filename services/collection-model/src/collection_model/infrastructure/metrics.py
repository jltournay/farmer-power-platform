"""OpenTelemetry metrics for Collection Model service.

This module provides metrics instrumentation for event processing
using OpenTelemetry's metrics API.
"""

import structlog
from collection_model.config import settings
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logger = structlog.get_logger(__name__)

# Global meter for creating metrics
_meter: metrics.Meter | None = None

# Global counters (initialized on setup)
_events_received_counter: metrics.Counter | None = None
_events_queued_counter: metrics.Counter | None = None
_events_duplicate_counter: metrics.Counter | None = None
_events_unmatched_counter: metrics.Counter | None = None
_events_disabled_counter: metrics.Counter | None = None


def setup_metrics() -> None:
    """Configure OpenTelemetry metrics with OTLP exporter.

    Sets up:
    - MeterProvider with service resource attributes
    - OTLP gRPC exporter for metrics collector
    - Event processing counters
    """
    global _meter, _events_received_counter, _events_queued_counter
    global _events_duplicate_counter, _events_unmatched_counter, _events_disabled_counter

    if not settings.otel_enabled:
        logger.info("OpenTelemetry metrics disabled")
        return

    logger.info(
        "Configuring OpenTelemetry metrics",
        service=settings.service_name,
        endpoint=settings.otel_exporter_endpoint,
    )

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.service_version,
            "service.namespace": settings.otel_service_namespace,
            "deployment.environment": settings.environment,
        },
    )

    # Configure OTLP metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.otel_exporter_endpoint,
        insecure=settings.otel_exporter_insecure,
    )

    # Create metric reader with periodic export
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=30000,  # Export every 30 seconds
    )

    # Create and set meter provider
    provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(provider)

    # Create meter for this service
    _meter = metrics.get_meter(
        name="collection_model",
        version=settings.service_version,
    )

    # Create counters for event processing
    _events_received_counter = _meter.create_counter(
        name="collection.events.received",
        description="Number of blob-created events received",
        unit="1",
    )

    _events_queued_counter = _meter.create_counter(
        name="collection.events.queued",
        description="Number of events successfully queued for processing",
        unit="1",
    )

    _events_duplicate_counter = _meter.create_counter(
        name="collection.events.duplicate",
        description="Number of duplicate events skipped",
        unit="1",
    )

    _events_unmatched_counter = _meter.create_counter(
        name="collection.events.unmatched",
        description="Number of events with no matching source config",
        unit="1",
    )

    _events_disabled_counter = _meter.create_counter(
        name="collection.events.disabled",
        description="Number of events skipped due to disabled source",
        unit="1",
    )

    logger.info("OpenTelemetry metrics configured successfully")


def increment_events_received(source_id: str = "unknown") -> None:
    """Increment the events received counter.

    Args:
        source_id: The source configuration ID for the event.
    """
    if _events_received_counter:
        _events_received_counter.add(1, {"source_id": source_id})


def increment_events_queued(source_id: str) -> None:
    """Increment the events queued counter.

    Args:
        source_id: The source configuration ID for the event.
    """
    if _events_queued_counter:
        _events_queued_counter.add(1, {"source_id": source_id})


def increment_events_duplicate(source_id: str) -> None:
    """Increment the duplicate events counter.

    Args:
        source_id: The source configuration ID for the event.
    """
    if _events_duplicate_counter:
        _events_duplicate_counter.add(1, {"source_id": source_id})


def increment_events_unmatched(container: str) -> None:
    """Increment the unmatched events counter.

    Args:
        container: The container name that had no matching config.
    """
    if _events_unmatched_counter:
        _events_unmatched_counter.add(1, {"container": container})


def increment_events_disabled(source_id: str) -> None:
    """Increment the disabled events counter.

    Args:
        source_id: The disabled source configuration ID.
    """
    if _events_disabled_counter:
        _events_disabled_counter.add(1, {"source_id": source_id})


def get_meter() -> metrics.Meter | None:
    """Get the global meter for creating additional metrics.

    Returns:
        The OpenTelemetry Meter or None if not initialized.
    """
    return _meter


def shutdown_metrics() -> None:
    """Shutdown metrics and flush pending data."""
    if not settings.otel_enabled:
        return

    logger.info("Shutting down OpenTelemetry metrics")
    provider = metrics.get_meter_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    logger.info("OpenTelemetry metrics shutdown complete")
