"""Unit tests for budget monitoring.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_model.domain.cost_event import LlmCostEvent
from ai_model.llm.budget_monitor import BudgetMonitor, ThresholdType


def create_cost_event(
    cost_usd: float = 1.0,
    timestamp: datetime | None = None,
) -> LlmCostEvent:
    """Create a test cost event."""
    return LlmCostEvent(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(UTC),
        request_id=str(uuid.uuid4()),
        agent_type="test",
        agent_id="test-agent",
        model="test-model",
        tokens_in=100,
        tokens_out=50,
        cost_usd=Decimal(str(cost_usd)),
        success=True,
        retry_count=0,
    )


class TestBudgetMonitor:
    """Tests for BudgetMonitor class."""

    def test_initialization(self) -> None:
        """Test budget monitor initialization."""
        monitor = BudgetMonitor(
            daily_threshold_usd=10.0,
            monthly_threshold_usd=100.0,
        )
        status = monitor.get_status()
        # Decimal string representation may include .0 for whole numbers
        assert Decimal(status["daily_threshold_usd"]) == Decimal("10")
        assert Decimal(status["monthly_threshold_usd"]) == Decimal("100")
        assert Decimal(status["daily_total_usd"]) == Decimal("0")
        assert Decimal(status["monthly_total_usd"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_record_cost_accumulates(self) -> None:
        """Test that costs accumulate correctly."""
        monitor = BudgetMonitor(daily_threshold_usd=100.0)

        await monitor.record_cost(create_cost_event(cost_usd=5.0))
        await monitor.record_cost(create_cost_event(cost_usd=3.0))
        await monitor.record_cost(create_cost_event(cost_usd=2.0))

        status = monitor.get_status()
        assert Decimal(status["daily_total_usd"]) == Decimal("10")
        assert Decimal(status["monthly_total_usd"]) == Decimal("10")

    @pytest.mark.asyncio
    async def test_daily_alert_triggered_when_threshold_exceeded(self) -> None:
        """Test daily alert is triggered when threshold exceeded."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)

        # Record costs below threshold
        await monitor.record_cost(create_cost_event(cost_usd=5.0))
        alert = await monitor.record_cost(create_cost_event(cost_usd=3.0))
        assert alert is None

        # Record cost that exceeds threshold
        alert = await monitor.record_cost(create_cost_event(cost_usd=3.0))
        assert alert is not None
        assert alert.threshold_type == ThresholdType.DAILY
        assert alert.threshold_usd == Decimal("10")
        assert alert.current_cost_usd == Decimal("11")

    @pytest.mark.asyncio
    async def test_monthly_alert_triggered_when_threshold_exceeded(self) -> None:
        """Test monthly alert is triggered when threshold exceeded."""
        monitor = BudgetMonitor(
            daily_threshold_usd=0.0,  # Disabled
            monthly_threshold_usd=50.0,
        )

        # Record costs below threshold
        await monitor.record_cost(create_cost_event(cost_usd=25.0))
        await monitor.record_cost(create_cost_event(cost_usd=20.0))

        # Record cost that exceeds threshold
        alert = await monitor.record_cost(create_cost_event(cost_usd=10.0))
        assert alert is not None
        assert alert.threshold_type == ThresholdType.MONTHLY
        assert alert.threshold_usd == Decimal("50")

    @pytest.mark.asyncio
    async def test_no_duplicate_daily_alerts(self) -> None:
        """Test that daily alert is only triggered once per period."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)

        # First event triggers alert
        await monitor.record_cost(create_cost_event(cost_usd=15.0))

        # Subsequent events should not trigger alert
        alert = await monitor.record_cost(create_cost_event(cost_usd=5.0))
        assert alert is None

        status = monitor.get_status()
        assert status["daily_alert_triggered"] is True

    @pytest.mark.asyncio
    async def test_no_duplicate_monthly_alerts(self) -> None:
        """Test that monthly alert is only triggered once per period."""
        monitor = BudgetMonitor(monthly_threshold_usd=50.0)

        # First event triggers alert
        await monitor.record_cost(create_cost_event(cost_usd=60.0))

        # Subsequent events should not trigger alert
        alert = await monitor.record_cost(create_cost_event(cost_usd=10.0))
        assert alert is None

        status = monitor.get_status()
        assert status["monthly_alert_triggered"] is True

    @pytest.mark.asyncio
    async def test_daily_reset_at_day_boundary(self) -> None:
        """Test daily totals reset at day boundary."""
        monitor = BudgetMonitor(daily_threshold_usd=100.0)

        # Record cost for "yesterday"
        yesterday = datetime.now(UTC) - timedelta(days=1)
        await monitor.record_cost(create_cost_event(cost_usd=50.0, timestamp=yesterday))

        # Record cost for "today" - should reset
        today = datetime.now(UTC)
        await monitor.record_cost(create_cost_event(cost_usd=10.0, timestamp=today))

        status = monitor.get_status()
        assert Decimal(status["daily_total_usd"]) == Decimal("10")  # Only today's cost

    def test_update_thresholds(self) -> None:
        """Test threshold updates at runtime."""
        monitor = BudgetMonitor(
            daily_threshold_usd=10.0,
            monthly_threshold_usd=100.0,
        )

        monitor.update_thresholds(
            daily_threshold_usd=20.0,
            monthly_threshold_usd=200.0,
        )

        status = monitor.get_status()
        assert Decimal(status["daily_threshold_usd"]) == Decimal("20")
        assert Decimal(status["monthly_threshold_usd"]) == Decimal("200")

    @pytest.mark.asyncio
    async def test_alert_reset_after_threshold_increase(self) -> None:
        """Test alert is reset when threshold increases above total."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)

        # Trigger alert
        await monitor.record_cost(create_cost_event(cost_usd=15.0))
        status = monitor.get_status()
        assert status["daily_alert_triggered"] is True

        # Increase threshold above current total
        monitor.update_thresholds(daily_threshold_usd=20.0)
        status = monitor.get_status()
        assert status["daily_alert_triggered"] is False

    def test_reset_totals(self) -> None:
        """Test reset_totals clears all state."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)
        monitor.reset_totals()

        status = monitor.get_status()
        assert status["daily_total_usd"] == "0"
        assert status["monthly_total_usd"] == "0"
        assert status["daily_alert_triggered"] is False
        assert status["monthly_alert_triggered"] is False

    @pytest.mark.asyncio
    async def test_disabled_threshold_no_alert(self) -> None:
        """Test no alert when threshold is 0 (disabled)."""
        monitor = BudgetMonitor(
            daily_threshold_usd=0.0,  # Disabled
            monthly_threshold_usd=0.0,  # Disabled
        )

        alert = await monitor.record_cost(create_cost_event(cost_usd=1000.0))
        assert alert is None

    @pytest.mark.asyncio
    async def test_alert_overage_calculation(self) -> None:
        """Test alert overage is calculated correctly."""
        monitor = BudgetMonitor(daily_threshold_usd=10.0)

        # Exceed by exactly 5
        alert = await monitor.record_cost(create_cost_event(cost_usd=15.0))
        assert alert is not None
        assert alert.overage_usd == Decimal("5")
