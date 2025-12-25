"""Unit tests for FarmerPerformance domain model."""

from datetime import UTC, date, datetime

import pytest
from plantation_model.domain.models.farmer import FarmScale
from plantation_model.domain.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from pydantic import ValidationError


class TestTrendDirection:
    """Tests for TrendDirection enum."""

    def test_trend_direction_enum_values(self) -> None:
        """Test TrendDirection enum string values."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DECLINING.value == "declining"


class TestHistoricalMetrics:
    """Tests for HistoricalMetrics model."""

    def test_historical_metrics_defaults(self) -> None:
        """Test historical metrics have sensible defaults."""
        metrics = HistoricalMetrics()

        assert metrics.grade_distribution_30d == {}
        assert metrics.grade_distribution_90d == {}
        assert metrics.grade_distribution_year == {}
        assert metrics.attribute_distributions_30d == {}
        assert metrics.primary_percentage_30d == 0.0
        assert metrics.total_kg_30d == 0.0
        assert metrics.improvement_trend == TrendDirection.STABLE
        assert metrics.computed_at is None

    def test_historical_metrics_with_grade_distribution(self) -> None:
        """Test historical metrics with grade distributions."""
        metrics = HistoricalMetrics(
            grade_distribution_30d={"Primary": 120, "Secondary": 30},
            grade_distribution_90d={"Primary": 300, "Secondary": 100},
        )

        assert metrics.grade_distribution_30d["Primary"] == 120
        assert metrics.grade_distribution_90d["Secondary"] == 100

    def test_historical_metrics_with_attribute_distributions(self) -> None:
        """Test historical metrics with attribute distributions."""
        metrics = HistoricalMetrics(
            attribute_distributions_30d={
                "leaf_type": {"bud": 15, "one_leaf_bud": 45, "coarse_leaf": 10},
                "banji_hardness": {"soft": 3, "hard": 2},
            },
        )

        assert "leaf_type" in metrics.attribute_distributions_30d
        assert metrics.attribute_distributions_30d["leaf_type"]["bud"] == 15
        assert metrics.attribute_distributions_30d["banji_hardness"]["hard"] == 2

    def test_historical_metrics_with_percentages(self) -> None:
        """Test historical metrics with primary percentages."""
        metrics = HistoricalMetrics(
            primary_percentage_30d=80.0,
            primary_percentage_90d=75.5,
            primary_percentage_year=78.2,
        )

        assert metrics.primary_percentage_30d == 80.0
        assert metrics.primary_percentage_90d == 75.5
        assert metrics.primary_percentage_year == 78.2

    def test_historical_metrics_percentage_validation_max(self) -> None:
        """Test primary percentage cannot exceed 100."""
        with pytest.raises(ValidationError):
            HistoricalMetrics(primary_percentage_30d=101.0)

    def test_historical_metrics_percentage_validation_min(self) -> None:
        """Test primary percentage cannot be negative."""
        with pytest.raises(ValidationError):
            HistoricalMetrics(primary_percentage_30d=-1.0)

    def test_historical_metrics_with_volume(self) -> None:
        """Test historical metrics with volume data."""
        metrics = HistoricalMetrics(
            total_kg_30d=450.5,
            total_kg_90d=1200.0,
            total_kg_year=5000.0,
            yield_kg_per_hectare_30d=300.3,
        )

        assert metrics.total_kg_30d == 450.5
        assert metrics.yield_kg_per_hectare_30d == 300.3

    def test_historical_metrics_with_trend(self) -> None:
        """Test historical metrics with improvement trend."""
        metrics = HistoricalMetrics(
            improvement_trend=TrendDirection.IMPROVING,
            computed_at=datetime.now(UTC),
        )

        assert metrics.improvement_trend == TrendDirection.IMPROVING
        assert metrics.computed_at is not None


class TestTodayMetrics:
    """Tests for TodayMetrics model."""

    def test_today_metrics_defaults(self) -> None:
        """Test today metrics have sensible defaults."""
        metrics = TodayMetrics()

        assert metrics.deliveries == 0
        assert metrics.total_kg == 0.0
        assert metrics.grade_counts == {}
        assert metrics.attribute_counts == {}
        assert metrics.last_delivery is None
        assert metrics.metrics_date == date.today()

    def test_today_metrics_with_deliveries(self) -> None:
        """Test today metrics with delivery data."""
        metrics = TodayMetrics(
            deliveries=3,
            total_kg=75.5,
            grade_counts={"Primary": 2, "Secondary": 1},
        )

        assert metrics.deliveries == 3
        assert metrics.total_kg == 75.5
        assert metrics.grade_counts["Primary"] == 2

    def test_today_metrics_with_attribute_counts(self) -> None:
        """Test today metrics with attribute counts."""
        metrics = TodayMetrics(
            attribute_counts={
                "leaf_type": {"two_leaves_bud": 2, "coarse_leaf": 1},
            },
        )

        assert metrics.attribute_counts["leaf_type"]["two_leaves_bud"] == 2

    def test_today_metrics_with_last_delivery(self) -> None:
        """Test today metrics with last delivery timestamp."""
        now = datetime.now(UTC)
        metrics = TodayMetrics(
            deliveries=1,
            last_delivery=now,
        )

        assert metrics.last_delivery == now

    def test_today_metrics_deliveries_non_negative(self) -> None:
        """Test deliveries cannot be negative."""
        with pytest.raises(ValidationError):
            TodayMetrics(deliveries=-1)

    def test_today_metrics_total_kg_non_negative(self) -> None:
        """Test total_kg cannot be negative."""
        with pytest.raises(ValidationError):
            TodayMetrics(total_kg=-1.0)


class TestFarmerPerformance:
    """Tests for FarmerPerformance model."""

    def test_farmer_performance_valid(self) -> None:
        """Test creating a valid farmer performance record."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
        )

        assert perf.farmer_id == "WM-0001"
        assert perf.grading_model_id == "tbk_kenya_tea_v1"
        assert perf.grading_model_version == "1.0.0"
        assert perf.farm_size_hectares == 1.5
        assert perf.farm_scale == FarmScale.MEDIUM

    def test_farmer_performance_default_metrics(self) -> None:
        """Test farmer performance has default empty metrics."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
        )

        assert perf.historical.grade_distribution_30d == {}
        assert perf.today.deliveries == 0

    def test_farmer_performance_with_historical(self) -> None:
        """Test farmer performance with historical data."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                grade_distribution_30d={"Primary": 100, "Secondary": 20},
                primary_percentage_30d=83.3,
                improvement_trend=TrendDirection.IMPROVING,
            ),
        )

        assert perf.historical.grade_distribution_30d["Primary"] == 100
        assert perf.historical.primary_percentage_30d == 83.3
        assert perf.historical.improvement_trend == TrendDirection.IMPROVING

    def test_farmer_performance_with_today(self) -> None:
        """Test farmer performance with today data."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            today=TodayMetrics(
                deliveries=2,
                total_kg=45.0,
                grade_counts={"Primary": 2},
            ),
        )

        assert perf.today.deliveries == 2
        assert perf.today.total_kg == 45.0
        assert perf.today.grade_counts["Primary"] == 2

    def test_farmer_performance_initialize_for_farmer(self) -> None:
        """Test factory method for initializing new farmer performance."""
        perf = FarmerPerformance.initialize_for_farmer(
            farmer_id="WM-0002",
            farm_size_hectares=0.5,
            farm_scale=FarmScale.SMALLHOLDER,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
        )

        assert perf.farmer_id == "WM-0002"
        assert perf.grading_model_id == "tbk_kenya_tea_v1"
        assert perf.farm_size_hectares == 0.5
        assert perf.farm_scale == FarmScale.SMALLHOLDER
        # Should have empty default metrics
        assert perf.historical.grade_distribution_30d == {}
        assert perf.today.deliveries == 0

    def test_farmer_performance_farm_size_validation_min(self) -> None:
        """Test farm size must be at least 0.01 hectares."""
        with pytest.raises(ValidationError):
            FarmerPerformance(
                farmer_id="WM-0001",
                grading_model_id="test_model",
                grading_model_version="1.0.0",
                farm_size_hectares=0.001,  # Too small
                farm_scale=FarmScale.SMALLHOLDER,
            )

    def test_farmer_performance_farm_size_validation_max(self) -> None:
        """Test farm size must not exceed 1000 hectares."""
        with pytest.raises(ValidationError):
            FarmerPerformance(
                farmer_id="WM-0001",
                grading_model_id="test_model",
                grading_model_version="1.0.0",
                farm_size_hectares=1001.0,  # Too large
                farm_scale=FarmScale.ESTATE,
            )

    def test_farmer_performance_timestamps(self) -> None:
        """Test farmer performance has default timestamps."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
        )

        assert perf.created_at is not None
        assert perf.updated_at is not None

    def test_farmer_performance_model_dump(self) -> None:
        """Test farmer performance serialization with model_dump (Pydantic 2.0)."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
        )

        data = perf.model_dump()

        assert data["farmer_id"] == "WM-0001"
        assert data["grading_model_id"] == "test_model"
        assert data["farm_scale"] == "medium"
        assert "historical" in data
        assert "today" in data

    def test_farmer_performance_get_attribute_trend_insufficient_data(self) -> None:
        """Test attribute trend returns None with insufficient data."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                attribute_distributions_30d={
                    "leaf_type": {"bud": 1},  # Too few samples
                },
            ),
        )

        trend = perf.get_attribute_trend("leaf_type", "bud")
        assert trend is None

    def test_farmer_performance_get_attribute_trend_increasing(self) -> None:
        """Test attribute trend detects increasing pattern."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                attribute_distributions_30d={
                    "leaf_type": {"bud": 50, "coarse": 50},  # 50% bud
                },
                attribute_distributions_90d={
                    "leaf_type": {"bud": 30, "coarse": 70},  # 30% bud
                },
            ),
        )

        trend = perf.get_attribute_trend("leaf_type", "bud")
        assert trend == "increasing"

    def test_farmer_performance_get_attribute_trend_decreasing(self) -> None:
        """Test attribute trend detects decreasing pattern."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                attribute_distributions_30d={
                    "leaf_type": {"bud": 30, "coarse": 70},  # 30% bud
                },
                attribute_distributions_90d={
                    "leaf_type": {"bud": 50, "coarse": 50},  # 50% bud
                },
            ),
        )

        trend = perf.get_attribute_trend("leaf_type", "bud")
        assert trend == "decreasing"

    def test_farmer_performance_get_attribute_trend_stable(self) -> None:
        """Test attribute trend detects stable pattern."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                attribute_distributions_30d={
                    "leaf_type": {"bud": 50, "coarse": 50},  # 50% bud
                },
                attribute_distributions_90d={
                    "leaf_type": {"bud": 48, "coarse": 52},  # 48% bud (within 10%)
                },
            ),
        )

        trend = perf.get_attribute_trend("leaf_type", "bud")
        assert trend == "stable"

    def test_farmer_performance_get_attribute_trend_unknown_attribute(self) -> None:
        """Test attribute trend returns None for unknown attribute."""
        perf = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="test_model",
            grading_model_version="1.0.0",
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
        )

        trend = perf.get_attribute_trend("nonexistent", "class")
        assert trend is None
