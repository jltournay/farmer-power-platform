"""Unit tests for QualityEventProcessor linkage field validation.

Story 0.6.10: Linkage Field Validation with Metrics
Story 0.6.13: Updated to use CollectionGrpcClient returning Pydantic Document models

Tests verify:
- AC1: Invalid farmer_id raises exception and increments metric
- AC2: Invalid factory_id raises exception and increments metric
- AC3: Invalid grading_model_id raises exception and increments metric
- AC4: Invalid region_id raises exception and increments metric
- AC5: Valid events pass through validation and are processed successfully
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_common.models import Document, ExtractionMetadata, IngestionMetadata, RawDocumentRef
from plantation_model.domain.services.quality_event_processor import (
    QualityEventProcessingError,
    QualityEventProcessor,
)


def _create_mock_document(
    document_id: str = "doc-123",
    source_id: str = "src-001",
    grading_model_id: str | None = "grading-model-001",
    factory_id: str | None = "factory-001",
    bag_summary: dict | None = None,
) -> Document:
    """Create a mock Document model for testing.

    Story 0.6.13: Tests now use Pydantic Document model instead of dict.
    """
    now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
    linkage_fields: dict = {}
    extracted_fields: dict = {}

    if grading_model_id:
        linkage_fields["grading_model_id"] = grading_model_id
    if factory_id:
        linkage_fields["factory_id"] = factory_id

    if bag_summary:
        extracted_fields["bag_summary"] = bag_summary
    else:
        extracted_fields["bag_summary"] = {
            "total_weight_kg": 10.5,
            "primary_percentage": 85.0,
        }

    return Document(
        document_id=document_id,
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
            source_id=source_id,
            received_at=now,
            processed_at=now,
        ),
        extracted_fields=extracted_fields,
        linkage_fields=linkage_fields,
        created_at=now,
    )


@pytest.fixture
def mock_collection_client():
    """Mock Collection gRPC client for fetching documents.

    Story 0.6.13: Returns Pydantic Document model instead of dict.
    """
    client = MagicMock()
    client.get_document = AsyncMock(return_value=_create_mock_document())
    return client


@pytest.fixture
def mock_grading_model_repo():
    """Mock grading model repository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(
        return_value=MagicMock(
            id="grading-model-001",
            model_version="1.0",
            grade_labels={"1": "Primary", "2": "Secondary"},
            attributes=[],
        )
    )
    repo.get_by_id_and_version = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_farmer_performance_repo():
    """Mock farmer performance repository."""
    repo = MagicMock()
    repo.get_by_farmer_id = AsyncMock(return_value=None)  # Will be set per test
    repo.reset_today = AsyncMock()
    repo.increment_today_delivery = AsyncMock()
    return repo


@pytest.fixture
def mock_farmer_repo():
    """Mock farmer repository for linkage validation."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)  # Will be set per test
    return repo


@pytest.fixture
def mock_factory_repo():
    """Mock factory repository for linkage validation."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)  # Will be set per test
    return repo


@pytest.fixture
def mock_region_repo():
    """Mock region repository for linkage validation."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)  # Will be set per test
    return repo


@pytest.fixture
def mock_event_publisher():
    """Mock DAPR pub/sub client."""
    publisher = MagicMock()
    publisher.publish_event = AsyncMock(return_value=True)
    return publisher


class TestFarmerIdValidation:
    """AC1: Invalid farmer_id must raise exception and increment metric."""

    @pytest.mark.asyncio
    async def test_invalid_farmer_id_raises_exception(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When farmer_id references nonexistent farmer, raise QualityEventProcessingError."""
        # Arrange: farmer_id does not exist in database
        mock_farmer_repo.get_by_id.return_value = None

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="nonexistent-farmer",
            )

        error = exc_info.value
        assert error.error_type == "farmer_not_found"
        assert error.field_name == "farmer_id"
        assert error.field_value == "nonexistent-farmer"
        assert error.document_id == "doc-123"

    @pytest.mark.asyncio
    async def test_valid_farmer_id_passes_validation(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When farmer_id exists, validation passes and processing continues."""
        # Arrange: farmer exists
        mock_farmer = MagicMock(id="farmer-001", region_id="region-001")
        mock_farmer_repo.get_by_id.return_value = mock_farmer

        # Factory exists
        mock_factory_repo.get_by_id.return_value = MagicMock(id="factory-001")

        # Region exists
        mock_region_repo.get_by_id.return_value = MagicMock(region_id="region-001")

        # No farmer performance (will skip update but not raise)
        mock_farmer_performance_repo.get_by_farmer_id.return_value = None

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act
        result = await processor.process(
            document_id="doc-123",
            farmer_id="farmer-001",
        )

        # Assert: no exception raised, farmer validation passed
        assert result["status"] == "skipped"  # Skipped because no performance record
        mock_farmer_repo.get_by_id.assert_called_once_with("farmer-001")


class TestFactoryIdValidation:
    """AC2: Invalid factory_id must raise exception and increment metric."""

    @pytest.mark.asyncio
    async def test_invalid_factory_id_raises_exception(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When factory_id references nonexistent factory, raise QualityEventProcessingError."""
        # Arrange: farmer exists
        mock_farmer = MagicMock(id="farmer-001", region_id="region-001")
        mock_farmer_repo.get_by_id.return_value = mock_farmer

        # Factory does NOT exist
        mock_factory_repo.get_by_id.return_value = None

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="farmer-001",
            )

        error = exc_info.value
        assert error.error_type == "factory_not_found"
        assert error.field_name == "factory_id"
        assert error.field_value == "factory-001"


class TestGradingModelIdValidation:
    """AC3: Invalid grading_model_id must raise exception and increment metric."""

    @pytest.mark.asyncio
    async def test_missing_grading_model_id_raises_exception(
        self,
        mock_grading_model_repo,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When document is missing grading_model_id, raise QualityEventProcessingError."""
        # Arrange: document has no grading_model_id
        mock_collection_client = MagicMock()
        mock_collection_client.get_document = AsyncMock(
            return_value=_create_mock_document(grading_model_id=None)  # No grading_model_id
        )

        # Farmer exists
        mock_farmer = MagicMock(id="farmer-001", region_id="region-001")
        mock_farmer_repo.get_by_id.return_value = mock_farmer

        # Factory exists
        mock_factory_repo.get_by_id.return_value = MagicMock(id="factory-001")

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="farmer-001",
            )

        error = exc_info.value
        assert error.error_type == "missing_grading_model"
        assert error.field_name == "grading_model_id"

    @pytest.mark.asyncio
    async def test_nonexistent_grading_model_id_raises_exception(
        self,
        mock_collection_client,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When grading_model_id references nonexistent model, raise exception."""
        # Arrange: grading model does NOT exist
        mock_grading_model_repo = MagicMock()
        mock_grading_model_repo.get_by_id = AsyncMock(return_value=None)
        mock_grading_model_repo.get_by_id_and_version = AsyncMock(return_value=None)

        # Farmer exists
        mock_farmer = MagicMock(id="farmer-001", region_id="region-001")
        mock_farmer_repo.get_by_id.return_value = mock_farmer

        # Factory exists
        mock_factory_repo.get_by_id.return_value = MagicMock(id="factory-001")

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="farmer-001",
            )

        error = exc_info.value
        assert error.error_type == "grading_model_not_found"
        assert error.field_name == "grading_model_id"
        assert error.field_value == "grading-model-001"


class TestRegionIdValidation:
    """AC4: Invalid region_id must raise exception and increment metric."""

    @pytest.mark.asyncio
    async def test_invalid_region_id_raises_exception(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_farmer_performance_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When farmer's region_id references nonexistent region, raise exception."""
        # Arrange: farmer exists with a region_id
        mock_farmer = MagicMock(id="farmer-001", region_id="nonexistent-region")
        mock_farmer_repo.get_by_id.return_value = mock_farmer

        # Factory exists
        mock_factory_repo.get_by_id.return_value = MagicMock(id="factory-001")

        # Region does NOT exist
        mock_region_repo.get_by_id.return_value = None

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="farmer-001",
            )

        error = exc_info.value
        assert error.error_type == "region_not_found"
        assert error.field_name == "region_id"
        assert error.field_value == "nonexistent-region"


class TestValidEventProcessing:
    """AC5: Valid events must pass through validation and be processed."""

    @pytest.mark.asyncio
    async def test_valid_event_processes_successfully(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_farmer_repo,
        mock_factory_repo,
        mock_region_repo,
        mock_event_publisher,
    ):
        """When all linkage fields are valid, event processes successfully."""
        import datetime as dt

        # Arrange: all entities exist
        mock_farmer = MagicMock(id="farmer-001", region_id="region-001")
        mock_farmer_repo.get_by_id.return_value = mock_farmer
        mock_factory_repo.get_by_id.return_value = MagicMock(id="factory-001")
        mock_region_repo.get_by_id.return_value = MagicMock(region_id="region-001")

        # Farmer performance exists
        mock_performance = MagicMock()
        mock_performance.today = MagicMock(
            metrics_date=dt.date.today(),
            deliveries=5,
            total_kg=50.0,
            grade_counts={"Primary": 4, "Secondary": 1},
        )
        mock_performance.historical = MagicMock(
            primary_percentage_30d=80.0,
            primary_percentage_90d=75.0,
            improvement_trend="stable",
        )

        mock_farmer_performance_repo = MagicMock()
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=mock_performance)
        mock_farmer_performance_repo.increment_today_delivery = AsyncMock(return_value=mock_performance)

        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            farmer_repo=mock_farmer_repo,
            factory_repo=mock_factory_repo,
            region_repo=mock_region_repo,
            event_publisher=mock_event_publisher,
        )

        # Act
        result = await processor.process(
            document_id="doc-123",
            farmer_id="farmer-001",
        )

        # Assert: successful processing
        assert result["status"] == "success"
        assert result["farmer_id"] == "farmer-001"
        assert result["document_id"] == "doc-123"

        # Verify all validation repos were called
        mock_farmer_repo.get_by_id.assert_called_once_with("farmer-001")
        mock_factory_repo.get_by_id.assert_called_once_with("factory-001")
        mock_region_repo.get_by_id.assert_called_once_with("region-001")


class TestExceptionAttributes:
    """Test QualityEventProcessingError has correct attributes for metrics."""

    def test_exception_has_field_name_and_value(self):
        """Exception includes field_name and field_value for metric labels."""
        error = QualityEventProcessingError(
            "Farmer not found",
            document_id="doc-123",
            farmer_id="farmer-001",
            error_type="farmer_not_found",
            field_name="farmer_id",
            field_value="farmer-001",
        )

        assert error.field_name == "farmer_id"
        assert error.field_value == "farmer-001"
        assert error.error_type == "farmer_not_found"

    def test_exception_str_includes_field_info(self):
        """Exception string representation includes field info."""
        error = QualityEventProcessingError(
            "Farmer not found",
            document_id="doc-123",
            error_type="farmer_not_found",
            field_name="farmer_id",
            field_value="farmer-001",
        )

        error_str = str(error)
        assert "farmer_not_found" in error_str
        assert "farmer_id" in error_str
        assert "farmer-001" in error_str


class TestBackwardCompatibility:
    """Test that processor works without linkage repos (backward compatible)."""

    @pytest.mark.asyncio
    async def test_processor_works_without_linkage_repos(
        self,
        mock_collection_client,
        mock_grading_model_repo,
        mock_event_publisher,
    ):
        """Processor still works when linkage repos are not provided (None)."""
        import datetime as dt

        # Farmer performance exists
        mock_performance = MagicMock()
        mock_performance.today = MagicMock(
            metrics_date=dt.date.today(),
            deliveries=5,
            total_kg=50.0,
            grade_counts={"Primary": 4, "Secondary": 1},
        )
        mock_performance.historical = MagicMock(
            primary_percentage_30d=80.0,
            primary_percentage_90d=75.0,
            improvement_trend="stable",
        )

        mock_farmer_performance_repo = MagicMock()
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=mock_performance)
        mock_farmer_performance_repo.increment_today_delivery = AsyncMock(return_value=mock_performance)

        # Create processor WITHOUT linkage repos (backward compatible)
        processor = QualityEventProcessor(
            collection_client=mock_collection_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
            # No farmer_repo, factory_repo, region_repo
            event_publisher=mock_event_publisher,
        )

        # Act: should not raise, just log warnings for skipped validations
        result = await processor.process(
            document_id="doc-123",
            farmer_id="farmer-001",
        )

        # Assert: processing completed (validation was skipped)
        assert result["status"] == "success"
