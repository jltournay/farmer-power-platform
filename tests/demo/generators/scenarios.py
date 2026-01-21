"""Farmer quality scenario definitions for demo data generation.

This module provides scenario-based quality patterns that create recognizable
farmer trajectories for demo purposes. Each scenario defines a quality pattern
that generates consistent quality history over time.

Story 0.8.4: Profile-Based Data Generation
AC #5: Quality history scenarios (improving, declining, consistent)

Quality Tiers (aligned with GradingModel grades):
- TIER_1: Premium quality (bud, one_leaf_bud - 80%+ primary)
- TIER_2: Standard quality (two_leaves_bud - 60-80% primary)
- TIER_3: Low quality (three_plus_leaves_bud - <60% primary)
- REJECT: Rejected (coarse_leaf - below threshold)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QualityTier(Enum):
    """Quality tier levels aligned with grading model outcomes.

    These tiers map to primary_percentage ranges and leaf_type distributions
    that produce consistent quality grades across different grading models.
    """

    TIER_1 = "tier_1"  # Premium: 85-100% primary, mostly bud/one_leaf_bud
    TIER_2 = "tier_2"  # Standard: 70-84% primary, mixed leaf types
    TIER_3 = "tier_3"  # Low: 50-69% primary, mostly two_leaves_bud+
    REJECT = "reject"  # Rejected: <50% primary, coarse_leaf dominant

    def get_primary_percentage_range(self) -> tuple[float, float]:
        """Get the primary percentage range for this tier.

        Returns:
            Tuple of (min, max) primary percentage.
        """
        ranges = {
            QualityTier.TIER_1: (85.0, 100.0),
            QualityTier.TIER_2: (70.0, 84.9),
            QualityTier.TIER_3: (50.0, 69.9),
            QualityTier.REJECT: (20.0, 49.9),
        }
        return ranges[self]

    def get_grade(self) -> str:
        """Get the grade label for this tier.

        Returns:
            Grade string (primary, secondary, or reject).
        """
        grades = {
            QualityTier.TIER_1: "primary",
            QualityTier.TIER_2: "primary",
            QualityTier.TIER_3: "secondary",
            QualityTier.REJECT: "reject",
        }
        return grades[self]


@dataclass
class FarmerScenario:
    """Definition of a farmer quality scenario.

    A scenario defines a quality pattern over time that creates recognizable
    farmer trajectories for demo and testing purposes.

    Attributes:
        name: Unique scenario identifier.
        description: Human-readable description for demo storytelling.
        quality_pattern: List of QualityTier values representing quality over time.
            Each entry represents one delivery period (e.g., weekly).
        is_active: Whether the farmer has recent activity.
        status_badge: Expected UI badge based on recent performance.
    """

    name: str
    description: str
    quality_pattern: list[QualityTier] = field(default_factory=list)
    is_active: bool = True
    status_badge: str = "WATCH"  # WIN, WATCH, or ACTION

    def get_recent_tier(self) -> QualityTier | None:
        """Get the most recent quality tier.

        Returns:
            Most recent QualityTier or None if no pattern.
        """
        if not self.quality_pattern:
            return None
        return self.quality_pattern[-1]

    def get_trend(self) -> str:
        """Calculate the quality trend based on pattern.

        Returns:
            Trend string: improving, declining, or stable.
        """
        if len(self.quality_pattern) < 2:
            return "stable"

        # Compare first half to second half
        mid = len(self.quality_pattern) // 2
        first_half = self.quality_pattern[:mid]
        second_half = self.quality_pattern[mid:]

        # Calculate average tier value (TIER_1=1, TIER_2=2, TIER_3=3, REJECT=4)
        tier_values = {
            QualityTier.TIER_1: 1,
            QualityTier.TIER_2: 2,
            QualityTier.TIER_3: 3,
            QualityTier.REJECT: 4,
        }

        first_avg = sum(tier_values[t] for t in first_half) / len(first_half)
        second_avg = sum(tier_values[t] for t in second_half) / len(second_half)

        if second_avg < first_avg - 0.3:
            return "improving"
        elif second_avg > first_avg + 0.3:
            return "declining"
        return "stable"


# Predefined scenarios per AC #5
# Pattern: 5 delivery periods representing quality trajectory over ~2-3 months
SCENARIOS: dict[str, FarmerScenario] = {
    "consistently_poor": FarmerScenario(
        name="consistently_poor",
        description="Farmer struggling with quality - needs intervention",
        quality_pattern=[
            QualityTier.TIER_3,
            QualityTier.TIER_3,
            QualityTier.REJECT,
            QualityTier.TIER_3,
            QualityTier.TIER_3,
        ],
        is_active=True,
        status_badge="ACTION",  # Below 70% primary = red badge
    ),
    "improving_trend": FarmerScenario(
        name="improving_trend",
        description="Farmer showing improvement after receiving advice",
        quality_pattern=[
            QualityTier.TIER_3,
            QualityTier.TIER_3,
            QualityTier.TIER_2,
            QualityTier.TIER_2,
            QualityTier.TIER_1,
        ],
        is_active=True,
        status_badge="WIN",  # Reached 85%+ primary
    ),
    "top_performer": FarmerScenario(
        name="top_performer",
        description="Consistently excellent quality - model farmer",
        quality_pattern=[
            QualityTier.TIER_1,
            QualityTier.TIER_1,
            QualityTier.TIER_1,
            QualityTier.TIER_1,
            QualityTier.TIER_1,
        ],
        is_active=True,
        status_badge="WIN",  # Consistently 85%+ primary
    ),
    "declining_trend": FarmerScenario(
        name="declining_trend",
        description="Farmer showing quality decline - needs attention",
        quality_pattern=[
            QualityTier.TIER_1,
            QualityTier.TIER_2,
            QualityTier.TIER_2,
            QualityTier.TIER_3,
            QualityTier.TIER_3,
        ],
        is_active=True,
        status_badge="WATCH",  # 70-84% primary = yellow badge
    ),
    "inactive": FarmerScenario(
        name="inactive",
        description="Inactive farmer (no recent deliveries)",
        quality_pattern=[],  # No deliveries
        is_active=False,
        status_badge="WATCH",  # Inactive status
    ),
}


def get_scenario(name: str) -> FarmerScenario:
    """Get a predefined scenario by name.

    Args:
        name: Scenario name (consistently_poor, improving_trend, etc.).

    Returns:
        FarmerScenario instance.

    Raises:
        ValueError: If scenario name is not recognized.
    """
    if name not in SCENARIOS:
        valid = ", ".join(SCENARIOS.keys())
        raise ValueError(f"Unknown scenario: {name}. Valid scenarios: {valid}")
    return SCENARIOS[name]


def list_scenarios() -> list[str]:
    """List all available scenario names.

    Returns:
        List of scenario name strings.
    """
    return list(SCENARIOS.keys())


class ScenarioAssigner:
    """Assigns scenarios to farmers based on profile configuration.

    Handles the distribution of predefined scenarios to farmers, with
    remaining farmers getting random quality patterns.

    Example:
        assigner = ScenarioAssigner(
            scenario_counts={"top_performer": 5, "improving_trend": 3}
        )
        for i in range(50):
            scenario = assigner.get_next_scenario()
            if scenario:
                # Apply predefined scenario
                farmer.scenario = scenario.name
            else:
                # Generate random quality pattern
                farmer.scenario = "random"
    """

    def __init__(self, scenario_counts: dict[str, int]) -> None:
        """Initialize with scenario distribution counts.

        Args:
            scenario_counts: Dict mapping scenario name to count.
        """
        self._queue: list[FarmerScenario] = []

        # Build queue of scenarios to assign
        for scenario_name, count in scenario_counts.items():
            if scenario_name not in SCENARIOS:
                raise ValueError(f"Unknown scenario: {scenario_name}")
            scenario = SCENARIOS[scenario_name]
            for _ in range(count):
                self._queue.append(scenario)

        self._index = 0

    def get_next_scenario(self) -> FarmerScenario | None:
        """Get the next scenario to assign.

        Returns:
            FarmerScenario if predefined scenarios remain, None otherwise.
        """
        if self._index >= len(self._queue):
            return None
        scenario = self._queue[self._index]
        self._index += 1
        return scenario

    def remaining_count(self) -> int:
        """Get count of remaining predefined scenarios.

        Returns:
            Number of predefined scenarios not yet assigned.
        """
        return max(0, len(self._queue) - self._index)

    def reset(self) -> None:
        """Reset the assigner to start from beginning."""
        self._index = 0
