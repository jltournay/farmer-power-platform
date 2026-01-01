"""Unit tests for QualityEventProcessor.

Story 1.7: Quality Grading Event Subscription
"""

import datetime as dt
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from plantation_model.domain.models.farmer import FarmScale
from plantation_model.domain.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from plantation_model.domain.models.grading_model import (
    GradeRules,
    GradingModel,
    GradingType,
)
from plantation_model.domain.services.quality_event_processor import (
    QualityEventProcessingError,
    QualityEventProcessor,
)
from plantation_model.infrastructure.collection_client import (
    DocumentNotFoundError,
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
def mock_event_publisher() -> AsyncMock:
    """Create a mock DAPR event publisher."""
    mock = AsyncMock()
    mock.publish_event = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def processor(
    mock_collection_client: AsyncMock,
    mock_grading_model_repo: AsyncMock,
    mock_farmer_performance_repo: AsyncMock,
    mock_event_publisher: AsyncMock,
) -> QualityEventProcessor:
    """Create a QualityEventProcessor with mocked dependencies."""
    return QualityEventProcessor(
        collection_client=mock_collection_client,
        grading_model_repo=mock_grading_model_repo,
        farmer_performance_repo=mock_farmer_performance_repo,
        event_publisher=mock_event_publisher,
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
def sample_document() -> dict:
    """Create a sample quality document for testing.

    NOTE: Document structure matches DocumentIndex model from collection_model.
    Fields are stored in 'extracted_fields' (not 'attributes').
    """
    return {
        "document_id": "doc-123",
        "source_id": "qc-analyzer-result",
        "farmer_id": "WM-0001",
        "extracted_fields": {
            "grading_model_id": "tbk_kenya_tea_v1",
            "grading_model_version": "1.0.0",
            "factory_id": "factory-001",
            "bag_summary": {
                "total_weight_kg": 25.0,
                "primary_percentage": 80.0,
                "secondary_percentage": 20.0,
                "overall_grade": "A",
                "leaf_type_distribution": {
                    "bud": 5,
                    "two_leaves_bud": 15,
                    "coarse_leaf": 3,
                },
            },
        },
        "linkage_fields": {
            "farmer_id": "WM-0001",
            "factory_id": "factory-001",
            "grading_model_id": "tbk_kenya_tea_v1",
        },
    }


class TestQualityEventProcessor:
    """Tests for QualityEventProcessor."""

    @pytest.mark.asyncio
    async def test_process_success(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        sample_document: dict,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test successful processing of a quality event."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        result = await processor.process(
            document_id="doc-123",
            farmer_id="WM-0001",
            batch_timestamp=datetime.now(dt.UTC),
        )

        # Assert
        assert result["status"] == "success"
        assert result["farmer_id"] == "WM-0001"
        assert result["document_id"] == "doc-123"
        assert "grade_counts" in result
        mock_collection_client.get_document.assert_called_once_with("doc-123")
        mock_grading_model_repo.get_by_id_and_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_document_not_found(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
    ) -> None:
        """Test error handling when document is not found."""
        # Arrange
        mock_collection_client.get_document.side_effect = DocumentNotFoundError("doc-123")

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        assert exc_info.value.error_type == "document_not_found"
        assert exc_info.value.document_id == "doc-123"

    @pytest.mark.asyncio
    async def test_process_grading_model_not_found(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        sample_document: dict,
    ) -> None:
        """Test error handling when grading model is not found."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = None

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        assert exc_info.value.error_type == "grading_model_not_found"

    @pytest.mark.asyncio
    async def test_process_farmer_not_found_skips_update(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        sample_document: dict,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test that processing continues (but skips update) when farmer not found."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = None

        # Act
        result = await processor.process(
            document_id="doc-123",
            farmer_id="WM-0001",
        )

        # Assert
        assert result["status"] == "skipped"
        assert result["reason"] == "farmer_not_found"

    @pytest.mark.asyncio
    async def test_process_missing_grading_model_id(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
    ) -> None:
        """Test error when document lacks grading_model_id."""
        # Arrange - document without grading_model_id
        mock_collection_client.get_document.return_value = {
            "document_id": "doc-123",
            "source_id": "qc-analyzer-result",
            "attributes": {
                "factory_id": "factory-001",
            },
        }

        # Act & Assert
        with pytest.raises(QualityEventProcessingError) as exc_info:
            await processor.process(
                document_id="doc-123",
                farmer_id="WM-0001",
            )

        assert exc_info.value.error_type == "missing_grading_model"

    @pytest.mark.asyncio
    async def test_process_date_rollover_resets_today(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        sample_document: dict,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test that date rollover resets today's metrics."""
        # Arrange - performance from yesterday
        yesterday_performance = sample_farmer_performance.model_copy()
        yesterday_performance.today.metrics_date = dt.date.today() - dt.timedelta(days=1)

        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = yesterday_performance
        mock_farmer_performance_repo.reset_today.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        await processor.process(
            document_id="doc-123",
            farmer_id="WM-0001",
        )

        # Assert
        mock_farmer_performance_repo.reset_today.assert_called_once_with("WM-0001")

    @pytest.mark.asyncio
    async def test_process_emits_quality_graded_event(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_event_publisher: AsyncMock,
        sample_document: dict,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test that plantation.quality.graded event is emitted."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        await processor.process(
            document_id="doc-123",
            farmer_id="WM-0001",
        )

        # Assert - check event publisher was called with quality.graded
        calls = mock_event_publisher.publish_event.call_args_list
        quality_graded_call = next(
            (c for c in calls if c.kwargs.get("topic") == "plantation.quality.graded"),
            None,
        )
        assert quality_graded_call is not None

    @pytest.mark.asyncio
    async def test_process_emits_performance_updated_event(
        self,
        processor: QualityEventProcessor,
        mock_collection_client: AsyncMock,
        mock_grading_model_repo: AsyncMock,
        mock_farmer_performance_repo: AsyncMock,
        mock_event_publisher: AsyncMock,
        sample_document: dict,
        sample_grading_model: GradingModel,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test that plantation.performance_updated event is emitted."""
        # Arrange
        mock_collection_client.get_document.return_value = sample_document
        mock_grading_model_repo.get_by_id_and_version.return_value = sample_grading_model
        mock_farmer_performance_repo.get_by_farmer_id.return_value = sample_farmer_performance
        mock_farmer_performance_repo.increment_today_delivery.return_value = sample_farmer_performance

        # Act
        await processor.process(
            document_id="doc-123",
            farmer_id="WM-0001",
        )

        # Assert - check performance_updated event
        calls = mock_event_publisher.publish_event.call_args_list
        perf_updated_call = next(
            (c for c in calls if c.kwargs.get("topic") == "plantation.performance_updated"),
            None,
        )
        assert perf_updated_call is not None
        # Verify NO current_category field (Engagement Model owns this)
        payload = perf_updated_call.kwargs.get("data", {})
        assert "current_category" not in payload


class TestGradeCountExtraction:
    """Tests for grade count extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_grade_counts_with_direct_counts(
        self,
        processor: QualityEventProcessor,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test extraction when bag_summary has grade_counts."""
        bag_summary = {
            "grade_counts": {"Primary": 10, "Secondary": 3},
        }

        result = processor._extract_grade_counts(bag_summary, sample_grading_model)

        assert result["Primary"] == 10
        assert result["Secondary"] == 3

    @pytest.mark.asyncio
    async def test_extract_grade_counts_from_percentage_high(
        self,
        processor: QualityEventProcessor,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test extraction assigns to Primary when primary_percentage >= 50."""
        bag_summary = {
            "primary_percentage": 80.0,
        }

        result = processor._extract_grade_counts(bag_summary, sample_grading_model)

        assert result.get("Primary") == 1

    @pytest.mark.asyncio
    async def test_extract_grade_counts_from_percentage_low(
        self,
        processor: QualityEventProcessor,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test extraction assigns to Secondary when primary_percentage < 50."""
        bag_summary = {
            "primary_percentage": 30.0,
        }

        result = processor._extract_grade_counts(bag_summary, sample_grading_model)

        assert result.get("Secondary") == 1


class TestPrimaryPercentageComputation:
    """Tests for primary percentage computation."""

    def test_compute_primary_percentage_with_counts(
        self,
        processor: QualityEventProcessor,
    ) -> None:
        """Test primary percentage calculation."""
        grade_counts = {"Primary": 8, "Secondary": 2}

        result = processor._compute_primary_percentage(grade_counts)

        assert result == 80.0

    def test_compute_primary_percentage_empty(
        self,
        processor: QualityEventProcessor,
    ) -> None:
        """Test primary percentage returns 0 for empty counts."""
        result = processor._compute_primary_percentage({})

        assert result == 0.0

    def test_compute_primary_percentage_zero_total(
        self,
        processor: QualityEventProcessor,
    ) -> None:
        """Test primary percentage returns 0 when total is 0."""
        grade_counts = {"Primary": 0, "Secondary": 0}

        result = processor._compute_primary_percentage(grade_counts)

        assert result == 0.0


class TestImprovementTrendComputation:
    """Tests for improvement trend computation."""

    def test_compute_trend_improving(
        self,
        processor: QualityEventProcessor,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test trend is IMPROVING when 30d > 90d + 5."""
        sample_farmer_performance.historical.primary_percentage_30d = 80.0
        sample_farmer_performance.historical.primary_percentage_90d = 70.0

        result = processor._compute_improvement_trend(sample_farmer_performance)

        assert result == TrendDirection.IMPROVING

    def test_compute_trend_declining(
        self,
        processor: QualityEventProcessor,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test trend is DECLINING when 30d < 90d - 5."""
        sample_farmer_performance.historical.primary_percentage_30d = 60.0
        sample_farmer_performance.historical.primary_percentage_90d = 75.0

        result = processor._compute_improvement_trend(sample_farmer_performance)

        assert result == TrendDirection.DECLINING

    def test_compute_trend_stable(
        self,
        processor: QualityEventProcessor,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test trend is STABLE when within ±5%."""
        sample_farmer_performance.historical.primary_percentage_30d = 72.0
        sample_farmer_performance.historical.primary_percentage_90d = 70.0

        result = processor._compute_improvement_trend(sample_farmer_performance)

        assert result == TrendDirection.STABLE


class TestAttributeDistributionExtraction:
    """Tests for attribute distribution extraction."""

    def test_extract_attribute_distribution(
        self,
        processor: QualityEventProcessor,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test extraction of leaf type distribution."""
        bag_summary = {
            "leaf_type_distribution": {
                "bud": 5,
                "two_leaves_bud": 15,
                "coarse_leaf": 3.0,  # Float should be converted to int
            },
        }

        result = processor._extract_attribute_distribution(bag_summary, sample_grading_model)

        assert result["leaf_type"]["bud"] == 5
        assert result["leaf_type"]["two_leaves_bud"] == 15
        assert result["leaf_type"]["coarse_leaf"] == 3

    def test_extract_attribute_distribution_empty(
        self,
        processor: QualityEventProcessor,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test empty distribution when no leaf_type_distribution."""
        bag_summary = {}

        result = processor._extract_attribute_distribution(bag_summary, sample_grading_model)

        assert result == {}
