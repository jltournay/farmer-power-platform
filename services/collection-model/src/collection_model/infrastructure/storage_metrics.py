"""OpenTelemetry metrics for document storage.

This module provides metrics tracking for document storage operations
including successful stores and duplicate detection. Metrics are exported
via DAPR's OpenTelemetry integration to Prometheus/Grafana.
"""

from opentelemetry import metrics

# Get meter for collection-model service
meter = metrics.get_meter("collection-model")

# Counter for total documents processed (stored or duplicate)
documents_counter = meter.create_counter(
    name="collection_documents_total",
    description="Total documents processed by status (stored/duplicate)",
    unit="1",
)

# Counter for total bytes stored
storage_bytes_counter = meter.create_counter(
    name="collection_storage_bytes_total",
    description="Total bytes stored in blob storage",
    unit="By",
)

# Counter for pull job fetch operations (Story 2.7)
pull_fetch_counter = meter.create_counter(
    name="collection_pull_fetch_total",
    description="Total pull fetch operations by status (success/failed)",
    unit="1",
)


class StorageMetrics:
    """OpenTelemetry metrics for document storage operations.

    Provides static methods to record storage events:
    - record_stored: When a document is successfully stored
    - record_duplicate: When a duplicate document is detected and skipped

    Metrics are labeled by source_id for per-source analysis.
    """

    @staticmethod
    def record_stored(source_id: str, size_bytes: int) -> None:
        """Record a successfully stored document.

        Args:
            source_id: ID of the source configuration.
            size_bytes: Size of the stored document in bytes.
        """
        documents_counter.add(1, {"source_id": source_id, "status": "stored"})
        storage_bytes_counter.add(size_bytes, {"source_id": source_id})

    @staticmethod
    def record_duplicate(source_id: str) -> None:
        """Record a duplicate document detection.

        Args:
            source_id: ID of the source configuration.
        """
        documents_counter.add(1, {"source_id": source_id, "status": "duplicate"})

    @staticmethod
    def record_pull_fetch_success(source_id: str) -> None:
        """Record a successful pull fetch operation (Story 2.7).

        Args:
            source_id: ID of the source configuration.
        """
        pull_fetch_counter.add(1, {"source_id": source_id, "status": "success"})

    @staticmethod
    def record_pull_fetch_failed(source_id: str) -> None:
        """Record a failed pull fetch operation (Story 2.7).

        Args:
            source_id: ID of the source configuration.
        """
        pull_fetch_counter.add(1, {"source_id": source_id, "status": "failed"})
