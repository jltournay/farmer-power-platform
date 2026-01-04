"""Budget monitoring for LLM cost thresholds.

This module provides the BudgetMonitor class for tracking running cost totals
and triggering alerts when daily or monthly thresholds are exceeded.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

import structlog
from ai_model.domain.cost_event import LlmCostEvent
from opentelemetry import metrics

logger = structlog.get_logger(__name__)

# OpenTelemetry metrics
meter = metrics.get_meter(__name__)
llm_daily_cost_gauge = meter.create_observable_gauge(
    name="llm_daily_cost_usd",
    description="Current daily LLM cost in USD",
    unit="usd",
)
llm_monthly_cost_gauge = meter.create_observable_gauge(
    name="llm_monthly_cost_usd",
    description="Current monthly LLM cost in USD",
    unit="usd",
)
llm_cost_alert_counter = meter.create_counter(
    name="llm_cost_alert_triggered",
    description="Number of cost threshold alerts triggered",
    unit="1",
)


class ThresholdType(str, Enum):
    """Types of cost thresholds."""

    DAILY = "daily"
    MONTHLY = "monthly"


@dataclass
class CostAlert:
    """Alert triggered when a cost threshold is exceeded."""

    threshold_type: ThresholdType
    threshold_usd: Decimal
    current_cost_usd: Decimal
    triggered_at: datetime
    event_id: str  # The cost event that triggered the alert

    @property
    def overage_usd(self) -> Decimal:
        """Return the amount over the threshold."""
        return self.current_cost_usd - self.threshold_usd


class BudgetMonitor:
    """Monitor for LLM cost thresholds with alert generation.

    Tracks running daily and monthly costs and triggers alerts when
    thresholds are exceeded. Alerts are only triggered once per threshold
    per period (day or month) to prevent alert fatigue.

    Example:
        ```python
        monitor = BudgetMonitor(
            daily_threshold_usd=10.0,
            monthly_threshold_usd=100.0,
        )

        # After each LLM call
        alert = await monitor.record_cost(cost_event)
        if alert:
            # Handle threshold breach
            await publish_alert_event(alert)
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

        # Current tracking period
        self._current_day: date | None = None
        self._current_month: tuple[int, int] | None = None  # (year, month)

        # Alert state - only trigger once per period
        self._daily_alert_triggered = False
        self._monthly_alert_triggered = False

        # Register observable gauges
        llm_daily_cost_gauge.callback = self._observe_daily_cost
        llm_monthly_cost_gauge.callback = self._observe_monthly_cost

        logger.info(
            "Budget monitor initialized",
            daily_threshold_usd=str(self._daily_threshold),
            monthly_threshold_usd=str(self._monthly_threshold),
        )

    def _observe_daily_cost(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for daily cost."""
        return [metrics.Observation(float(self._daily_total))]

    def _observe_monthly_cost(self, options: metrics.CallbackOptions) -> list[metrics.Observation]:
        """Observable gauge callback for monthly cost."""
        return [metrics.Observation(float(self._monthly_total))]

    def _check_period_reset(self, now: datetime) -> None:
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

    async def record_cost(self, event: LlmCostEvent) -> CostAlert | None:
        """Record a cost event and check for threshold breaches.

        Args:
            event: The cost event to record.

        Returns:
            CostAlert if a threshold was exceeded, None otherwise.
        """
        now = event.timestamp or datetime.now(UTC)
        self._check_period_reset(now)

        # Add cost to running totals
        self._daily_total += event.cost_usd
        self._monthly_total += event.cost_usd

        logger.debug(
            "Cost recorded",
            event_id=event.id,
            cost_usd=str(event.cost_usd),
            daily_total=str(self._daily_total),
            monthly_total=str(self._monthly_total),
        )

        # Check daily threshold
        if self._daily_threshold > 0 and self._daily_total >= self._daily_threshold and not self._daily_alert_triggered:
            self._daily_alert_triggered = True
            llm_cost_alert_counter.add(1, {"threshold_type": "daily"})
            alert = CostAlert(
                threshold_type=ThresholdType.DAILY,
                threshold_usd=self._daily_threshold,
                current_cost_usd=self._daily_total,
                triggered_at=now,
                event_id=event.id,
            )
            logger.warning(
                "Daily cost threshold exceeded",
                threshold_usd=str(self._daily_threshold),
                current_cost_usd=str(self._daily_total),
                overage_usd=str(alert.overage_usd),
            )
            return alert

        # Check monthly threshold
        if (
            self._monthly_threshold > 0
            and self._monthly_total >= self._monthly_threshold
            and not self._monthly_alert_triggered
        ):
            self._monthly_alert_triggered = True
            llm_cost_alert_counter.add(1, {"threshold_type": "monthly"})
            alert = CostAlert(
                threshold_type=ThresholdType.MONTHLY,
                threshold_usd=self._monthly_threshold,
                current_cost_usd=self._monthly_total,
                triggered_at=now,
                event_id=event.id,
            )
            logger.warning(
                "Monthly cost threshold exceeded",
                threshold_usd=str(self._monthly_threshold),
                current_cost_usd=str(self._monthly_total),
                overage_usd=str(alert.overage_usd),
            )
            return alert

        return None

    def get_status(self) -> dict:
        """Get current budget monitoring status.

        Returns:
            Dictionary with current totals and thresholds.
        """
        return {
            "daily_threshold_usd": str(self._daily_threshold),
            "daily_total_usd": str(self._daily_total),
            "daily_alert_triggered": self._daily_alert_triggered,
            "daily_remaining_usd": str(max(Decimal("0"), self._daily_threshold - self._daily_total)),
            "monthly_threshold_usd": str(self._monthly_threshold),
            "monthly_total_usd": str(self._monthly_total),
            "monthly_alert_triggered": self._monthly_alert_triggered,
            "monthly_remaining_usd": str(max(Decimal("0"), self._monthly_threshold - self._monthly_total)),
            "current_day": self._current_day.isoformat() if self._current_day else None,
            "current_month": (
                f"{self._current_month[0]}-{self._current_month[1]:02d}" if self._current_month else None
            ),
        }

    def update_thresholds(
        self,
        daily_threshold_usd: float | None = None,
        monthly_threshold_usd: float | None = None,
    ) -> None:
        """Update cost thresholds at runtime.

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
            )

        if monthly_threshold_usd is not None:
            self._monthly_threshold = Decimal(str(monthly_threshold_usd))
            # Reset alert if new threshold is higher than current total
            if self._monthly_total < self._monthly_threshold:
                self._monthly_alert_triggered = False
            logger.info(
                "Monthly threshold updated",
                new_threshold_usd=str(self._monthly_threshold),
            )

    def reset_totals(self) -> None:
        """Reset all running totals and alert states.

        This is primarily useful for testing.
        """
        self._daily_total = Decimal("0")
        self._monthly_total = Decimal("0")
        self._current_day = None
        self._current_month = None
        self._daily_alert_triggered = False
        self._monthly_alert_triggered = False
        logger.info("Budget monitor totals reset")
