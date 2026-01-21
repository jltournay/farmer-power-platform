"""Unit tests for QualityEventProcessor farmer auto-assignment.

Story 1.11: Auto-Assignment of Farmer to Collection Point on Quality Result

Tests cover:
- AC 1.11.1: Auto-assignment when farmer not in CP's farmer_ids
- AC 1.11.2: Idempotent assignment (no duplicates)
- AC 1.11.3: Cross-factory assignment (N:M relationship)
- AC 1.11.4: Logging and metrics
"""

import datetime as dt
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fp_common.models import (
    CollectionPoint,
    Document,
    ExtractionMetadata,
    GeoLocation,
    IngestionMetadata,
    RawDocumentRef,
)
from plantation_model.domain.models import (
    FarmerPerformance,
    FarmScale,
    GradeRules,
    GradingModel,
    GradingType,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from plantation_model.domain.services.quality_event_processor import (
    QualityEventProcessor,
)


@pytest.fixture
def mock_collection_client() -> AsyncMock:
    """Create a mock Collection client."""
    return AsyncMock()


@pytest.fixture
def mock_grading_model_repo() -> AsyncMock:
    """Create a mock GradingModelRepository."""
    return AsyncMock()


@pytest.fixture
def mock_farmer_performance_repo() -> AsyncMock:
    """Create a mock FarmerPerformanceRepository."""
    return AsyncMock()


@pytest.fixture
def mock_cp_repo() -> AsyncMock:
    """Create a mock CollectionPointRepository."""
    return AsyncMock()


@pytest.fixture
def processor_with_cp_repo(
    mock_collection_client: AsyncMock,
    mock_grading_model_repo: AsyncMock,
    mock_farmer_performance_repo: AsyncMock,
    mock_cp_repo: AsyncMock,
) -> QualityEventProcessor:
    """Create a QualityEventProcessor with CP repo for auto-assignment tests."""
    return QualityEventProcessor(
        collection_client=mock_collection_client,
        grading_model_repo=mock_grading_model_repo,
        farmer_performance_repo=mock_farmer_performance_repo,
        cp_repo=mock_cp_repo,
    )


@pytest.fixture
def processor_without_cp_repo(
    mock_collection_client: AsyncMock,
    mock_grading_model_repo: AsyncMock,
    mock_farmer_performance_repo: AsyncMock,
) -> QualityEventProcessor:
    """Create a QualityEventProcessor without CP repo."""
    return QualityEventProcessor(
        collection_client=mock_collection_client,
        grading_model_repo=mock_grading_model_repo,
        farmer_performance_repo=mock_farmer_performance_repo,
    )


@pytest.fixture
def sample_grading_model() -> GradingModel:
    """Create a sample grading model for testing."""
    return GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="1.0.0",
        regulatory_authority="Tea Board of Kenya",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={},
        grade_rules=GradeRules(),
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        active_at_factory=["factory-001"],
    )


@pytest.fixture
def sample_farmer_performance() -> FarmerPerformance:
    """Create a sample farmer performance for testing."""
    return FarmerPerformance(
        farmer_id="WM-0001",
        grading_model_id="tbk_kenya_tea_v1",
        grading_model_version="1.0.0",
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        historical=HistoricalMetrics(
            primary_percentage_30d=75.0,
            primary_percentage_90d=70.0,
            improvement_trend=TrendDirection.IMPROVING,
        ),
        today=TodayMetrics(
            deliveries=2,
            total_kg=45.0,
            grade_counts={"Primary": 2},
            metrics_date=dt.date.today(),
        ),
    )


@pytest.fixture
def sample_collection_point() -> CollectionPoint:
    """Create a sample collection point for testing."""
    return CollectionPoint(
        id="cp-001",
        name="Wamumu CP 1",
        factory_id="factory-001",
        location=GeoLocation(latitude=-0.4150, longitude=36.9500, altitude_meters=1850.0),
        region_id="region-001",
        clerk_id="clerk-001",
        status="active",
        farmer_ids=["WM-0002", "WM-0003"],  # Note: WM-0001 NOT included
    )


@pytest.fixture
def sample_document_with_cp() -> Document:
    """Create a sample quality document with collection_point_id."""
    now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
    return Document(
        document_id="doc-123",
        raw_document=RawDocumentRef(
            blob_container="quality-data",
            blob_path="factory/batch.json",
            content_hash="sha256:test",
            size_bytes=1024,
            stored_at=now,
        ),
        extraction=ExtractionMetadata(
            ai_agent_id="extractor-v1",
            extraction_timestamp=now,
            confidence=0.95,
            validation_passed=True,
            validation_warnings=[],
        ),
        ingestion=IngestionMetadata(
            ingestion_id="ing-001",
            source_id="qc-analyzer-result",
            received_at=now,
            processed_at=now,
        ),
        extracted_fields={
            "grading_model_id": "tbk_kenya_tea_v1",
            "grading_model_version": "1.0.0",
            "factory_id": "factory-001",
            "collection_point_id": "cp-001",
            "bag_summary": {
                "total_weight_kg": 25.0,
                "primary_percentage": 80.0,
            },
        },
        linkage_fields={
            "farmer_id": "WM-0001",
            "factory_id": "factory-001",
            "collection_point_id": "cp-001",
        },
        created_at=now,
    )


@pytest.fixture
def sample_document_without_cp() -> Document:
    """Create a sample quality document without collection_point_id."""
    now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
    return Document(
        document_id="doc-456",
        raw_document=RawDocumentRef(
            blob_container="quality-data",
            blob_path="factory/batch.json",
            content_hash="sha256:test",
            size_bytes=1024,
            stored_at=now,
        ),
        extraction=ExtractionMetadata(
            ai_agent_id="extractor-v1",
            extraction_timestamp=now,
            confidence=0.95,
            validation_passed=True,
            validation_warnings=[],
        ),
        ingestion=IngestionMetadata(
            ingestion_id="ing-001",
            source_id="qc-analyzer-result",
            received_at=now,
            processed_at=now,
        ),
        extracted_fields={
            "grading_model_id": "tbk_kenya_tea_v1",
            "grading_model_version": "1.0.0",
            "factory_id": "factory-001",
            "bag_summary": {
                "total_weight_kg": 25.0,
                "primary_percentage": 80.0,
            },
        },
        linkage_fields={
            "farmer_id": "WM-0001",
            "factory_id": "factory-001",
        },
        created_at=now,
    )


class TestAutoAssignment:
    """Tests for AC 1.11.1: Auto-assignment on quality result."""

    @pytest.mark.asyncio
    async def test_auto_assigns_farmer_to_cp_when_not_already_assigned(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_document_with_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
        sample_collection_point: CollectionPoint,
    ) -> None:
        """Test farmer is auto-assigned to CP when receiving first quality result."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_with_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # CP repo returns empty list (farmer not assigned) then updated CP
        mock_cp_repo.list_by_farmer.return_value = ([], None, 0)
        updated_cp = sample_collection_point.model_copy()
        updated_cp.farmer_ids = ["WM-0002", "WM-0003", "WM-0001"]
        mock_cp_repo.add_farmer.return_value = updated_cp

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        # Assert
        assert result["status"] == "success"
        mock_cp_repo.add_farmer.assert_called_once_with("cp-001", "WM-0001")

    @pytest.mark.asyncio
    async def test_no_auto_assignment_when_cp_repo_not_configured(
        self,
        processor_without_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        sample_document_with_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test processing succeeds without auto-assignment when cp_repo is None."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_with_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_without_cp_repo.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        # Assert - processing succeeds, just no auto-assignment
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_no_auto_assignment_when_document_lacks_cp_id(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_document_without_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test no auto-assignment when document doesn't have collection_point_id."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_without_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-456",
                farmer_id="WM-0001",
            )

        # Assert - processing succeeds, no add_farmer called
        assert result["status"] == "success"
        mock_cp_repo.add_farmer.assert_not_called()


class TestIdempotentAssignment:
    """Tests for AC 1.11.2: Idempotent assignment (no duplicates)."""

    @pytest.mark.asyncio
    async def test_no_duplicate_assignment_when_already_assigned(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_document_with_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
        sample_collection_point: CollectionPoint,
    ) -> None:
        """Test no duplicate assignment when farmer already in CP's farmer_ids."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_with_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # CP repo returns the CP in list_by_farmer (already assigned)
        mock_cp_repo.list_by_farmer.return_value = ([sample_collection_point], None, 1)

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        # Assert - add_farmer NOT called since farmer already assigned
        assert result["status"] == "success"
        mock_cp_repo.add_farmer.assert_not_called()


class TestCrossFactoryAssignment:
    """Tests for AC 1.11.3: Cross-factory assignment (N:M relationship)."""

    @pytest.mark.asyncio
    async def test_assigns_farmer_to_second_cp_at_different_factory(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test farmer can be assigned to CP at second factory (N:M relationship)."""
        # Arrange - document from CP-B at Factory 2
        now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
        document_factory_2 = Document(
            document_id="doc-789",
            raw_document=RawDocumentRef(
                blob_container="quality-data",
                blob_path="factory/batch.json",
                content_hash="sha256:test",
                size_bytes=1024,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="extractor-v1",
                extraction_timestamp=now,
                confidence=0.95,
                validation_passed=True,
                validation_warnings=[],
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-001",
                source_id="qc-analyzer-result",
                received_at=now,
                processed_at=now,
            ),
            extracted_fields={
                "grading_model_id": "tbk_kenya_tea_v1",
                "grading_model_version": "1.0.0",
                "factory_id": "factory-002",  # Different factory!
                "collection_point_id": "cp-002",  # Different CP!
                "bag_summary": {
                    "total_weight_kg": 25.0,
                    "primary_percentage": 80.0,
                },
            },
            linkage_fields={
                "farmer_id": "WM-0001",
                "factory_id": "factory-002",
                "collection_point_id": "cp-002",
            },
            created_at=now,
        )

        # Farmer is already at cp-001 (Factory 1)
        cp_factory_1 = CollectionPoint(
            id="cp-001",
            name="Wamumu CP 1",
            factory_id="factory-001",
            location=GeoLocation(latitude=-0.4150, longitude=36.9500, altitude_meters=1850.0),
            region_id="region-001",
            clerk_id="clerk-001",
            status="active",
            farmer_ids=["WM-0001"],  # Already assigned to Factory 1's CP
        )

        # CP at Factory 2
        cp_factory_2 = CollectionPoint(
            id="cp-002",
            name="Nanyuki CP 1",
            factory_id="factory-002",
            location=GeoLocation(latitude=-0.0200, longitude=37.0700, altitude_meters=1900.0),
            region_id="region-002",
            clerk_id="clerk-002",
            status="active",
            farmer_ids=["WM-0005"],  # WM-0001 NOT here yet
        )

        mock_collection_client.get_document.return_value = document_factory_2
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Farmer already assigned to cp-001, but NOT to cp-002
        mock_cp_repo.list_by_farmer.return_value = ([cp_factory_1], None, 1)

        # After assignment
        updated_cp_2 = cp_factory_2.model_copy()
        updated_cp_2.farmer_ids = ["WM-0005", "WM-0001"]
        mock_cp_repo.add_farmer.return_value = updated_cp_2

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-789",
                farmer_id="WM-0001",
            )

        # Assert - farmer assigned to second CP at different factory
        assert result["status"] == "success"
        mock_cp_repo.add_farmer.assert_called_once_with("cp-002", "WM-0001")


class TestErrorHandling:
    """Tests for error scenarios that should not fail event processing."""

    @pytest.mark.asyncio
    async def test_processing_succeeds_when_cp_not_found(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_document_with_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test event processing succeeds even if CP is not found (soft failure)."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_with_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # CP repo can't find the farmer (not assigned yet)
        mock_cp_repo.list_by_farmer.return_value = ([], None, 0)
        # But add_farmer returns None (CP doesn't exist)
        mock_cp_repo.add_farmer.return_value = None

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        # Assert - processing should still succeed (auto-assignment is best-effort)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_processing_succeeds_when_cp_repo_raises_error(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_cp_repo: AsyncMock,
        sample_document_with_cp: Document,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test event processing succeeds even if CP repo throws exception."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document_with_cp
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # CP repo throws an error
        mock_cp_repo.list_by_farmer.side_effect = Exception("Database connection error")

        # Act
        with patch(
            "plantation_model.domain.services.quality_event_processor.publish_event",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await processor_with_cp_repo.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        # Assert - processing should still succeed (auto-assignment is best-effort)
        assert result["status"] == "success"


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_collection_point_id_from_extracted_fields(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        sample_document_with_cp: Document,
    ) -> None:
        """Test extraction of CP ID from extracted_fields."""
        result = processor_with_cp_repo._get_collection_point_id(sample_document_with_cp)
        assert result == "cp-001"

    def test_get_collection_point_id_from_linkage_fields(
        self,
        processor_with_cp_repo: QualityEventProcessor,
    ) -> None:
        """Test extraction of CP ID from linkage_fields when not in extracted_fields."""
        now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
        doc = Document(
            document_id="doc-test",
            raw_document=RawDocumentRef(
                blob_container="quality-data",
                blob_path="factory/batch.json",
                content_hash="sha256:test",
                size_bytes=1024,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="extractor-v1",
                extraction_timestamp=now,
                confidence=0.95,
                validation_passed=True,
                validation_warnings=[],
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-001",
                source_id="qc-analyzer-result",
                received_at=now,
                processed_at=now,
            ),
            extracted_fields={},  # No CP ID here
            linkage_fields={"collection_point_id": "cp-from-linkage"},  # CP ID here
            created_at=now,
        )

        result = processor_with_cp_repo._get_collection_point_id(doc)
        assert result == "cp-from-linkage"

    def test_get_collection_point_id_returns_none_when_missing(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        sample_document_without_cp: Document,
    ) -> None:
        """Test returns None when document lacks CP ID."""
        result = processor_with_cp_repo._get_collection_point_id(sample_document_without_cp)
        assert result is None

    @pytest.mark.asyncio
    async def test_ensure_farmer_assigned_to_cp_returns_true_on_new_assignment(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_cp_repo: AsyncMock,
        sample_collection_point: CollectionPoint,
    ) -> None:
        """Test _ensure_farmer_assigned_to_cp returns True when newly assigned."""
        # Farmer not yet assigned
        mock_cp_repo.list_by_farmer.return_value = ([], None, 0)
        # Assignment succeeds
        mock_cp_repo.add_farmer.return_value = sample_collection_point

        result = await processor_with_cp_repo._ensure_farmer_assigned_to_cp("WM-0001", "cp-001")

        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_farmer_assigned_to_cp_returns_false_when_already_assigned(
        self,
        processor_with_cp_repo: QualityEventProcessor,
        mock_cp_repo: AsyncMock,
        sample_collection_point: CollectionPoint,
    ) -> None:
        """Test _ensure_farmer_assigned_to_cp returns False when already assigned."""
        # Add farmer to the CP fixture so it appears assigned
        cp_with_farmer = sample_collection_point.model_copy()
        cp_with_farmer.farmer_ids = ["WM-0001"]

        # Farmer already assigned to this CP
        mock_cp_repo.list_by_farmer.return_value = ([cp_with_farmer], None, 1)

        result = await processor_with_cp_repo._ensure_farmer_assigned_to_cp("WM-0001", "cp-001")

        assert result is False
        mock_cp_repo.add_farmer.assert_not_called()
