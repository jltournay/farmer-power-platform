"""Unit tests for FarmerPerformanceRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models.farmer import FarmScale
from plantation_model.domain.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock MongoDB database."""
    return MagicMock()


@pytest.fixture
def farmer_perf_repo(mock_db: MagicMock) -> FarmerPerformanceRepository:
    """Create a FarmerPerformanceRepository with mocked database."""
    return FarmerPerformanceRepository(mock_db)


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
            grade_distribution_30d={"Primary": 100, "Secondary": 20},
            primary_percentage_30d=83.3,
            improvement_trend=TrendDirection.IMPROVING,
        ),
        today=TodayMetrics(
            deliveries=2,
            total_kg=45.0,
            grade_counts={"Primary": 2},
        ),
    )


class TestFarmerPerformanceRepository:
    """Tests for FarmerPerformanceRepository."""

    @pytest.mark.asyncio
    async def test_create_farmer_performance(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test creating a farmer performance record."""
        farmer_perf_repo._collection.insert_one = AsyncMock()

        result = await farmer_perf_repo.create(sample_farmer_performance)

        farmer_perf_repo._collection.insert_one.assert_called_once()
        assert result == sample_farmer_performance

    @pytest.mark.asyncio
    async def test_get_by_farmer_id_found(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test retrieving a farmer performance by farmer ID."""
        mock_doc = sample_farmer_performance.model_dump()
        mock_doc["_id"] = sample_farmer_performance.farmer_id
        farmer_perf_repo._collection.find_one = AsyncMock(return_value=mock_doc)

        result = await farmer_perf_repo.get_by_farmer_id(sample_farmer_performance.farmer_id)

        assert result is not None
        assert result.farmer_id == sample_farmer_performance.farmer_id
        assert result.grading_model_id == sample_farmer_performance.grading_model_id

    @pytest.mark.asyncio
    async def test_get_by_farmer_id_not_found(
        self, farmer_perf_repo: FarmerPerformanceRepository
    ) -> None:
        """Test retrieving a non-existent farmer performance."""
        farmer_perf_repo._collection.find_one = AsyncMock(return_value=None)

        result = await farmer_perf_repo.get_by_farmer_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_for_farmer(
        self, farmer_perf_repo: FarmerPerformanceRepository
    ) -> None:
        """Test initializing performance for a new farmer."""
        farmer_perf_repo._collection.insert_one = AsyncMock()

        result = await farmer_perf_repo.initialize_for_farmer(
            farmer_id="WM-0002",
            farm_size_hectares=0.5,
            farm_scale=FarmScale.SMALLHOLDER,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        assert result is not None
        assert result.farmer_id == "WM-0002"
        assert result.grading_model_id == "tbk_kenya_tea_v1"
        assert result.historical.grade_distribution_30d == {}
        assert result.today.deliveries == 0

    @pytest.mark.asyncio
    async def test_update_historical_metrics(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test updating historical metrics."""
        updated_doc = sample_farmer_performance.model_dump()
        updated_doc["_id"] = sample_farmer_performance.farmer_id
        updated_doc["historical"]["grade_distribution_30d"] = {"Primary": 150, "Secondary": 25}
        farmer_perf_repo._collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        new_historical = HistoricalMetrics(
            grade_distribution_30d={"Primary": 150, "Secondary": 25},
            primary_percentage_30d=85.7,
        )
        result = await farmer_perf_repo.update_historical(
            sample_farmer_performance.farmer_id, new_historical
        )

        assert result is not None
        assert result.historical.grade_distribution_30d["Primary"] == 150

    @pytest.mark.asyncio
    async def test_update_today_metrics(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test updating today's metrics."""
        updated_doc = sample_farmer_performance.model_dump()
        updated_doc["_id"] = sample_farmer_performance.farmer_id
        updated_doc["today"]["deliveries"] = 3
        updated_doc["today"]["total_kg"] = 60.0
        farmer_perf_repo._collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        new_today = TodayMetrics(
            deliveries=3,
            total_kg=60.0,
            grade_counts={"Primary": 3},
        )
        result = await farmer_perf_repo.update_today(
            sample_farmer_performance.farmer_id, new_today
        )

        assert result is not None
        assert result.today.deliveries == 3
        assert result.today.total_kg == 60.0

    @pytest.mark.asyncio
    async def test_increment_today_delivery(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test incrementing today's delivery count."""
        updated_doc = sample_farmer_performance.model_dump()
        updated_doc["_id"] = sample_farmer_performance.farmer_id
        updated_doc["today"]["deliveries"] = 3
        updated_doc["today"]["total_kg"] = 55.0
        farmer_perf_repo._collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await farmer_perf_repo.increment_today_delivery(
            sample_farmer_performance.farmer_id,
            kg_amount=10.0,
            grade="Primary",
        )

        assert result is not None
        farmer_perf_repo._collection.find_one_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_today_metrics(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test resetting today's metrics for a new day."""
        updated_doc = sample_farmer_performance.model_dump()
        updated_doc["_id"] = sample_farmer_performance.farmer_id
        updated_doc["today"]["deliveries"] = 0
        updated_doc["today"]["total_kg"] = 0.0
        updated_doc["today"]["grade_counts"] = {}
        farmer_perf_repo._collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await farmer_perf_repo.reset_today(sample_farmer_performance.farmer_id)

        assert result is not None
        assert result.today.deliveries == 0

    @pytest.mark.asyncio
    async def test_list_by_grading_model(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test listing farmer performances by grading model."""
        mock_doc = sample_farmer_performance.model_dump()
        mock_doc["_id"] = sample_farmer_performance.farmer_id

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
        farmer_perf_repo._collection.find = MagicMock(return_value=mock_cursor)
        farmer_perf_repo._collection.count_documents = AsyncMock(return_value=1)

        result, next_token, total = await farmer_perf_repo.list_by_grading_model("tbk_kenya_tea_v1")

        assert len(result) == 1
        assert result[0].farmer_id == "WM-0001"
        assert total == 1

    @pytest.mark.asyncio
    async def test_upsert_creates_new(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test upsert creates a new performance record."""
        farmer_perf_repo._collection.replace_one = AsyncMock()

        result = await farmer_perf_repo.upsert(sample_farmer_performance)

        farmer_perf_repo._collection.replace_one.assert_called_once()
        call_args = farmer_perf_repo._collection.replace_one.call_args
        assert call_args[1]["upsert"] is True
        assert result.farmer_id == sample_farmer_performance.farmer_id

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(
        self, farmer_perf_repo: FarmerPerformanceRepository, sample_farmer_performance: FarmerPerformance
    ) -> None:
        """Test upsert updates an existing performance record."""
        farmer_perf_repo._collection.replace_one = AsyncMock()

        # Modify performance and upsert
        sample_farmer_performance.today.deliveries = 5
        result = await farmer_perf_repo.upsert(sample_farmer_performance)

        farmer_perf_repo._collection.replace_one.assert_called_once()
        assert result.today.deliveries == 5

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self, farmer_perf_repo: FarmerPerformanceRepository
    ) -> None:
        """Test index creation."""
        farmer_perf_repo._collection.create_index = AsyncMock()

        await farmer_perf_repo.ensure_indexes()

        # Should create indexes for farmer_id, grading_model_id, farm_scale, trend, and updated_at
        assert farmer_perf_repo._collection.create_index.call_count >= 5
