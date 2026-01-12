"""Unit tests for BudgetMonitor service.

Story 13.3: Cost Repository and Budget Monitor

Tests:
- Cost recording with threshold checking
- Warm-up from repository (AC #3)
- OpenTelemetry metrics (AC #4)
- Period resets (daily/monthly)
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from platform_cost.domain.cost_event import CurrentDayCost
from platform_cost.services.budget_monitor import (
    BudgetMonitor,
    ThresholdType,
)


@pytest.fixture
def budget_monitor() -> BudgetMonitor:
    """Create BudgetMonitor with test thresholds."""
    return BudgetMonitor(
        daily_threshold_usd=10.0,
        monthly_threshold_usd=100.0,
    )


@pytest.fixture
def mock_cost_repository() -> MagicMock:
    """Create mock UnifiedCostRepository."""
    mock = MagicMock()
    mock.get_current_day_cost = AsyncMock(
        return_value=CurrentDayCost(
            cost_date=date.today(),
            total_cost_usd=Decimal("0"),
            by_type={},
            updated_at=datetime.now(UTC),
        )
    )
    mock.get_current_month_cost = AsyncMock(return_value=Decimal("0"))
    return mock


class TestInitialization:
    """Tests for BudgetMonitor initialization."""

    def test_initializes_with_thresholds(self) -> None:
        """Test that BudgetMonitor initializes with configured thresholds."""
        monitor = BudgetMonitor(
            daily_threshold_usd=15.0,
            monthly_threshold_usd=150.0,
        )

        status = monitor.get_status()
        assert Decimal(status.daily_threshold_usd) == Decimal("15")
        assert Decimal(status.monthly_threshold_usd) == Decimal("150")

    def test_initializes_with_zero_totals(self) -> None:
        """Test that totals start at zero."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)

        status = monitor.get_status()
        assert Decimal(status.daily_total_usd) == Decimal("0")
        assert Decimal(status.monthly_total_usd) == Decimal("0")

    def test_zero_threshold_means_disabled(self) -> None:
        """Test that zero threshold disables alerting."""
        monitor = BudgetMonitor(daily_threshold_usd=0, monthly_threshold_usd=0)

        # Record high cost - should not trigger alert since thresholds are 0
        alert = monitor.record_cost("llm", Decimal("1000.00"))
        assert alert is None


class TestRecordCost:
    """Tests for record_cost method."""

    def test_accumulates_daily_total(self, budget_monitor) -> None:
        """Test that costs are accumulated in daily total."""
        budget_monitor.record_cost("llm", Decimal("1.00"))
        budget_monitor.record_cost("llm", Decimal("2.00"))
        budget_monitor.record_cost("document", Decimal("0.50"))

        status = budget_monitor.get_status()
        assert Decimal(status.daily_total_usd) == Decimal("3.5")

    def test_accumulates_monthly_total(self, budget_monitor) -> None:
        """Test that costs are accumulated in monthly total."""
        budget_monitor.record_cost("llm", Decimal("5.00"))
        budget_monitor.record_cost("document", Decimal("3.00"))

        status = budget_monitor.get_status()
        assert Decimal(status.monthly_total_usd) == Decimal("8")

    def test_tracks_by_type(self, budget_monitor) -> None:
        """Test that costs are tracked per type."""
        budget_monitor.record_cost("llm", Decimal("2.00"))
        budget_monitor.record_cost("document", Decimal("1.00"))
        budget_monitor.record_cost("llm", Decimal("3.00"))

        status = budget_monitor.get_status()
        assert Decimal(status.by_type["llm"]) == Decimal("5")
        assert Decimal(status.by_type["document"]) == Decimal("1")

    def test_returns_daily_threshold_alert(self, budget_monitor) -> None:
        """Test that daily threshold breach returns DAILY alert."""
        # Record costs up to threshold
        alert = budget_monitor.record_cost("llm", Decimal("10.00"))

        assert alert == ThresholdType.DAILY

    def test_daily_alert_only_fires_once(self, budget_monitor) -> None:
        """Test that daily alert only fires once per period."""
        # First breach - should alert
        alert1 = budget_monitor.record_cost("llm", Decimal("10.00"))
        assert alert1 == ThresholdType.DAILY

        # Second cost after breach - should not re-alert
        alert2 = budget_monitor.record_cost("llm", Decimal("5.00"))
        assert alert2 is None

    def test_returns_monthly_threshold_alert(self, budget_monitor) -> None:
        """Test that monthly threshold breach returns MONTHLY alert."""
        # Record costs up to monthly threshold
        alert = budget_monitor.record_cost("llm", Decimal("100.00"))

        # Daily fires first since it's also exceeded
        assert alert == ThresholdType.DAILY

        # Record more to get monthly alert
        alert2 = budget_monitor.record_cost("llm", Decimal("1.00"))
        assert alert2 == ThresholdType.MONTHLY

    def test_no_alert_under_threshold(self, budget_monitor) -> None:
        """Test that no alert fires when under threshold."""
        alert = budget_monitor.record_cost("llm", Decimal("5.00"))
        assert alert is None


class TestWarmUp:
    """Tests for warm_up_from_repository method (AC #3)."""

    @pytest.mark.asyncio
    async def test_restores_daily_total(self, budget_monitor, mock_cost_repository) -> None:
        """Test that warm-up restores daily total from repository."""
        mock_cost_repository.get_current_day_cost.return_value = CurrentDayCost(
            cost_date=date.today(),
            total_cost_usd=Decimal("5.00"),
            by_type={"llm": Decimal("4.00"), "document": Decimal("1.00")},
            updated_at=datetime.now(UTC),
        )

        await budget_monitor.warm_up_from_repository(mock_cost_repository)

        status = budget_monitor.get_status()
        assert Decimal(status.daily_total_usd) == Decimal("5")
        assert Decimal(status.by_type["llm"]) == Decimal("4")
        assert Decimal(status.by_type["document"]) == Decimal("1")

    @pytest.mark.asyncio
    async def test_restores_monthly_total(self, budget_monitor, mock_cost_repository) -> None:
        """Test that warm-up restores monthly total from repository."""
        mock_cost_repository.get_current_month_cost.return_value = Decimal("50.00")

        await budget_monitor.warm_up_from_repository(mock_cost_repository)

        status = budget_monitor.get_status()
        assert Decimal(status.monthly_total_usd) == Decimal("50")

    @pytest.mark.asyncio
    async def test_sets_alert_state_if_exceeded(self, budget_monitor, mock_cost_repository) -> None:
        """Test that warm-up sets alert state if threshold already exceeded."""
        mock_cost_repository.get_current_day_cost.return_value = CurrentDayCost(
            cost_date=date.today(),
            total_cost_usd=Decimal("15.00"),  # Over daily threshold of 10
            by_type={},
            updated_at=datetime.now(UTC),
        )
        mock_cost_repository.get_current_month_cost.return_value = Decimal("15.00")

        await budget_monitor.warm_up_from_repository(mock_cost_repository)

        status = budget_monitor.get_status()
        assert status.daily_alert_triggered is True
        # Monthly is not exceeded (50 < 100), so should be False
        assert status.monthly_alert_triggered is False

    @pytest.mark.asyncio
    async def test_fail_fast_on_repository_error(self, budget_monitor) -> None:
        """Test that warm-up fails fast if repository query fails (AC #3)."""
        mock_repo = MagicMock()
        mock_repo.get_current_day_cost = AsyncMock(side_effect=Exception("DB connection failed"))

        with pytest.raises(Exception) as exc_info:
            await budget_monitor.warm_up_from_repository(mock_repo)

        assert "DB connection failed" in str(exc_info.value)


class TestPeriodReset:
    """Tests for period reset behavior."""

    def test_daily_reset_on_new_day(self, budget_monitor) -> None:
        """Test that daily totals reset on new day."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        today = datetime.now(UTC)

        # Record cost for yesterday
        budget_monitor.record_cost("llm", Decimal("5.00"), timestamp=yesterday)

        # Record cost for today - should reset daily
        budget_monitor.record_cost("llm", Decimal("2.00"), timestamp=today)

        status = budget_monitor.get_status()
        assert Decimal(status.daily_total_usd) == Decimal("2")
        assert status.current_day == today.date().isoformat()

    def test_daily_reset_clears_alert_state(self, budget_monitor) -> None:
        """Test that daily reset clears alert state."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        today = datetime.now(UTC)

        # Trigger daily alert yesterday
        budget_monitor.record_cost("llm", Decimal("15.00"), timestamp=yesterday)

        # New day should reset alert
        budget_monitor.record_cost("llm", Decimal("1.00"), timestamp=today)

        status = budget_monitor.get_status()
        assert status.daily_alert_triggered is False


class TestGetStatus:
    """Tests for get_status method."""

    def test_returns_budget_status(self, budget_monitor) -> None:
        """Test that get_status returns BudgetStatus model."""
        budget_monitor.record_cost("llm", Decimal("3.00"))

        status = budget_monitor.get_status()

        assert Decimal(status.daily_threshold_usd) == Decimal("10")
        assert Decimal(status.daily_total_usd) == Decimal("3")
        assert Decimal(status.daily_remaining_usd) == Decimal("7")
        assert status.daily_utilization_percent == 30.0

    def test_utilization_percentage_calculation(self, budget_monitor) -> None:
        """Test utilization percentage is calculated correctly."""
        budget_monitor.record_cost("llm", Decimal("2.50"))

        status = budget_monitor.get_status()
        assert status.daily_utilization_percent == 25.0  # 2.5 / 10 * 100

    def test_remaining_never_negative(self, budget_monitor) -> None:
        """Test that remaining budget is never negative."""
        budget_monitor.record_cost("llm", Decimal("15.00"))  # Over threshold

        status = budget_monitor.get_status()
        assert Decimal(status.daily_remaining_usd) == Decimal("0")


class TestUpdateThresholds:
    """Tests for update_thresholds method."""

    def test_updates_daily_threshold(self, budget_monitor) -> None:
        """Test that daily threshold can be updated."""
        budget_monitor.update_thresholds(daily_threshold_usd=20.0)

        status = budget_monitor.get_status()
        assert Decimal(status.daily_threshold_usd) == Decimal("20")

    def test_updates_monthly_threshold(self, budget_monitor) -> None:
        """Test that monthly threshold can be updated."""
        budget_monitor.update_thresholds(monthly_threshold_usd=200.0)

        status = budget_monitor.get_status()
        assert Decimal(status.monthly_threshold_usd) == Decimal("200")

    def test_partial_update_preserves_other_threshold(self, budget_monitor) -> None:
        """Test that partial update preserves other threshold."""
        budget_monitor.update_thresholds(daily_threshold_usd=25.0)

        status = budget_monitor.get_status()
        assert Decimal(status.daily_threshold_usd) == Decimal("25")
        assert Decimal(status.monthly_threshold_usd) == Decimal("100")  # Unchanged

    def test_resets_alert_if_new_threshold_higher(self, budget_monitor) -> None:
        """Test that alert state resets if new threshold is higher than total."""
        # Trigger alert
        budget_monitor.record_cost("llm", Decimal("10.00"))
        assert budget_monitor.get_status().daily_alert_triggered is True

        # Raise threshold above current total
        budget_monitor.update_thresholds(daily_threshold_usd=20.0)

        # Alert should be reset
        assert budget_monitor.get_status().daily_alert_triggered is False


class TestResetTotals:
    """Tests for reset_totals method."""

    def test_resets_all_counters(self, budget_monitor) -> None:
        """Test that reset_totals clears all state."""
        budget_monitor.record_cost("llm", Decimal("10.00"))
        budget_monitor.reset_totals()

        status = budget_monitor.get_status()
        assert status.daily_total_usd == "0"
        assert status.monthly_total_usd == "0"
        assert status.daily_alert_triggered is False
        assert status.monthly_alert_triggered is False
        assert status.by_type == {}
