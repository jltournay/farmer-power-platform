"""Integration tests for FarmerPerformance repository with real MongoDB.

These tests validate that FarmerPerformance CRUD operations work correctly
with a real MongoDB instance. They implement the deferred tests from Story 1-4.

Prerequisites:
    docker-compose -f tests/docker-compose.test.yaml up -d

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_farmer_performance_mongodb.py -v
"""

from datetime import UTC, datetime

import pytest
from plantation_model.domain.models import (
    FarmerPerformance,
    FarmScale,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)


def create_test_farmer_performance(
    farmer_id: str = "WM-0001",
    grading_model_id: str = "tbk_kenya_tea_v1",
    farm_size: float = 1.5,
    farm_scale: FarmScale = FarmScale.MEDIUM,
) -> FarmerPerformance:
    """Create a test farmer performance with default values."""
    return FarmerPerformance(
        farmer_id=farmer_id,
        grading_model_id=grading_model_id,
        grading_model_version="1.0.0",
        farm_size_hectares=farm_size,
        farm_scale=farm_scale,
    )


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestFarmerPerformanceRepository:
    """Integration tests for FarmerPerformanceRepository."""

    async def test_initialize_for_farmer(self, test_db) -> None:
        """Test farmer registration auto-creates performance record.

        Story 1-4, Task 9.2: Test farmer registration creates performance
        record with correct grading_model_id.
        """
        repo = FarmerPerformanceRepository(test_db)

        # Initialize performance for new farmer
        performance = await repo.initialize_for_farmer(
            farmer_id="WM-0001",
            farm_size_hectares=2.0,
            farm_scale=FarmScale.MEDIUM,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        # Verify returned object
        assert performance.farmer_id == "WM-0001"
        assert performance.grading_model_id == "tbk_kenya_tea_v1"
        assert performance.grading_model_version == "1.0.0"
        assert performance.farm_size_hectares == 2.0
        assert performance.farm_scale == FarmScale.MEDIUM

        # Verify stored in DB
        stored = await repo.get_by_farmer_id("WM-0001")
        assert stored is not None
        assert stored.grading_model_id == "tbk_kenya_tea_v1"

    async def test_performance_record_has_correct_grading_model_reference(self, test_db) -> None:
        """Test performance record has correct grading_model_id reference.

        Story 1-4, Task 9.2 continued: Validate grading model reference integrity.
        """
        repo = FarmerPerformanceRepository(test_db)

        # Create with specific grading model
        await repo.initialize_for_farmer(
            farmer_id="WM-0002",
            farm_size_hectares=5.5,
            farm_scale=FarmScale.ESTATE,
            grading_model_id="coffee_grade_v2",
            grading_model_version="2.1.0",
        )

        # Retrieve and verify reference
        stored = await repo.get_by_farmer_id("WM-0002")

        assert stored.grading_model_id == "coffee_grade_v2"
        assert stored.grading_model_version == "2.1.0"
        assert stored.farm_scale == FarmScale.ESTATE

    async def test_get_farmer_summary_returns_complete_data(self, test_db) -> None:
        """Test GetFarmerSummary returns complete performance data.

        Story 1-4, Task 9.3: Test GetFarmerSummary returns complete
        performance data including historical and today metrics.
        """
        repo = FarmerPerformanceRepository(test_db)

        # Create performance with historical data
        performance = FarmerPerformance(
            farmer_id="WM-0003",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.SMALLHOLDER,
            historical=HistoricalMetrics(
                grade_distribution_30d={"Primary": 80, "Secondary": 20},
                grade_distribution_90d={"Primary": 200, "Secondary": 100},
                attribute_distributions_30d={
                    "leaf_type": {
                        "bud": 10,
                        "one_leaf_bud": 30,
                        "two_leaves_bud": 40,
                        "coarse_leaf": 20,
                    }
                },
                primary_percentage_30d=80.0,
                primary_percentage_90d=66.7,
                total_kg_30d=150.0,
                total_kg_90d=500.0,
                yield_kg_per_hectare_30d=150.0,
                improvement_trend=TrendDirection.IMPROVING,
                computed_at=datetime.now(UTC),
            ),
            today=TodayMetrics(
                deliveries=3,
                total_kg=45.0,
                grade_counts={"Primary": 2, "Secondary": 1},
                attribute_counts={"leaf_type": {"two_leaves_bud": 3}},
            ),
        )
        await repo.create(performance)

        # Retrieve complete data
        stored = await repo.get_by_farmer_id("WM-0003")

        # Verify historical data
        assert stored.historical.grade_distribution_30d["Primary"] == 80
        assert stored.historical.grade_distribution_30d["Secondary"] == 20
        assert stored.historical.primary_percentage_30d == 80.0
        assert stored.historical.improvement_trend == TrendDirection.IMPROVING
        assert stored.historical.total_kg_30d == 150.0
        assert "leaf_type" in stored.historical.attribute_distributions_30d

        # Verify today data
        assert stored.today.deliveries == 3
        assert stored.today.total_kg == 45.0
        assert stored.today.grade_counts["Primary"] == 2
        assert "leaf_type" in stored.today.attribute_counts

    async def test_upsert_creates_new_record(self, test_db) -> None:
        """Test upsert creates record if not exists."""
        repo = FarmerPerformanceRepository(test_db)

        performance = create_test_farmer_performance(farmer_id="WM-0004")

        result = await repo.upsert(performance)

        assert result.farmer_id == "WM-0004"

        # Verify in DB
        stored = await repo.get_by_farmer_id("WM-0004")
        assert stored is not None

    async def test_upsert_updates_existing_record(self, test_db) -> None:
        """Test upsert updates existing record."""
        repo = FarmerPerformanceRepository(test_db)

        # Create initial
        performance = create_test_farmer_performance(farmer_id="WM-0005")
        await repo.create(performance)

        # Update via upsert
        updated = FarmerPerformance(
            farmer_id="WM-0005",
            grading_model_id="new_model_v2",
            grading_model_version="2.0.0",
            farm_size_hectares=3.0,
            farm_scale=FarmScale.MEDIUM,
        )
        await repo.upsert(updated)

        # Verify updated
        stored = await repo.get_by_farmer_id("WM-0005")
        assert stored.grading_model_id == "new_model_v2"
        assert stored.farm_size_hectares == 3.0

    async def test_update_historical_metrics(self, test_db) -> None:
        """Test updating historical metrics."""
        repo = FarmerPerformanceRepository(test_db)

        # Create initial
        await repo.initialize_for_farmer(
            farmer_id="WM-0006",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        # Update historical
        new_historical = HistoricalMetrics(
            grade_distribution_30d={"Primary": 100, "Secondary": 10},
            primary_percentage_30d=90.9,
            improvement_trend=TrendDirection.IMPROVING,
            computed_at=datetime.now(UTC),
        )
        updated = await repo.update_historical("WM-0006", new_historical)

        assert updated is not None
        assert updated.historical.grade_distribution_30d["Primary"] == 100
        assert updated.historical.primary_percentage_30d == 90.9
        assert updated.historical.improvement_trend == TrendDirection.IMPROVING

    async def test_update_today_metrics(self, test_db) -> None:
        """Test updating today's metrics."""
        repo = FarmerPerformanceRepository(test_db)

        # Create initial
        await repo.initialize_for_farmer(
            farmer_id="WM-0007",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.SMALLHOLDER,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        # Update today
        new_today = TodayMetrics(
            deliveries=5,
            total_kg=75.0,
            grade_counts={"Primary": 4, "Secondary": 1},
            last_delivery=datetime.now(UTC),
        )
        updated = await repo.update_today("WM-0007", new_today)

        assert updated is not None
        assert updated.today.deliveries == 5
        assert updated.today.total_kg == 75.0
        assert updated.today.grade_counts["Primary"] == 4

    async def test_increment_today_delivery(self, test_db) -> None:
        """Test atomic increment of today's delivery metrics."""
        repo = FarmerPerformanceRepository(test_db)

        # Create initial
        await repo.initialize_for_farmer(
            farmer_id="WM-0008",
            farm_size_hectares=2.0,
            farm_scale=FarmScale.MEDIUM,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        # First delivery
        result1 = await repo.increment_today_delivery(
            farmer_id="WM-0008",
            kg_amount=15.0,
            grade="Primary",
        )

        assert result1.today.deliveries == 1
        assert result1.today.total_kg == 15.0
        assert result1.today.grade_counts["Primary"] == 1

        # Second delivery
        result2 = await repo.increment_today_delivery(
            farmer_id="WM-0008",
            kg_amount=20.0,
            grade="Primary",
        )

        assert result2.today.deliveries == 2
        assert result2.today.total_kg == 35.0
        assert result2.today.grade_counts["Primary"] == 2

        # Third delivery with different grade
        result3 = await repo.increment_today_delivery(
            farmer_id="WM-0008",
            kg_amount=10.0,
            grade="Secondary",
        )

        assert result3.today.deliveries == 3
        assert result3.today.total_kg == 45.0
        assert result3.today.grade_counts["Primary"] == 2
        assert result3.today.grade_counts["Secondary"] == 1

    async def test_increment_today_with_attribute_counts(self, test_db) -> None:
        """Test atomic increment with attribute-level counts."""
        repo = FarmerPerformanceRepository(test_db)

        # Create initial
        await repo.initialize_for_farmer(
            farmer_id="WM-0009",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.SMALLHOLDER,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        # Delivery with attribute counts
        result = await repo.increment_today_delivery(
            farmer_id="WM-0009",
            kg_amount=25.0,
            grade="Primary",
            attribute_counts={
                "leaf_type": {
                    "bud": 5,
                    "one_leaf_bud": 10,
                    "two_leaves_bud": 8,
                },
                "banji_hardness": {
                    "soft": 2,
                },
            },
        )

        assert result.today.attribute_counts["leaf_type"]["bud"] == 5
        assert result.today.attribute_counts["leaf_type"]["one_leaf_bud"] == 10
        assert result.today.attribute_counts["banji_hardness"]["soft"] == 2

    async def test_reset_today_metrics(self, test_db) -> None:
        """Test resetting today's metrics for new day."""
        repo = FarmerPerformanceRepository(test_db)

        # Create with some today data
        performance = FarmerPerformance(
            farmer_id="WM-0010",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            today=TodayMetrics(
                deliveries=5,
                total_kg=100.0,
                grade_counts={"Primary": 4, "Secondary": 1},
            ),
        )
        await repo.create(performance)

        # Reset
        reset = await repo.reset_today("WM-0010")

        assert reset.today.deliveries == 0
        assert reset.today.total_kg == 0.0
        assert reset.today.grade_counts == {}
        assert reset.today.last_delivery is None

    async def test_list_by_grading_model(self, test_db) -> None:
        """Test listing performances by grading model."""
        repo = FarmerPerformanceRepository(test_db)

        # Create performances with different grading models
        for i in range(3):
            await repo.initialize_for_farmer(
                farmer_id=f"WM-100{i}",
                farm_size_hectares=1.0,
                farm_scale=FarmScale.SMALLHOLDER,
                grading_model_id="model_a",
                grading_model_version="1.0.0",
            )

        for i in range(2):
            await repo.initialize_for_farmer(
                farmer_id=f"WM-200{i}",
                farm_size_hectares=2.0,
                farm_scale=FarmScale.MEDIUM,
                grading_model_id="model_b",
                grading_model_version="1.0.0",
            )

        # List by model_a
        results_a, _, total_a = await repo.list_by_grading_model("model_a")
        assert total_a == 3
        assert len(results_a) == 3
        assert all(p.grading_model_id == "model_a" for p in results_a)

        # List by model_b
        results_b, _, total_b = await repo.list_by_grading_model("model_b")
        assert total_b == 2
        assert all(p.grading_model_id == "model_b" for p in results_b)

    async def test_ensure_indexes(self, test_db) -> None:
        """Test index creation happens correctly."""
        repo = FarmerPerformanceRepository(test_db)

        # Create indexes
        await repo.ensure_indexes()

        # Verify indexes exist
        indexes = await test_db["farmer_performances"].index_information()

        assert "idx_farmer_perf_farmer_id" in indexes
        assert "idx_farmer_perf_grading_model" in indexes
        assert "idx_farmer_perf_farm_scale" in indexes
        assert "idx_farmer_perf_trend" in indexes
        assert "idx_farmer_perf_updated_at" in indexes

    async def test_unique_farmer_id_constraint(self, test_db) -> None:
        """Test duplicate farmer_id is rejected."""
        repo = FarmerPerformanceRepository(test_db)
        await repo.ensure_indexes()

        # Create first record
        await repo.initialize_for_farmer(
            farmer_id="WM-DUP",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.SMALLHOLDER,
            grading_model_id="model",
            grading_model_version="1.0.0",
        )

        # Try duplicate - should raise
        with pytest.raises(Exception):  # DuplicateKeyError
            await repo.initialize_for_farmer(
                farmer_id="WM-DUP",
                farm_size_hectares=2.0,
                farm_scale=FarmScale.MEDIUM,
                grading_model_id="model",
                grading_model_version="1.0.0",
            )
