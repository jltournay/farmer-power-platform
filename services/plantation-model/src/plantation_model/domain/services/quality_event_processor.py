"""Quality Event Processor - orchestrates quality result event processing.

Story 1.7: Quality Grading Event Subscription

This service processes quality result events from Collection Model:
1. Fetches the full document from Collection Model
2. Loads the GradingModel for grade label lookup
3. Extracts grade counts dynamically using grading model's grade_labels
4. Updates FarmerPerformance metrics
5. Emits plantation.quality.graded event
6. Computes performance summary
7. Emits plantation.performance_updated event for Engagement Model
"""

import datetime as dt
from datetime import datetime
from typing import Any

import structlog
from opentelemetry import trace
from plantation_model.config import settings
from plantation_model.domain.models.farmer_performance import TrendDirection
from plantation_model.infrastructure.collection_client import (
    CollectionClient,
    CollectionClientError,
    DocumentNotFoundError,
)
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class QualityEventProcessingError(Exception):
    """Raised when quality event processing fails."""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        farmer_id: str | None = None,
        error_type: str = "processing_error",
        cause: Exception | None = None,
    ) -> None:
        self.document_id = document_id
        self.farmer_id = farmer_id
        self.error_type = error_type
        self.cause = cause
        super().__init__(message)


class QualityEventProcessor:
    """Processes quality result events and updates farmer performance.

    This is the main orchestrator for Story 1.7, implementing the event
    processing pipeline that connects Collection Model events to
    FarmerPerformance updates and downstream notifications.

    Key Design Principles:
    - Model-Driven: Grade labels come from GradingModel, not hardcoded
    - Atomic Updates: Uses MongoDB $inc for thread-safe counter updates
    - Event Sourcing: Emits events for downstream consumers (Engagement Model)
    """

    def __init__(
        self,
        collection_client: CollectionClient,
        grading_model_repo: GradingModelRepository,
        farmer_performance_repo: FarmerPerformanceRepository,
        event_publisher: DaprPubSubClient | None = None,
    ) -> None:
        """Initialize the processor with required dependencies.

        Args:
            collection_client: Client for fetching documents from Collection Model.
            grading_model_repo: Repository for loading grading models.
            farmer_performance_repo: Repository for updating farmer performance.
            event_publisher: Optional DAPR pub/sub client for event emission.
        """
        self._collection_client = collection_client
        self._grading_model_repo = grading_model_repo
        self._farmer_performance_repo = farmer_performance_repo
        self._event_publisher = event_publisher

    async def process(
        self,
        document_id: str,
        farmer_id: str,
        batch_timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Process a quality result event.

        Main entry point called by the DAPR subscription handler.
        Orchestrates the full processing pipeline:
        1. Fetch document from Collection Model
        2. Load grading model
        3. Extract grade counts
        4. Update farmer performance
        5. Emit domain events

        Args:
            document_id: The Collection Model document ID.
            farmer_id: The farmer/plantation ID.
            batch_timestamp: Optional timestamp of the QC batch.

        Returns:
            Dict with processing results including grade_counts and events emitted.

        Raises:
            QualityEventProcessingError: If processing fails.
        """
        with tracer.start_as_current_span("process_quality_event") as span:
            span.set_attribute("document_id", document_id)
            span.set_attribute("farmer_id", farmer_id)

            try:
                # Step 1: Fetch document from Collection Model
                document = await self._fetch_document(document_id)

                # Step 2: Extract grading model reference from document
                grading_model_id = self._get_grading_model_id(document)
                grading_model_version = self._get_grading_model_version(document)

                if not grading_model_id:
                    raise QualityEventProcessingError(
                        "Document missing grading_model_id",
                        document_id=document_id,
                        farmer_id=farmer_id,
                        error_type="missing_grading_model",
                    )

                # Step 3: Load grading model
                grading_model = await self._load_grading_model(grading_model_id, grading_model_version)

                if grading_model is None:
                    raise QualityEventProcessingError(
                        f"Grading model not found: {grading_model_id}@{grading_model_version}",
                        document_id=document_id,
                        farmer_id=farmer_id,
                        error_type="grading_model_not_found",
                    )

                # Step 4: Extract quality metrics from document
                bag_summary = self._get_bag_summary(document)
                grade_counts = self._extract_grade_counts(bag_summary, grading_model)
                attribute_distribution = self._extract_attribute_distribution(bag_summary, grading_model)
                total_weight_kg = self._get_total_weight(bag_summary)

                span.set_attribute("grade_counts", str(grade_counts))
                span.set_attribute("total_weight_kg", total_weight_kg)

                # Step 5: Check for date rollover and update farmer performance
                performance = await self._update_farmer_performance(
                    farmer_id=farmer_id,
                    grade_counts=grade_counts,
                    attribute_counts=attribute_distribution,
                    weight_kg=total_weight_kg,
                )

                if performance is None:
                    logger.warning(
                        "Farmer performance not found - skipping update",
                        farmer_id=farmer_id,
                        document_id=document_id,
                    )
                    # Don't raise - farmer might not exist yet
                    # Return early with partial result
                    return {
                        "status": "skipped",
                        "reason": "farmer_not_found",
                        "document_id": document_id,
                        "farmer_id": farmer_id,
                    }

                # Step 6: Emit plantation.quality.graded event
                await self._emit_quality_graded_event(
                    farmer_id=farmer_id,
                    document_id=document_id,
                    grading_model_id=grading_model_id,
                    grading_model_version=grading_model_version or "unknown",
                    grade_counts=grade_counts,
                    attribute_distribution=attribute_distribution,
                )

                # Step 7: Compute performance summary and emit update event
                factory_id = self._get_factory_id(document)
                primary_percentage = self._compute_primary_percentage(performance.today.grade_counts)
                improvement_trend = self._compute_improvement_trend(performance)

                await self._emit_performance_updated_event(
                    farmer_id=farmer_id,
                    factory_id=factory_id,
                    primary_percentage=primary_percentage,
                    improvement_trend=improvement_trend,
                    today_summary={
                        "deliveries": performance.today.deliveries,
                        "total_kg": performance.today.total_kg,
                        "grade_counts": performance.today.grade_counts,
                    },
                    triggered_by_document_id=document_id,
                )

                span.set_attribute("processing.success", True)

                return {
                    "status": "success",
                    "document_id": document_id,
                    "farmer_id": farmer_id,
                    "grade_counts": grade_counts,
                    "primary_percentage": primary_percentage,
                    "improvement_trend": improvement_trend.value,
                }

            except QualityEventProcessingError:
                raise
            except DocumentNotFoundError as e:
                raise QualityEventProcessingError(
                    f"Document not found: {document_id}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="document_not_found",
                    cause=e,
                ) from e
            except CollectionClientError as e:
                raise QualityEventProcessingError(
                    f"Failed to fetch document: {e}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="collection_client_error",
                    cause=e,
                ) from e
            except Exception as e:
                logger.exception(
                    "Unexpected error processing quality event",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error=str(e),
                )
                raise QualityEventProcessingError(
                    f"Unexpected error: {e}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="unexpected_error",
                    cause=e,
                ) from e

    async def _fetch_document(self, document_id: str) -> dict[str, Any]:
        """Fetch quality document from Collection Model."""
        with tracer.start_as_current_span("fetch_document"):
            document = await self._collection_client.get_document(document_id)
            logger.debug(
                "Fetched document from Collection Model",
                document_id=document_id,
                source_id=document.get("source_id"),
            )
            return document

    async def _load_grading_model(self, model_id: str, model_version: str | None):
        """Load grading model by ID and version."""
        with tracer.start_as_current_span("load_grading_model"):
            if model_version:
                # Use versioned lookup for exact match
                model = await self._grading_model_repo.get_by_id_and_version(model_id, model_version)
            else:
                # Fallback to latest version
                model = await self._grading_model_repo.get_by_id(model_id)

            if model:
                logger.debug(
                    "Loaded grading model",
                    model_id=model_id,
                    model_version=model.model_version,
                )
            return model

    def _get_grading_model_id(self, document: dict[str, Any]) -> str | None:
        """Extract grading model ID from document."""
        # Check extracted_fields first (where DocumentIndex stores it)
        extracted_fields = document.get("extracted_fields", {})
        if "grading_model_id" in extracted_fields:
            return extracted_fields["grading_model_id"]
        # Check linkage_fields (also populated by DocumentIndex)
        linkage_fields = document.get("linkage_fields", {})
        if "grading_model_id" in linkage_fields:
            return linkage_fields["grading_model_id"]
        # Check top-level (raw document fallback)
        return document.get("grading_model_id")

    def _get_grading_model_version(self, document: dict[str, Any]) -> str | None:
        """Extract grading model version from document."""
        # Check extracted_fields first (where DocumentIndex stores it)
        extracted_fields = document.get("extracted_fields", {})
        if "grading_model_version" in extracted_fields:
            return extracted_fields["grading_model_version"]
        # Check top-level (raw document fallback)
        return document.get("grading_model_version")

    def _get_factory_id(self, document: dict[str, Any]) -> str:
        """Extract factory ID from document."""
        # Check extracted_fields first (where DocumentIndex stores it)
        extracted_fields = document.get("extracted_fields", {})
        if "factory_id" in extracted_fields:
            return extracted_fields["factory_id"]
        # Check linkage_fields (also populated by DocumentIndex)
        linkage_fields = document.get("linkage_fields", {})
        if "factory_id" in linkage_fields:
            return linkage_fields["factory_id"]
        # Check top-level (raw document fallback)
        return document.get("factory_id", "unknown")

    def _get_bag_summary(self, document: dict[str, Any]) -> dict[str, Any]:
        """Extract bag summary from document."""
        # Check extracted_fields first (where DocumentIndex stores it)
        extracted_fields = document.get("extracted_fields", {})
        if "bag_summary" in extracted_fields:
            return extracted_fields["bag_summary"]
        # Check top-level (raw document fallback)
        return document.get("bag_summary", {})

    def _get_total_weight(self, bag_summary: dict[str, Any]) -> float:
        """Extract total weight from bag summary."""
        return float(bag_summary.get("total_weight_kg", 0.0))

    def _extract_grade_counts(self, bag_summary: dict[str, Any], grading_model) -> dict[str, int]:
        """Extract grade counts dynamically using grading model labels.

        The QC result contains grade distribution (counts or percentages).
        We extract counts for each grade label defined in the grading model.

        This is MODEL-DRIVEN: no hardcoded grade labels like "primary"/"secondary".
        """
        grade_counts: dict[str, int] = {}

        # Get grade labels from the grading model
        grade_labels = grading_model.grade_labels or {}

        # The bag_summary may have grade counts directly or as percentages
        # Check for direct counts first
        if "grade_counts" in bag_summary:
            counts_data = bag_summary["grade_counts"]
            for label in grade_labels.values():
                if label in counts_data:
                    grade_counts[label] = int(counts_data[label])
        else:
            # Derive from percentages if counts not available
            # Each delivery = 1 bag, so increment by 1 for the primary grade
            # Use overall_grade or primary_percentage to determine grade
            primary_pct = bag_summary.get("primary_percentage", 0)

            # For now, count as 1 delivery, use threshold to assign grade
            # This is a simplification - in reality, QC provides detailed counts
            grade_values = list(grade_labels.values()) if grade_labels else ["Primary"]
            if primary_pct >= 50:
                # Assign to first grade label (typically "Primary" or "A")
                first_label = grade_values[0]
                grade_counts[first_label] = 1
            else:
                # Assign to second grade label (typically "Secondary" or "B")
                if len(grade_values) >= 2:
                    second_label = grade_values[1]
                    grade_counts[second_label] = 1
                else:
                    # Single grade system - always increment
                    first_label = grade_values[0]
                    grade_counts[first_label] = 1

        return grade_counts

    def _extract_attribute_distribution(self, bag_summary: dict[str, Any], grading_model) -> dict[str, dict[str, int]]:
        """Extract attribute distribution from bag summary.

        Uses grading model's attributes list to know which attributes to track.
        """
        distribution: dict[str, dict[str, int]] = {}

        # Get attribute distribution from bag summary
        leaf_type_dist = bag_summary.get("leaf_type_distribution", {})

        if leaf_type_dist:
            # Normalize to integers
            distribution["leaf_type"] = {k: int(v) for k, v in leaf_type_dist.items() if isinstance(v, (int, float))}

        # Could extract more attributes based on grading_model.attributes
        # For now, focus on leaf_type_distribution which is in the schema

        return distribution

    async def _update_farmer_performance(
        self,
        farmer_id: str,
        grade_counts: dict[str, int],
        attribute_counts: dict[str, dict[str, int]],
        weight_kg: float,
    ):
        """Update farmer performance with quality metrics.

        Handles date rollover - if it's a new day, resets today metrics first.
        Uses atomic $inc operations for thread-safe updates.
        """
        with tracer.start_as_current_span("update_farmer_performance"):
            # Get current performance to check date
            performance = await self._farmer_performance_repo.get_by_farmer_id(farmer_id)

            if performance is None:
                return None

            # Check for date rollover
            today = dt.date.today()
            if performance.today.metrics_date != today:
                logger.info(
                    "Date rollover detected - resetting today metrics",
                    farmer_id=farmer_id,
                    old_date=performance.today.metrics_date.isoformat(),
                    new_date=today.isoformat(),
                )
                performance = await self._farmer_performance_repo.reset_today(farmer_id)

            # Determine primary grade for increment (first grade in counts)
            primary_grade = next(iter(grade_counts.keys())) if grade_counts else "Primary"

            # Increment today's metrics atomically
            performance = await self._farmer_performance_repo.increment_today_delivery(
                farmer_id=farmer_id,
                kg_amount=weight_kg,
                grade=primary_grade,
                attribute_counts=attribute_counts,
            )

            if performance:
                logger.info(
                    "Updated farmer performance",
                    farmer_id=farmer_id,
                    deliveries=performance.today.deliveries,
                    total_kg=performance.today.total_kg,
                    grade_counts=performance.today.grade_counts,
                )

            return performance

    def _compute_primary_percentage(self, grade_counts: dict[str, int]) -> float:
        """Compute primary percentage from today's grade counts.

        Returns the percentage of the first grade label (typically "Primary").
        """
        if not grade_counts:
            return 0.0

        total = sum(grade_counts.values())
        if total == 0:
            return 0.0

        # First grade is assumed to be "primary" quality
        first_label = next(iter(grade_counts.keys()), None)
        if first_label is None:
            return 0.0

        primary_count = grade_counts.get(first_label, 0)
        return (primary_count / total) * 100.0

    def _compute_improvement_trend(self, performance) -> TrendDirection:
        """Compute improvement trend from historical data.

        Compares 30-day vs 90-day primary percentage to determine trend.
        """
        pct_30d = performance.historical.primary_percentage_30d
        pct_90d = performance.historical.primary_percentage_90d

        # If no historical data, return stable
        if pct_30d == 0.0 and pct_90d == 0.0:
            return performance.historical.improvement_trend

        # Compare with 5% threshold
        if pct_30d > pct_90d + 5.0:
            return TrendDirection.IMPROVING
        elif pct_30d < pct_90d - 5.0:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE

    async def _emit_quality_graded_event(
        self,
        farmer_id: str,
        document_id: str,
        grading_model_id: str,
        grading_model_version: str,
        grade_counts: dict[str, int],
        attribute_distribution: dict[str, dict[str, int]],
    ) -> bool:
        """Emit plantation.quality.graded event via DAPR pub/sub."""
        if self._event_publisher is None:
            logger.debug(
                "Event publisher not configured - skipping quality.graded event",
                farmer_id=farmer_id,
            )
            return False

        payload = {
            "event_type": "plantation.quality.graded",
            "farmer_id": farmer_id,
            "document_id": document_id,
            "grading_model_id": grading_model_id,
            "grading_model_version": grading_model_version,
            "grade_counts": grade_counts,
            "attribute_distribution": attribute_distribution,
            "timestamp": datetime.now(dt.UTC).isoformat(),
        }

        success = await self._event_publisher.publish_event(
            pubsub_name=settings.dapr_pubsub_name,
            topic="plantation.quality.graded",
            data=payload,
        )

        if success:
            logger.info(
                "Emitted plantation.quality.graded event",
                farmer_id=farmer_id,
                document_id=document_id,
            )
        return success

    async def _emit_performance_updated_event(
        self,
        farmer_id: str,
        factory_id: str,
        primary_percentage: float,
        improvement_trend: TrendDirection,
        today_summary: dict[str, Any],
        triggered_by_document_id: str,
    ) -> bool:
        """Emit plantation.performance_updated event for Engagement Model.

        NOTE: No current_category field - Engagement Model owns WIN/WATCH/WORK
        vocabulary and computes category from primary_percentage + factory thresholds.
        """
        if self._event_publisher is None:
            logger.debug(
                "Event publisher not configured - skipping performance_updated event",
                farmer_id=farmer_id,
            )
            return False

        payload = {
            "event_type": "plantation.performance_updated",
            "farmer_id": farmer_id,
            "factory_id": factory_id,
            "primary_percentage": round(primary_percentage, 2),
            "improvement_trend": improvement_trend.value,
            "today": today_summary,
            "triggered_by_document_id": triggered_by_document_id,
            "timestamp": datetime.now(dt.UTC).isoformat(),
        }

        success = await self._event_publisher.publish_event(
            pubsub_name=settings.dapr_pubsub_name,
            topic="plantation.performance_updated",
            data=payload,
        )

        if success:
            logger.info(
                "Emitted plantation.performance_updated event",
                farmer_id=farmer_id,
                factory_id=factory_id,
                primary_percentage=primary_percentage,
            )
        return success
