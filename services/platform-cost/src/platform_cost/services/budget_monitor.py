"""Budget monitoring for platform-wide cost thresholds.

Story 13.3: Cost Repository and Budget Monitor

This module provides the BudgetMonitor class for tracking running cost totals
across all cost types (LLM, Document, Embedding, SMS) and triggering alerts
when daily or monthly thresholds are exceeded.

Key features:
- Tracks running daily and monthly totals
- OpenTelemetry observable gauges for Prometheus/Grafana
- Warm-up from MongoDB on restart (fail-fast if query fails)
- Runtime threshold updates
- Per-type cost breakdowns

OpenTelemetry Metrics (per AC #4):
- platform_cost_daily_total_usd: Running daily cost
- platform_cost_monthly_total_usd: Running monthly cost
- platform_cost_daily_threshold_usd: Configured daily threshold
- platform_cost_monthly_threshold_usd: Configured monthly threshold
- platform_cost_daily_utilization_percent: % of daily threshold used
- platform_cost_monthly_utilization_percent: % of monthly threshold used
- platform_cost_by_type_usd: Daily cost by cost_type label
- platform_cost_events_total: Counter of events processed
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

import structlog
from opentelemetry import metrics
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from platform_cost.infrastructure.repositories.cost_repository import (
        UnifiedCostRepository,
    )

logger = structlog.get_logger(__name__)

# OpenTelemetry meter
meter = metrics.get_meter("platform_cost.budget_monitor")


class ThresholdType(str, Enum):
    """Types of cost thresholds."""

    DAILY = "daily"
    MONTHLY = "monthly"


class BudgetStatus(BaseModel):
    """Current budget monitoring status.

    Returned by BudgetMonitor.get_status() for dashboard display.

    Attributes:
        daily_threshold_usd: Configured daily threshold
        daily_total_usd: Running daily total
        daily_alert_triggered: Whether daily threshold has been exceeded
        daily_remaining_usd: Remaining daily budget
        daily_utilization_percent: Percentage of daily threshold used
        monthly_threshold_usd: Configured monthly threshold
        monthly_total_usd: Running monthly total
        monthly_alert_triggered: Whether monthly threshold has been exceeded
        monthly_remaining_usd: Remaining monthly budget
        monthly_utilization_percent: Percentage of monthly threshold used
        by_type: Daily breakdown by cost type
        current_day: Current tracking day
        current_month: Current tracking month (YYYY-MM)
    """

    daily_threshold_usd: str = Field(description="Configured daily threshold")
    daily_total_usd: str = Field(description="Running daily total")
    daily_alert_triggered: bool = Field(description="Whether daily threshold exceeded")
    daily_remaining_usd: str = Field(description="Remaining daily budget")
    daily_utilization_percent: float = Field(description="% of daily threshold used")
    monthly_threshold_usd: str = Field(description="Configured monthly threshold")
    monthly_total_usd: str = Field(description="Running monthly total")
    monthly_alert_triggered: bool = Field(description="Whether monthly threshold exceeded")
    monthly_remaining_usd: str = Field(description="Remaining monthly budget")
    monthly_utilization_percent: float = Field(description="% of monthly threshold used")
    by_type: dict[str, str] = Field(description="Daily cost by type")
    current_day: str | None = Field(description="Current tracking day (ISO)")
    current_month: str | None = Field(description="Current tracking month (YYYY-MM)")


class BudgetMonitor:
    """Monitor for platform-wide cost thresholds with alert generation.

    Tracks running daily and monthly costs across all cost types and exposes
    OpenTelemetry metrics for monitoring. Supports warm-up from MongoDB on
    restart to restore accurate totals.

    Example:
        ```python
        monitor = BudgetMonitor(
            daily_threshold_usd=10.0,
            monthly_threshold_usd=100.0,
        )

        # Warm up from repository on startup
        await monitor.warm_up_from_repository(cost_repository)

        # After each cost event
        monitor.record_cost(cost_type="llm", amount_usd=Decimal("0.01"))
        ```
    """

    def __init__(
        self,
        daily_threshold_usd: float = 0.0,
        monthly_threshold_usd: float = 0.0,
    ) -> None:
        """Initialize the budget monitor.

        Args:
            daily_threshold_usd: Daily cost threshold in USD. 0 = disabled.
            monthly_threshold_usd: Monthly cost threshold in USD. 0 = disabled.
        """
        self._daily_threshold = Decimal(str(daily_threshold_usd))
        self._monthly_threshold = Decimal(str(monthly_threshold_usd))

        # Running totals
        self._daily_total = Decimal("0")
        self._monthly_total = Decimal("0")

        # Per-type daily totals
        self._daily_by_type: dict[str, Decimal] = {}

        # Current tracking period
        self._current_day: date | None = None
        self._current_month: tuple[int, int] | None = None  # (year, month)

        # Alert state - only trigger once per period
        self._daily_alert_triggered = False
        self._monthly_alert_triggered = False

        # Event counter
        self._event_counter = meter.create_counter(
            name="platform_cost_events_total",
            description="Total number of cost events processed",
            unit="1",
        )

        # Create observable gauges with callbacks
        self._create_observable_gauges()

        logger.info(
            "Budget monitor initialized",
            daily_threshold_usd=str(self._daily_threshold),
            monthly_threshold_usd=str(self._monthly_threshold),
        )

    def _create_observable_gauges(self) -> None:
        """Create OpenTelemetry observable gauges with callback functions."""
        # Daily total gauge
        meter.create_observable_gauge(
            name="platform_cost_daily_total_usd",
            description="Running daily cost in USD",
            unit="usd",
            callbacks=[self._observe_daily_total],
        )

        # Monthly total gauge
        meter.create_observable_gauge(
            name="platform_cost_monthly_total_usd",
            description="Running monthly cost in USD",
            unit="usd",
            callbacks=[self._observe_monthly_total],
        )

        # Daily threshold gauge
        meter.create_observable_gauge(
            name="platform_cost_daily_threshold_usd",
            description="Configured daily cost threshold in USD",
            unit="usd",
            callbacks=[self._observe_daily_threshold],
        )

        # Monthly threshold gauge
        meter.create_observable_gauge(
            name="platform_cost_monthly_threshold_usd",
            description="Configured monthly cost threshold in USD",
            unit="usd",
            callbacks=[self._observe_monthly_threshold],
        )

        # Daily utilization percentage gauge
        meter.create_observable_gauge(
            name="platform_cost_daily_utilization_percent",
            description="Percentage of daily threshold used",
            unit="%",
            callbacks=[self._observe_daily_utilization],
        )

        # Monthly utilization percentage gauge
        meter.create_observable_gauge(
            name="platform_cost_monthly_utilization_percent",
            description="Percentage of monthly threshold used",
            unit="%",
            callbacks=[self._observe_monthly_utilization],
        )

        # Per-type cost gauge (with cost_type label)
        meter.create_observable_gauge(
            name="platform_cost_by_type_usd",
            description="Daily cost breakdown by cost type",
            unit="usd",
            callbacks=[self._observe_by_type],
        )

    def _observe_daily_total(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for daily total."""
        return [metrics.Observation(float(self._daily_total))]

    def _observe_monthly_total(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for monthly total."""
        return [metrics.Observation(float(self._monthly_total))]

    def _observe_daily_threshold(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for daily threshold."""
        return [metrics.Observation(float(self._daily_threshold))]

    def _observe_monthly_threshold(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for monthly threshold."""
        return [metrics.Observation(float(self._monthly_threshold))]

    def _observe_daily_utilization(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for daily utilization percentage."""
        utilization = float(self._daily_total / self._daily_threshold * 100) if self._daily_threshold > 0 else 0.0
        return [metrics.Observation(utilization)]

    def _observe_monthly_utilization(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for monthly utilization percentage."""
        utilization = float(self._monthly_total / self._monthly_threshold * 100) if self._monthly_threshold > 0 else 0.0
        return [metrics.Observation(utilization)]

    def _observe_by_type(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for per-type costs."""
        observations = []
        for cost_type, amount in self._daily_by_type.items():
            observations.append(metrics.Observation(float(amount), {"cost_type": cost_type}))
        return observations

    def _check_reset(self, now: datetime) -> None:
        """Check if period has changed and reset counters if needed.

        Args:
            now: Current timestamp.
        """
        today = now.date()
        current_month = (now.year, now.month)

        # Check daily reset
        if self._current_day != today:
            if self._current_day is not None:
                logger.info(
                    "Daily period reset",
                    previous_day=self._current_day.isoformat(),
                    previous_total=str(self._daily_total),
                )
            self._current_day = today
            self._daily_total = Decimal("0")
            self._daily_by_type = {}
            self._daily_alert_triggered = False

        # Check monthly reset
        if self._current_month != current_month:
            if self._current_month is not None:
                logger.info(
                    "Monthly period reset",
                    previous_month=f"{self._current_month[0]}-{self._current_month[1]:02d}",
                    previous_total=str(self._monthly_total),
                )
            self._current_month = current_month
            self._monthly_total = Decimal("0")
            self._monthly_alert_triggered = False

    def record_cost(
        self,
        cost_type: str,
        amount_usd: Decimal,
        timestamp: datetime | None = None,
    ) -> ThresholdType | None:
        """Record a cost and check for threshold breaches.

        Args:
            cost_type: Type of cost (llm, document, embedding, sms).
            amount_usd: Cost amount in USD.
            timestamp: When the cost was incurred. Defaults to now.

        Returns:
            ThresholdType if a threshold was exceeded (first time), None otherwise.
        """
        now = timestamp or datetime.now(UTC)
        self._check_reset(now)

        # Update totals
        self._daily_total += amount_usd
        self._monthly_total += amount_usd

        # Update per-type total
        if cost_type not in self._daily_by_type:
            self._daily_by_type[cost_type] = Decimal("0")
        self._daily_by_type[cost_type] += amount_usd

        # Increment event counter
        self._event_counter.add(1, {"cost_type": cost_type})

        logger.debug(
            "Cost recorded",
            cost_type=cost_type,
            amount_usd=str(amount_usd),
            daily_total=str(self._daily_total),
            monthly_total=str(self._monthly_total),
        )

        # Check daily threshold
        if self._daily_threshold > 0 and self._daily_total >= self._daily_threshold and not self._daily_alert_triggered:
            self._daily_alert_triggered = True
            logger.warning(
                "Daily cost threshold exceeded",
                threshold_usd=str(self._daily_threshold),
                current_cost_usd=str(self._daily_total),
            )
            return ThresholdType.DAILY

        # Check monthly threshold
        if (
            self._monthly_threshold > 0
            and self._monthly_total >= self._monthly_threshold
            and not self._monthly_alert_triggered
        ):
            self._monthly_alert_triggered = True
            logger.warning(
                "Monthly cost threshold exceeded",
                threshold_usd=str(self._monthly_threshold),
                current_cost_usd=str(self._monthly_total),
            )
            return ThresholdType.MONTHLY

        return None

    def get_status(self) -> BudgetStatus:
        """Get current budget monitoring status.

        Returns:
            BudgetStatus with current totals and thresholds.
        """
        # Calculate utilization percentages
        daily_utilization = float(self._daily_total / self._daily_threshold * 100) if self._daily_threshold > 0 else 0.0
        monthly_utilization = (
            float(self._monthly_total / self._monthly_threshold * 100) if self._monthly_threshold > 0 else 0.0
        )

        # Build by_type dict with string values
        by_type = {cost_type: str(amount) for cost_type, amount in self._daily_by_type.items()}

        return BudgetStatus(
            daily_threshold_usd=str(self._daily_threshold),
            daily_total_usd=str(self._daily_total),
            daily_alert_triggered=self._daily_alert_triggered,
            daily_remaining_usd=str(max(Decimal("0"), self._daily_threshold - self._daily_total)),
            daily_utilization_percent=round(daily_utilization, 2),
            monthly_threshold_usd=str(self._monthly_threshold),
            monthly_total_usd=str(self._monthly_total),
            monthly_alert_triggered=self._monthly_alert_triggered,
            monthly_remaining_usd=str(max(Decimal("0"), self._monthly_threshold - self._monthly_total)),
            monthly_utilization_percent=round(monthly_utilization, 2),
            by_type=by_type,
            current_day=self._current_day.isoformat() if self._current_day else None,
            current_month=(f"{self._current_month[0]}-{self._current_month[1]:02d}" if self._current_month else None),
        )

    async def warm_up_from_repository(self, cost_repository: "UnifiedCostRepository") -> None:
        """Warm up from MongoDB on startup.

        Restores daily and monthly totals from the database so that
        metrics are accurate after a service restart. Sets alert state
        based on restored totals.

        CRITICAL: This method MUST succeed for the service to start.
        If the query fails, the service should fail-fast rather than
        report incorrect zero totals.

        Args:
            cost_repository: The cost repository to query.

        Raises:
            Exception: If warm-up query fails (fail-fast behavior).
        """
        logger.info("Starting BudgetMonitor warm-up from MongoDB")

        try:
            # Get current day cost
            current_day_cost = await cost_repository.get_current_day_cost()
            self._daily_total = current_day_cost.total_cost_usd
            self._daily_by_type = dict(current_day_cost.by_type.items())
            self._current_day = current_day_cost.cost_date

            # Get current month cost
            self._monthly_total = await cost_repository.get_current_month_cost()
            today = date.today()
            self._current_month = (today.year, today.month)

            # Set alert state based on restored totals
            if self._daily_threshold > 0 and self._daily_total >= self._daily_threshold:
                self._daily_alert_triggered = True
                logger.info(
                    "Daily alert state restored (already exceeded)",
                    threshold_usd=str(self._daily_threshold),
                    current_cost_usd=str(self._daily_total),
                )

            if self._monthly_threshold > 0 and self._monthly_total >= self._monthly_threshold:
                self._monthly_alert_triggered = True
                logger.info(
                    "Monthly alert state restored (already exceeded)",
                    threshold_usd=str(self._monthly_threshold),
                    current_cost_usd=str(self._monthly_total),
                )

            logger.info(
                "BudgetMonitor warm-up complete",
                daily_total_usd=str(self._daily_total),
                monthly_total_usd=str(self._monthly_total),
                daily_alert_triggered=self._daily_alert_triggered,
                monthly_alert_triggered=self._monthly_alert_triggered,
            )

        except Exception as e:
            logger.error(
                "Failed to warm up BudgetMonitor from MongoDB",
                error=str(e),
            )
            # Re-raise to fail-fast - better to be down than report wrong metrics
            raise

    def update_thresholds(
        self,
        daily_threshold_usd: float | None = None,
        monthly_threshold_usd: float | None = None,
    ) -> None:
        """Update cost thresholds at runtime.

        If the new threshold is higher than the current total, resets
        the alert state to allow re-triggering.

        Args:
            daily_threshold_usd: New daily threshold (None = keep current).
            monthly_threshold_usd: New monthly threshold (None = keep current).
        """
        if daily_threshold_usd is not None:
            self._daily_threshold = Decimal(str(daily_threshold_usd))
            # Reset alert if new threshold is higher than current total
            if self._daily_total < self._daily_threshold:
                self._daily_alert_triggered = False
            logger.info(
                "Daily threshold updated",
                new_threshold_usd=str(self._daily_threshold),
                alert_reset=not self._daily_alert_triggered,
            )

        if monthly_threshold_usd is not None:
            self._monthly_threshold = Decimal(str(monthly_threshold_usd))
            # Reset alert if new threshold is higher than current total
            if self._monthly_total < self._monthly_threshold:
                self._monthly_alert_triggered = False
            logger.info(
                "Monthly threshold updated",
                new_threshold_usd=str(self._monthly_threshold),
                alert_reset=not self._monthly_alert_triggered,
            )

    def reset_totals(self) -> None:
        """Reset all running totals and alert states.

        This is primarily useful for testing.
        """
        self._daily_total = Decimal("0")
        self._monthly_total = Decimal("0")
        self._daily_by_type = {}
        self._current_day = None
        self._current_month = None
        self._daily_alert_triggered = False
        self._monthly_alert_triggered = False
        logger.info("Budget monitor totals reset")
