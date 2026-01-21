"""Unit tests for scenario definitions.

Story 0.8.4: Profile-Based Data Generation
AC #5: Scenario-based quality patterns
"""

# Add required paths
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
_tests_demo_path = _project_root / "tests" / "demo"
if str(_tests_demo_path) not in sys.path:
    sys.path.insert(0, str(_tests_demo_path))

from generators.scenarios import (  # noqa: E402
    SCENARIOS,
    FarmerScenario,
    QualityTier,
    ScenarioAssigner,
    get_scenario,
    list_scenarios,
)


class TestQualityTier:
    """Test QualityTier enum."""

    def test_tier_1_percentage_range(self) -> None:
        """Test TIER_1 returns correct percentage range."""
        min_pct, max_pct = QualityTier.TIER_1.get_primary_percentage_range()

        assert min_pct == 85.0
        assert max_pct == 100.0

    def test_tier_2_percentage_range(self) -> None:
        """Test TIER_2 returns correct percentage range."""
        min_pct, max_pct = QualityTier.TIER_2.get_primary_percentage_range()

        assert min_pct == 70.0
        assert max_pct == 84.9

    def test_tier_3_percentage_range(self) -> None:
        """Test TIER_3 returns correct percentage range."""
        min_pct, max_pct = QualityTier.TIER_3.get_primary_percentage_range()

        assert min_pct == 50.0
        assert max_pct == 69.9

    def test_reject_percentage_range(self) -> None:
        """Test REJECT returns correct percentage range."""
        min_pct, max_pct = QualityTier.REJECT.get_primary_percentage_range()

        assert min_pct == 20.0
        assert max_pct == 49.9

    def test_tier_1_grade(self) -> None:
        """Test TIER_1 returns primary grade."""
        assert QualityTier.TIER_1.get_grade() == "primary"

    def test_tier_3_grade(self) -> None:
        """Test TIER_3 returns secondary grade."""
        assert QualityTier.TIER_3.get_grade() == "secondary"

    def test_reject_grade(self) -> None:
        """Test REJECT returns reject grade."""
        assert QualityTier.REJECT.get_grade() == "reject"


class TestPredefinedScenarios:
    """Test predefined scenarios."""

    def test_all_scenarios_defined(self) -> None:
        """Test all expected scenarios are defined."""
        expected = [
            "consistently_poor",
            "improving_trend",
            "top_performer",
            "declining_trend",
            "inactive",
        ]

        for scenario_name in expected:
            assert scenario_name in SCENARIOS

    def test_top_performer_has_all_tier_1(self) -> None:
        """Test top_performer scenario has all TIER_1 quality."""
        scenario = SCENARIOS["top_performer"]

        assert all(t == QualityTier.TIER_1 for t in scenario.quality_pattern)
        assert scenario.status_badge == "WIN"

    def test_improving_trend_improves(self) -> None:
        """Test improving_trend starts low and ends high."""
        scenario = SCENARIOS["improving_trend"]

        # First tier should be worse than last tier
        assert scenario.quality_pattern[0] == QualityTier.TIER_3
        assert scenario.quality_pattern[-1] == QualityTier.TIER_1

    def test_inactive_has_no_pattern(self) -> None:
        """Test inactive scenario has empty pattern."""
        scenario = SCENARIOS["inactive"]

        assert len(scenario.quality_pattern) == 0
        assert scenario.is_active is False


class TestFarmerScenario:
    """Test FarmerScenario dataclass."""

    def test_get_recent_tier_returns_last(self) -> None:
        """Test get_recent_tier returns last tier in pattern."""
        scenario = FarmerScenario(
            name="test",
            description="Test",
            quality_pattern=[QualityTier.TIER_3, QualityTier.TIER_2, QualityTier.TIER_1],
        )

        assert scenario.get_recent_tier() == QualityTier.TIER_1

    def test_get_recent_tier_empty_returns_none(self) -> None:
        """Test get_recent_tier returns None for empty pattern."""
        scenario = FarmerScenario(
            name="test",
            description="Test",
            quality_pattern=[],
        )

        assert scenario.get_recent_tier() is None

    def test_get_trend_improving(self) -> None:
        """Test get_trend detects improving pattern."""
        scenario = FarmerScenario(
            name="test",
            description="Test",
            quality_pattern=[QualityTier.TIER_3, QualityTier.TIER_3, QualityTier.TIER_1, QualityTier.TIER_1],
        )

        assert scenario.get_trend() == "improving"

    def test_get_trend_declining(self) -> None:
        """Test get_trend detects declining pattern."""
        scenario = FarmerScenario(
            name="test",
            description="Test",
            quality_pattern=[QualityTier.TIER_1, QualityTier.TIER_1, QualityTier.TIER_3, QualityTier.TIER_3],
        )

        assert scenario.get_trend() == "declining"

    def test_get_trend_stable(self) -> None:
        """Test get_trend detects stable pattern."""
        scenario = FarmerScenario(
            name="test",
            description="Test",
            quality_pattern=[QualityTier.TIER_2, QualityTier.TIER_2, QualityTier.TIER_2, QualityTier.TIER_2],
        )

        assert scenario.get_trend() == "stable"


class TestScenarioAssigner:
    """Test ScenarioAssigner class."""

    def test_assigner_returns_scenarios_in_order(self) -> None:
        """Test assigner returns scenarios until exhausted."""
        assigner = ScenarioAssigner({"top_performer": 2, "consistently_poor": 1})

        # Get first 3 scenarios
        s1 = assigner.get_next_scenario()
        s2 = assigner.get_next_scenario()
        s3 = assigner.get_next_scenario()

        assert s1 is not None
        assert s2 is not None
        assert s3 is not None

    def test_assigner_returns_none_when_exhausted(self) -> None:
        """Test assigner returns None when all scenarios assigned."""
        assigner = ScenarioAssigner({"top_performer": 1})

        assigner.get_next_scenario()  # Use the one scenario
        result = assigner.get_next_scenario()

        assert result is None

    def test_assigner_remaining_count(self) -> None:
        """Test remaining_count decrements correctly."""
        assigner = ScenarioAssigner({"top_performer": 3})

        assert assigner.remaining_count() == 3
        assigner.get_next_scenario()
        assert assigner.remaining_count() == 2

    def test_assigner_raises_on_unknown_scenario(self) -> None:
        """Test assigner raises for unknown scenario name."""
        with pytest.raises(ValueError) as exc_info:
            ScenarioAssigner({"unknown_scenario": 1})

        assert "unknown_scenario" in str(exc_info.value)


class TestGetScenario:
    """Test get_scenario utility function."""

    def test_get_known_scenario(self) -> None:
        """Test get_scenario returns known scenario."""
        scenario = get_scenario("top_performer")

        assert scenario.name == "top_performer"

    def test_get_unknown_scenario_raises(self) -> None:
        """Test get_scenario raises for unknown scenario."""
        with pytest.raises(ValueError) as exc_info:
            get_scenario("unknown")

        assert "unknown" in str(exc_info.value)


class TestListScenarios:
    """Test list_scenarios utility function."""

    def test_list_scenarios_returns_all(self) -> None:
        """Test list_scenarios returns all scenario names."""
        scenarios = list_scenarios()

        assert "top_performer" in scenarios
        assert "improving_trend" in scenarios
        assert "consistently_poor" in scenarios
