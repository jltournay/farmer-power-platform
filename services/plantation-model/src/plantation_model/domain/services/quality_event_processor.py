"""Quality Event Processor - orchestrates quality result event processing.

Story 1.7: Quality Grading Event Subscription
Story 0.6.13: Migrated from direct MongoDB to gRPC via DAPR (ADR-010/011)

This service processes quality result events from Collection Model:
1. Fetches the full document from Collection Model via gRPC
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
from fp_common.models import Document
from opentelemetry import metrics, trace
from plantation_model.config import settings
from plantation_model.domain.models import TrendDirection
from plantation_model.events.publisher import publish_event
from plantation_model.infrastructure.collection_grpc_client import (
    CollectionClientError,
    CollectionGrpcClient,
    DocumentNotFoundError,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)
from plantation_model.infrastructure.repositories.region_repository import (
    RegionRepository,
)

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("plantation-model")

# Story 0.6.10: Counter for linkage field validation failures (ADR-008)
# Labels: field (farmer_id, factory_id, grading_model_id, region_id), error (not_found, missing)
linkage_validation_failures = meter.create_counter(
    name="event_linkage_validation_failures_total",
    description="Total events with invalid linkage fields that require DLQ handling",
    unit="1",
)

# Story 1.11 - Counter for farmer auto-assignments
# Status labels: success, already_assigned, cp_not_found, skipped_no_repo, error
farmer_auto_assignments = meter.create_counter(
    name="farmer_auto_assignments_total",
    description="Total farmer auto-assignments to collection points on quality events",
    unit="1",
)


class QualityEventProcessingError(Exception):
    """Raised when quality event processing fails.

    Story 0.6.10: Enhanced with field_name and field_value for linkage validation errors.
    This enables precise error reporting and metric labeling per ADR-008.

    Attributes:
        document_id: The Collection Model document ID being processed.
        farmer_id: The farmer ID from the event (if known).
        error_type: Classification of the error (e.g., "farmer_not_found", "missing_grading_model").
        field_name: The specific linkage field that failed validation (e.g., "farmer_id").
        field_value: The invalid value that caused the error.
        cause: The underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        farmer_id: str | None = None,
        error_type: str = "processing_error",
        field_name: str | None = None,
        field_value: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.document_id = document_id
        self.farmer_id = farmer_id
        self.error_type = error_type
        self.field_name = field_name
        self.field_value = field_value
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        """Return a descriptive string representation."""
        parts = [f"{self.error_type}: {self.args[0]}"]
        if self.document_id:
            parts.append(f"document_id={self.document_id}")
        if self.field_name:
            parts.append(f"field={self.field_name}")
        if self.field_value:
            parts.append(f"value={self.field_value}")
        return " | ".join(parts)


class QualityEventProcessor:
    """Processes quality result events and updates farmer performance.

    This is the main orchestrator for Story 1.7, implementing the event
    processing pipeline that connects Collection Model events to
    FarmerPerformance updates and downstream notifications.

    Key Design Principles:
    - Model-Driven: Grade labels come from GradingModel, not hardcoded
    - Atomic Updates: Uses MongoDB $inc for thread-safe counter updates
    - Event Sourcing: Emits events for downstream consumers (Engagement Model)

    Story 0.6.13: Uses gRPC via DAPR instead of direct MongoDB access.
    """

    def __init__(
        self,
        collection_client: CollectionGrpcClient,
        grading_model_repo: GradingModelRepository,
        farmer_performance_repo: FarmerPerformanceRepository,
        farmer_repo: FarmerRepository | None = None,
        factory_repo: FactoryRepository | None = None,
        region_repo: RegionRepository | None = None,
        cp_repo: CollectionPointRepository | None = None,
    ) -> None:
        """Initialize the processor with required dependencies.

        Args:
            collection_client: gRPC client for fetching documents from Collection Model.
            grading_model_repo: Repository for loading grading models.
            farmer_performance_repo: Repository for updating farmer performance.
            farmer_repo: Repository for farmer validation (Story 0.6.10).
            factory_repo: Repository for factory validation (Story 0.6.10).
            region_repo: Repository for region validation (Story 0.6.10).
            cp_repo: Repository for collection point operations (Story 1.11).

        Note:
            Story 0.6.14: DAPR publishing now uses module-level publish_event() function
            from events.publisher per ADR-010.
        """
        self._collection_client = collection_client
        self._grading_model_repo = grading_model_repo
        self._farmer_performance_repo = farmer_performance_repo
        self._farmer_repo = farmer_repo
        self._factory_repo = factory_repo
        self._region_repo = region_repo
        self._cp_repo = cp_repo

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

                # =====================================================================
                # Story 0.6.10: Linkage Field Validation (ADR-008)
                # ALL 4 linkage fields must be validated with exceptions, not warnings.
                # =====================================================================

                # Step 2: Validate farmer_id (AC1)
                farmer = await self._validate_farmer_id(document_id, farmer_id)

                # Step 2b: Auto-assign farmer to collection point (Story 1.11)
                cp_id = self._get_collection_point_id(document)
                if cp_id:
                    await self._ensure_farmer_assigned_to_cp(farmer_id, cp_id)

                # Step 3: Validate factory_id (AC2)
                factory_id = self._get_factory_id(document)
                if factory_id and factory_id != "unknown":
                    await self._validate_factory_id(document_id, farmer_id, factory_id)

                # Step 4: Validate grading_model_id (AC3)
                grading_model_id = self._get_grading_model_id(document)
                grading_model_version = self._get_grading_model_version(document)

                if not grading_model_id:
                    linkage_validation_failures.add(1, {"field": "grading_model_id", "error": "missing"})
                    raise QualityEventProcessingError(
                        "Document missing grading_model_id",
                        document_id=document_id,
                        farmer_id=farmer_id,
                        error_type="missing_grading_model",
                        field_name="grading_model_id",
                    )

                # Step 5: Load grading model and validate it exists
                grading_model = await self._load_grading_model(grading_model_id, grading_model_version)

                if grading_model is None:
                    linkage_validation_failures.add(1, {"field": "grading_model_id", "error": "not_found"})
                    raise QualityEventProcessingError(
                        f"Grading model not found: {grading_model_id}@{grading_model_version}",
                        document_id=document_id,
                        farmer_id=farmer_id,
                        error_type="grading_model_not_found",
                        field_name="grading_model_id",
                        field_value=grading_model_id,
                    )

                # Step 6: Validate region_id (AC4) - via farmer's region reference
                if farmer and farmer.region_id:
                    await self._validate_region_id(document_id, farmer_id, farmer.region_id)

                # Step 7: Extract quality metrics from document
                bag_summary = self._get_bag_summary(document)
                grade_counts = self._extract_grade_counts(bag_summary, grading_model)
                attribute_distribution = self._extract_attribute_distribution(bag_summary, grading_model)
                total_weight_kg = self._get_total_weight(bag_summary)

                span.set_attribute("grade_counts", str(grade_counts))
                span.set_attribute("total_weight_kg", total_weight_kg)

                # Step 8: Check for date rollover and update farmer performance
                performance = await self._update_farmer_performance(
                    farmer_id=farmer_id,
                    grade_counts=grade_counts,
                    attribute_counts=attribute_distribution,
                    weight_kg=total_weight_kg,
                )

                # Note: performance can be None if FarmerPerformance record doesn't exist yet
                # (farmer exists but no deliveries recorded). This is allowed - we skip the update.
                if performance is None:
                    logger.warning(
                        "FarmerPerformance record not found - farmer exists but has no delivery history",
                        farmer_id=farmer_id,
                        document_id=document_id,
                    )
                    return {
                        "status": "skipped",
                        "reason": "no_performance_record",
                        "document_id": document_id,
                        "farmer_id": farmer_id,
                    }

                # Step 9: Emit plantation.quality.graded event
                await self._emit_quality_graded_event(
                    farmer_id=farmer_id,
                    document_id=document_id,
                    grading_model_id=grading_model_id,
                    grading_model_version=grading_model_version or "unknown",
                    grade_counts=grade_counts,
                    attribute_distribution=attribute_distribution,
                )

                # Step 10: Compute performance summary and emit update event
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

    async def _fetch_document(self, document_id: str) -> Document:
        """Fetch quality document from Collection Model via gRPC.

        Story 0.6.13: Uses gRPC client instead of direct MongoDB access.
        """
        with tracer.start_as_current_span("fetch_document"):
            document = await self._collection_client.get_document(document_id)
            logger.debug(
                "Fetched document from Collection Model via gRPC",
                document_id=document_id,
                source_id=document.ingestion.source_id,
            )
            return document

    # =========================================================================
    # Story 0.6.10: Linkage Field Validation Methods (ADR-008)
    # =========================================================================

    async def _validate_farmer_id(self, document_id: str, farmer_id: str):
        """Validate that farmer_id references an existing farmer.

        AC1: Invalid farmer_id must raise exception and increment metric.

        Args:
            document_id: The document being processed.
            farmer_id: The farmer ID to validate.

        Returns:
            The Farmer entity if found.

        Raises:
            QualityEventProcessingError: If farmer not found.
        """
        if self._farmer_repo is None:
            logger.warning(
                "Farmer repository not configured - skipping farmer validation",
                farmer_id=farmer_id,
            )
            return None

        with tracer.start_as_current_span("validate_farmer_id"):
            farmer = await self._farmer_repo.get_by_id(farmer_id)

            if farmer is None:
                linkage_validation_failures.add(1, {"field": "farmer_id", "error": "not_found"})
                raise QualityEventProcessingError(
                    f"Farmer not found: {farmer_id}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="farmer_not_found",
                    field_name="farmer_id",
                    field_value=farmer_id,
                )

            logger.debug("Farmer validated", farmer_id=farmer_id)
            return farmer

    async def _validate_factory_id(self, document_id: str, farmer_id: str, factory_id: str) -> None:
        """Validate that factory_id references an existing factory.

        AC2: Invalid factory_id must raise exception and increment metric.

        Args:
            document_id: The document being processed.
            farmer_id: The farmer ID (for error context).
            factory_id: The factory ID to validate.

        Raises:
            QualityEventProcessingError: If factory not found.
        """
        if self._factory_repo is None:
            logger.warning(
                "Factory repository not configured - skipping factory validation",
                factory_id=factory_id,
            )
            return

        with tracer.start_as_current_span("validate_factory_id"):
            factory = await self._factory_repo.get_by_id(factory_id)

            if factory is None:
                linkage_validation_failures.add(1, {"field": "factory_id", "error": "not_found"})
                raise QualityEventProcessingError(
                    f"Factory not found: {factory_id}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="factory_not_found",
                    field_name="factory_id",
                    field_value=factory_id,
                )

            logger.debug("Factory validated", factory_id=factory_id)

    async def _validate_region_id(self, document_id: str, farmer_id: str, region_id: str) -> None:
        """Validate that region_id references an existing region.

        AC4: Invalid region_id (via farmer) must raise exception and increment metric.

        Args:
            document_id: The document being processed.
            farmer_id: The farmer ID (for error context).
            region_id: The region ID to validate.

        Raises:
            QualityEventProcessingError: If region not found.
        """
        if self._region_repo is None:
            logger.warning(
                "Region repository not configured - skipping region validation",
                region_id=region_id,
            )
            return

        with tracer.start_as_current_span("validate_region_id"):
            region = await self._region_repo.get_by_id(region_id)

            if region is None:
                linkage_validation_failures.add(1, {"field": "region_id", "error": "not_found"})
                raise QualityEventProcessingError(
                    f"Region not found: {region_id}",
                    document_id=document_id,
                    farmer_id=farmer_id,
                    error_type="region_not_found",
                    field_name="region_id",
                    field_value=region_id,
                )

            logger.debug("Region validated", region_id=region_id)

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

    def _get_grading_model_id(self, document: Document) -> str | None:
        """Extract grading model ID from document.

        Story 0.6.13: Updated to work with Pydantic Document model.
        """
        # Check extracted_fields first (where DocumentIndex stores it)
        if "grading_model_id" in document.extracted_fields:
            return str(document.extracted_fields["grading_model_id"])
        # Check linkage_fields (also populated by DocumentIndex)
        if "grading_model_id" in document.linkage_fields:
            return str(document.linkage_fields["grading_model_id"])
        return None

    def _get_grading_model_version(self, document: Document) -> str | None:
        """Extract grading model version from document.

        Story 0.6.13: Updated to work with Pydantic Document model.
        """
        # Check extracted_fields first (where DocumentIndex stores it)
        if "grading_model_version" in document.extracted_fields:
            return str(document.extracted_fields["grading_model_version"])
        return None

    def _get_factory_id(self, document: Document) -> str:
        """Extract factory ID from document.

        Story 0.6.13: Updated to work with Pydantic Document model.
        """
        # Check extracted_fields first (where DocumentIndex stores it)
        if "factory_id" in document.extracted_fields:
            return str(document.extracted_fields["factory_id"])
        # Check linkage_fields (also populated by DocumentIndex)
        if "factory_id" in document.linkage_fields:
            return str(document.linkage_fields["factory_id"])
        return "unknown"

    def _get_collection_point_id(self, document: Document) -> str | None:
        """Extract collection point ID from document.

        Story 1.11: Get CP ID for auto-assignment.

        Args:
            document: The quality document.

        Returns:
            Collection point ID or None if not present.
        """
        # Check extracted_fields first
        if "collection_point_id" in document.extracted_fields:
            return str(document.extracted_fields["collection_point_id"])
        # Check linkage_fields
        if "collection_point_id" in document.linkage_fields:
            return str(document.linkage_fields["collection_point_id"])
        return None

    async def _ensure_farmer_assigned_to_cp(self, farmer_id: str, cp_id: str) -> bool:
        """Auto-assign farmer to collection point if not already assigned (idempotent).

        Story 1.11: Automatically associates a farmer with the collection point
        when their first quality result is received at that CP. Uses $addToSet
        for idempotency - calling this multiple times for the same farmer/CP
        combination has no effect after the first assignment.

        Args:
            farmer_id: The farmer identifier.
            cp_id: The collection point identifier.

        Returns:
            True if farmer was newly assigned, False if already assigned or CP not found.
        """
        if self._cp_repo is None:
            logger.debug(
                "Collection point repository not configured - skipping auto-assignment",
                farmer_id=farmer_id,
                cp_id=cp_id,
            )
            farmer_auto_assignments.add(1, {"status": "skipped_no_repo"})
            return False

        with tracer.start_as_current_span("ensure_farmer_assigned_to_cp") as span:
            span.set_attribute("farmer_id", farmer_id)
            span.set_attribute("cp_id", cp_id)

            import time

            start_time = time.time()

            try:
                # First check if farmer is already assigned (optimization to avoid write if not needed)
                cps, _, _ = await self._cp_repo.list_by_farmer(farmer_id, page_size=100)
                already_assigned = any(cp.id == cp_id for cp in cps)

                if already_assigned:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.debug(
                        "Farmer already assigned to collection point",
                        farmer_id=farmer_id,
                        cp_id=cp_id,
                        duration_ms=round(duration_ms, 2),
                    )
                    span.set_attribute("assignment.status", "already_assigned")
                    farmer_auto_assignments.add(1, {"status": "already_assigned"})
                    return False

                # Add farmer to CP (idempotent via $addToSet)
                updated_cp = await self._cp_repo.add_farmer(cp_id, farmer_id)
                duration_ms = (time.time() - start_time) * 1000

                if updated_cp is None:
                    logger.warning(
                        "Collection point not found for auto-assignment",
                        farmer_id=farmer_id,
                        cp_id=cp_id,
                        duration_ms=round(duration_ms, 2),
                    )
                    span.set_attribute("assignment.status", "cp_not_found")
                    farmer_auto_assignments.add(1, {"status": "cp_not_found"})
                    return False

                logger.info(
                    "Farmer auto-assigned to collection point",
                    farmer_id=farmer_id,
                    cp_id=cp_id,
                    cp_name=updated_cp.name,
                    factory_id=updated_cp.factory_id,
                    duration_ms=round(duration_ms, 2),
                )
                span.set_attribute("assignment.status", "success")
                span.set_attribute("assignment.cp_name", updated_cp.name)
                farmer_auto_assignments.add(1, {"status": "success"})
                return True

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    "Failed to auto-assign farmer to collection point",
                    farmer_id=farmer_id,
                    cp_id=cp_id,
                    error=str(e),
                    duration_ms=round(duration_ms, 2),
                )
                span.set_attribute("assignment.status", "error")
                span.set_attribute("assignment.error", str(e))
                farmer_auto_assignments.add(1, {"status": "error"})
                # Don't raise - auto-assignment failure should not fail the event processing
                return False

    def _get_bag_summary(self, document: Document) -> dict[str, Any]:
        """Extract bag summary from document.

        Story 0.6.13: Updated to work with Pydantic Document model.
        Handles stringified dicts from proto map<string, string>.
        """
        import ast

        # Maximum size for bag_summary string to prevent DoS via oversized payloads
        MAX_BAG_SUMMARY_SIZE = 10_000  # 10KB should be plenty for QC data

        # Check extracted_fields (where DocumentIndex stores it)
        if "bag_summary" in document.extracted_fields:
            bag_summary = document.extracted_fields["bag_summary"]
            if isinstance(bag_summary, dict):
                return bag_summary
            if isinstance(bag_summary, str):
                # Defense-in-depth: check size before parsing
                if len(bag_summary) > MAX_BAG_SUMMARY_SIZE:
                    logger.warning(
                        "bag_summary string too large, skipping parse",
                        size=len(bag_summary),
                        max_size=MAX_BAG_SUMMARY_SIZE,
                        document_id=document.document_id,
                    )
                    return {}
                # Proto map<string, string> converts nested dicts to strings
                # e.g., "{'grade_counts': {'Primary': 5}}" needs parsing
                try:
                    parsed = ast.literal_eval(bag_summary)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, SyntaxError):
                    logger.warning(
                        "Failed to parse bag_summary string",
                        bag_summary=bag_summary[:100] if len(bag_summary) > 100 else bag_summary,
                    )
            return {}
        return {}

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
        """Emit plantation.quality.graded event via DAPR pub/sub.

        Story 0.6.14: Uses module-level publish_event() per ADR-010.
        """
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

        success = await publish_event(
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

        Story 0.6.14: Uses module-level publish_event() per ADR-010.
        """
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

        success = await publish_event(
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
