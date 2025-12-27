"""OpenTelemetry metrics for Collection Model service.

This module provides metrics instrumentation for event processing
using OpenTelemetry's metrics API.

Metrics are encapsulated in service classes to avoid module-level state
and enable proper dependency injection.
"""

import structlog
from collection_model.config import settings
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logger = structlog.get_logger(__name__)


class EventMetrics:
    """Metrics for event ingestion (blob-created events).

    Encapsulates all event-related counters to avoid module-level state.
    """

    def __init__(self, meter: metrics.Meter) -> None:
        """Initialize event metrics.

        Args:
            meter: OpenTelemetry Meter for creating counters.
        """
        self.events_received = meter.create_counter(
            name="collection.events.received",
            description="Number of blob-created events received",
            unit="1",
        )
        self.events_queued = meter.create_counter(
            name="collection.events.queued",
            description="Number of events successfully queued for processing",
            unit="1",
        )
        self.events_duplicate = meter.create_counter(
            name="collection.events.duplicate",
            description="Number of duplicate events skipped",
            unit="1",
        )
        self.events_unmatched = meter.create_counter(
            name="collection.events.unmatched",
            description="Number of events with no matching source config",
            unit="1",
        )
        self.events_disabled = meter.create_counter(
            name="collection.events.disabled",
            description="Number of events skipped due to disabled source",
            unit="1",
        )

    def increment_received(self, source_id: str = "unknown") -> None:
        """Increment the events received counter."""
        self.events_received.add(1, {"source_id": source_id})

    def increment_queued(self, source_id: str) -> None:
        """Increment the events queued counter."""
        self.events_queued.add(1, {"source_id": source_id})

    def increment_duplicate(self, source_id: str) -> None:
        """Increment the duplicate events counter."""
        self.events_duplicate.add(1, {"source_id": source_id})

    def increment_unmatched(self, container: str) -> None:
        """Increment the unmatched events counter."""
        self.events_unmatched.add(1, {"container": container})

    def increment_disabled(self, source_id: str) -> None:
        """Increment the disabled events counter."""
        self.events_disabled.add(1, {"source_id": source_id})


class ProcessingMetrics:
    """Metrics for content processing (worker jobs).

    Encapsulates all processing-related counters and histograms
    to avoid module-level state.
    """

    def __init__(self, meter: metrics.Meter) -> None:
        """Initialize processing metrics.

        Args:
            meter: OpenTelemetry Meter for creating instruments.
        """
        self.processing_completed = meter.create_counter(
            name="collection.processing.completed",
            description="Number of jobs processed successfully",
            unit="1",
        )
        self.processing_errors = meter.create_counter(
            name="collection.processing.errors",
            description="Number of processing errors",
            unit="1",
        )
        self.processing_duration = meter.create_histogram(
            name="collection.processing.duration",
            description="Processing duration in seconds",
            unit="s",
        )

    def record_success(self, source_id: str, duration: float) -> None:
        """Record a successful processing job."""
        labels = {"source_id": source_id}
        self.processing_completed.add(1, labels)
        self.processing_duration.record(duration, labels)

    def record_error(self, source_id: str, duration: float, error_type: str) -> None:
        """Record a failed processing job."""
        labels = {"source_id": source_id}
        self.processing_errors.add(1, {**labels, "error_type": error_type})
        self.processing_duration.record(duration, labels)


class MetricsService:
    """Central metrics service for the Collection Model.

    Provides access to all metric instruments. Initialized once at startup
    and injected as a dependency where needed.
    """

    def __init__(self, meter: metrics.Meter) -> None:
        """Initialize all metrics.

        Args:
            meter: OpenTelemetry Meter for creating instruments.
        """
        self.meter = meter
        self.events = EventMetrics(meter)
        self.processing = ProcessingMetrics(meter)


# Metrics service instance (set by setup_metrics)
_metrics_service: MetricsService | None = None


def setup_metrics() -> MetricsService | None:
    """Configure OpenTelemetry metrics with OTLP exporter.

    Sets up:
    - MeterProvider with service resource attributes
    - OTLP gRPC exporter for metrics collector
    - MetricsService with all counters and histograms

    Returns:
        MetricsService instance or None if disabled.
    """
    global _metrics_service

    if not settings.otel_enabled:
        logger.info("OpenTelemetry metrics disabled")
        return None

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
    meter = metrics.get_meter(
        name="collection_model",
        version=settings.service_version,
    )

    # Create and store metrics service
    _metrics_service = MetricsService(meter)

    logger.info("OpenTelemetry metrics configured successfully")
    return _metrics_service


def get_metrics_service() -> MetricsService | None:
    """Get the metrics service instance.

    Returns:
        MetricsService or None if not initialized or disabled.
    """
    return _metrics_service


def shutdown_metrics() -> None:
    """Shutdown metrics and flush pending data."""
    if not settings.otel_enabled:
        return

    logger.info("Shutting down OpenTelemetry metrics")
    provider = metrics.get_meter_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    logger.info("OpenTelemetry metrics shutdown complete")
