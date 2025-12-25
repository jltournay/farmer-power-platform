"""Farmer Performance domain models.

FarmerPerformance tracks quality metrics and trends for individual farmers.
It includes both historical metrics (computed by batch jobs) and today's
real-time metrics (updated by streaming events).

Key relationships:
- References a GradingModel for interpreting grade and attribute distributions
- Links to a Farmer via farmer_id
- Contains denormalized farm context (size, scale) for efficient computation
"""

import datetime as dt
from datetime import datetime
from enum import Enum

from plantation_model.domain.models.farmer import FarmScale
from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Trend direction for farmer performance.

    Computed by comparing recent performance (30d) vs longer term (90d/year).
    """

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class HistoricalMetrics(BaseModel):
    """Historical performance metrics computed by batch job.

    These metrics are updated periodically (e.g., nightly) by batch jobs
    that aggregate quality events from the Collection Model.

    Structure supports attribute-level tracking for root-cause analysis:
    e.g., "Your coarse_leaf count increased from 8% to 15%"
    """

    # Grade-level distributions
    grade_distribution_30d: dict[str, int] = Field(
        default_factory=dict,
        description="Grade counts for last 30 days (e.g., {'Primary': 120, 'Secondary': 30})",
    )
    grade_distribution_90d: dict[str, int] = Field(
        default_factory=dict,
        description="Grade counts for last 90 days",
    )
    grade_distribution_year: dict[str, int] = Field(
        default_factory=dict,
        description="Grade counts for last year",
    )

    # Attribute-level distributions (enables root-cause analysis)
    # Structure: {"attribute_name": {"class_name": count, ...}, ...}
    attribute_distributions_30d: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Attribute class counts for last 30 days",
    )
    attribute_distributions_90d: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Attribute class counts for last 90 days",
    )
    attribute_distributions_year: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Attribute class counts for last year",
    )

    # Derived convenience metrics
    primary_percentage_30d: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade in last 30 days",
    )
    primary_percentage_90d: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade in last 90 days",
    )
    primary_percentage_year: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade in last year",
    )

    # Volume metrics
    total_kg_30d: float = Field(
        default=0.0,
        ge=0.0,
        description="Total kg delivered in last 30 days",
    )
    total_kg_90d: float = Field(
        default=0.0,
        ge=0.0,
        description="Total kg delivered in last 90 days",
    )
    total_kg_year: float = Field(
        default=0.0,
        ge=0.0,
        description="Total kg delivered in last year",
    )

    # Yield metrics
    yield_kg_per_hectare_30d: float = Field(
        default=0.0,
        ge=0.0,
        description="Yield per hectare in last 30 days",
    )
    yield_kg_per_hectare_90d: float = Field(
        default=0.0,
        ge=0.0,
        description="Yield per hectare in last 90 days",
    )
    yield_kg_per_hectare_year: float = Field(
        default=0.0,
        ge=0.0,
        description="Yield per hectare in last year",
    )

    # Trend
    improvement_trend: TrendDirection = Field(
        default=TrendDirection.STABLE,
        description="Quality trend direction",
    )
    computed_at: datetime | None = Field(
        default=None,
        description="When these metrics were last computed",
    )


class TodayMetrics(BaseModel):
    """Today's performance metrics (updated by streaming events).

    These metrics are updated in real-time as quality events arrive
    from the Collection Model. They reset when the date changes.
    """

    deliveries: int = Field(
        default=0,
        ge=0,
        description="Number of deliveries today",
    )
    total_kg: float = Field(
        default=0.0,
        ge=0.0,
        description="Total kg delivered today",
    )

    # Grade-level counts for today
    grade_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Grade counts for today",
    )

    # Attribute-level counts for today
    # Structure: {"attribute_name": {"class_name": count, ...}, ...}
    attribute_counts: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Attribute class counts for today",
    )

    last_delivery: datetime | None = Field(
        default=None,
        description="Timestamp of last delivery today",
    )
    metrics_date: dt.date = Field(
        default_factory=dt.date.today,
        description="Date these metrics are for (resets when date changes)",
    )


class FarmerPerformance(BaseModel):
    """Complete farmer performance tracking with attribute-level detail.

    This is the central model for understanding a farmer's quality performance.
    It combines:
    - Historical metrics (batch-computed trends and distributions)
    - Today's metrics (real-time delivery tracking)
    - Farm context (for yield calculations and scale-based recommendations)

    Key features:
    - Attribute-level tracking enables root-cause analysis
    - Trend detection helps identify improvement opportunities
    - Grading model reference ensures correct label interpretation
    """

    farmer_id: str = Field(description="Reference to farmer")

    # Grading model reference (for interpreting distributions)
    grading_model_id: str = Field(description="Reference to grading model")
    grading_model_version: str = Field(description="Grading model version")

    # Farm context (denormalized for efficient computation)
    farm_size_hectares: float = Field(
        ge=0.01,
        le=1000.0,
        description="Farm size for yield calculations",
    )
    farm_scale: FarmScale = Field(description="Farm scale classification")

    # Performance metrics
    historical: HistoricalMetrics = Field(default_factory=HistoricalMetrics)
    today: TodayMetrics = Field(default_factory=TodayMetrics)

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(dt.UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(dt.UTC),
        description="Last update timestamp",
    )

    @classmethod
    def initialize_for_farmer(
        cls,
        farmer_id: str,
        farm_size_hectares: float,
        farm_scale: FarmScale,
        grading_model_id: str,
        grading_model_version: str,
    ) -> "FarmerPerformance":
        """Create default performance record for a new farmer.

        Called when a farmer is registered to initialize their performance
        tracking with the factory's assigned grading model.

        Args:
            farmer_id: The farmer's unique identifier.
            farm_size_hectares: Farm size for yield calculations.
            farm_scale: Farm scale classification.
            grading_model_id: The grading model assigned to the farmer's factory.
            grading_model_version: Version of the grading model.

        Returns:
            A new FarmerPerformance with default empty metrics.
        """
        return cls(
            farmer_id=farmer_id,
            grading_model_id=grading_model_id,
            grading_model_version=grading_model_version,
            farm_size_hectares=farm_size_hectares,
            farm_scale=farm_scale,
        )

    def get_attribute_trend(
        self,
        attribute_name: str,
        class_name: str,
    ) -> str | None:
        """Compare 30d vs 90d distribution for a specific attribute class.

        This enables insights like "Your coarse_leaf rate has been increasing"
        which helps with targeted coaching.

        Args:
            attribute_name: The attribute to analyze (e.g., "leaf_type").
            class_name: The class within the attribute (e.g., "coarse_leaf").

        Returns:
            "increasing", "decreasing", "stable", or None if insufficient data.
        """
        dist_30d = self.historical.attribute_distributions_30d.get(attribute_name, {})
        dist_90d = self.historical.attribute_distributions_90d.get(attribute_name, {})

        count_30d = dist_30d.get(class_name, 0)
        count_90d = dist_90d.get(class_name, 0)

        # Need data in both periods
        total_30d = sum(dist_30d.values()) if dist_30d else 0
        total_90d = sum(dist_90d.values()) if dist_90d else 0

        if total_30d < 3 or total_90d < 3:
            return None

        pct_30d = count_30d / total_30d
        pct_90d = count_90d / total_90d

        if pct_30d > pct_90d * 1.1:  # 10% threshold
            return "increasing"
        elif pct_30d < pct_90d * 0.9:
            return "decreasing"
        else:
            return "stable"

    model_config = {
        "json_schema_extra": {
            "example": {
                "farmer_id": "WM-0001",
                "grading_model_id": "tbk_kenya_tea_v1",
                "grading_model_version": "1.0.0",
                "farm_size_hectares": 1.5,
                "farm_scale": "medium",
                "historical": {
                    "grade_distribution_30d": {"Primary": 120, "Secondary": 30},
                    "attribute_distributions_30d": {
                        "leaf_type": {
                            "bud": 15,
                            "one_leaf_bud": 45,
                            "two_leaves_bud": 50,
                            "three_plus_leaves_bud": 10,
                            "coarse_leaf": 15,
                            "banji": 5,
                        },
                        "banji_hardness": {"soft": 3, "hard": 2},
                    },
                    "primary_percentage_30d": 80.0,
                    "improvement_trend": "improving",
                },
                "today": {
                    "deliveries": 2,
                    "total_kg": 45.0,
                    "grade_counts": {"Primary": 2},
                    "attribute_counts": {"leaf_type": {"two_leaves_bud": 2}},
                },
            },
        },
    }
