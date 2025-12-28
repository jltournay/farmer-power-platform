"""Flush period calculator service (Story 1.8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plantation_model.domain.models.value_objects import FlushCalendar, FlushPeriod


@dataclass
class FlushResult:
    """Result of flush period calculation."""

    name: str
    period: FlushPeriod
    days_remaining: int


class FlushCalculator:
    """Calculator for determining current flush period from a flush calendar.

    Handles year-spanning periods (e.g., dormant period from Dec 16 to Mar 14).
    """

    def get_current_flush(
        self,
        flush_calendar: FlushCalendar,
        current_date: date | None = None,
    ) -> FlushResult | None:
        """Determine the current flush period based on date.

        Args:
            flush_calendar: The flush calendar to check against.
            current_date: The date to check (defaults to today).

        Returns:
            FlushResult with name, period, and days remaining, or None if no match.
        """
        if current_date is None:
            current_date = date.today()

        month_day = current_date.strftime("%m-%d")

        # Check each flush period
        flush_periods = [
            ("first_flush", flush_calendar.first_flush),
            ("monsoon_flush", flush_calendar.monsoon_flush),
            ("autumn_flush", flush_calendar.autumn_flush),
            ("dormant", flush_calendar.dormant),
        ]

        for flush_name, period in flush_periods:
            if self._is_date_in_period(month_day, period.start, period.end):
                days_remaining = self._calculate_days_remaining(current_date, period.end)
                return FlushResult(
                    name=flush_name,
                    period=period,
                    days_remaining=days_remaining,
                )

        return None

    def _is_date_in_period(self, month_day: str, start: str, end: str) -> bool:
        """Check if a month-day falls within a period.

        Args:
            month_day: The date to check in MM-DD format.
            start: Period start in MM-DD format.
            end: Period end in MM-DD format.

        Returns:
            True if the date falls within the period.
        """
        # Handle year-spanning period (e.g., "12-16" to "03-14")
        if start > end:
            # Period spans year boundary
            return month_day >= start or month_day <= end
        else:
            # Normal period within same year
            return start <= month_day <= end

    def _calculate_days_remaining(self, current_date: date, end_mm_dd: str) -> int:
        """Calculate days remaining until period end.

        Args:
            current_date: The current date.
            end_mm_dd: Period end in MM-DD format.

        Returns:
            Number of days until period ends.
        """
        end_month, end_day = int(end_mm_dd[:2]), int(end_mm_dd[3:])

        # Build end date - try current year first
        try:
            end_date = date(current_date.year, end_month, end_day)
        except ValueError:
            # Handle Feb 29 on non-leap year
            end_date = date(current_date.year, end_month, 28)

        # If end date is before current date, it's in the next year
        if end_date < current_date:
            try:
                end_date = date(current_date.year + 1, end_month, end_day)
            except ValueError:
                end_date = date(current_date.year + 1, end_month, 28)

        return (end_date - current_date).days

    def get_next_flush(
        self,
        flush_calendar: FlushCalendar,
        current_date: date | None = None,
    ) -> FlushResult | None:
        """Get the next upcoming flush period.

        Args:
            flush_calendar: The flush calendar to check against.
            current_date: The date to check from (defaults to today).

        Returns:
            FlushResult for the next flush period, or None.
        """
        if current_date is None:
            current_date = date.today()

        current_flush = self.get_current_flush(flush_calendar, current_date)
        if current_flush is None:
            return None

        # Define flush order
        flush_order = ["first_flush", "monsoon_flush", "autumn_flush", "dormant"]

        # Find current position and get next
        try:
            current_idx = flush_order.index(current_flush.name)
        except ValueError:
            return None

        next_idx = (current_idx + 1) % len(flush_order)
        next_flush_name = flush_order[next_idx]

        flush_periods = {
            "first_flush": flush_calendar.first_flush,
            "monsoon_flush": flush_calendar.monsoon_flush,
            "autumn_flush": flush_calendar.autumn_flush,
            "dormant": flush_calendar.dormant,
        }

        next_period = flush_periods[next_flush_name]

        # Calculate days until next flush starts
        start_month, start_day = int(next_period.start[:2]), int(next_period.start[3:])
        try:
            start_date = date(current_date.year, start_month, start_day)
        except ValueError:
            start_date = date(current_date.year, start_month, 28)

        if start_date <= current_date:
            try:
                start_date = date(current_date.year + 1, start_month, start_day)
            except ValueError:
                start_date = date(current_date.year + 1, start_month, 28)

        days_until = (start_date - current_date).days

        return FlushResult(
            name=next_flush_name,
            period=next_period,
            days_remaining=days_until,
        )
