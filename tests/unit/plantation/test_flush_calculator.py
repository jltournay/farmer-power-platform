"""Unit tests for FlushCalculator (Story 1.8)."""

from datetime import date

import pytest
from plantation_model.domain.models.value_objects import FlushCalendar, FlushPeriod
from plantation_model.domain.services.flush_calculator import FlushCalculator


def create_test_flush_calendar() -> FlushCalendar:
    """Create a standard test flush calendar."""
    return FlushCalendar(
        first_flush=FlushPeriod(
            start="03-15",
            end="05-15",
            characteristics="Highest quality, delicate flavor",
        ),
        monsoon_flush=FlushPeriod(
            start="06-15",
            end="09-30",
            characteristics="High volume, robust flavor",
        ),
        autumn_flush=FlushPeriod(
            start="10-15",
            end="12-15",
            characteristics="Balanced quality",
        ),
        dormant=FlushPeriod(
            start="12-16",
            end="03-14",
            characteristics="Minimal growth",
        ),
    )


class TestFlushCalculator:
    """Tests for FlushCalculator."""

    def test_get_current_flush_first_flush(self) -> None:
        """Test getting current flush during first flush period."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar, date(2025, 4, 1))

        assert result is not None
        assert result.name == "first_flush"
        assert result.period.start == "03-15"
        assert result.period.end == "05-15"
        assert result.days_remaining == 44  # Apr 1 to May 15

    def test_get_current_flush_monsoon_flush(self) -> None:
        """Test getting current flush during monsoon flush period."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar, date(2025, 7, 15))

        assert result is not None
        assert result.name == "monsoon_flush"
        assert result.period.characteristics == "High volume, robust flavor"

    def test_get_current_flush_autumn_flush(self) -> None:
        """Test getting current flush during autumn flush period."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar, date(2025, 11, 1))

        assert result is not None
        assert result.name == "autumn_flush"
        assert result.period.characteristics == "Balanced quality"

    def test_get_current_flush_dormant_before_year_end(self) -> None:
        """Test getting current flush during dormant period before year end."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        # December 28 should be in dormant period
        result = calculator.get_current_flush(calendar, date(2025, 12, 28))

        assert result is not None
        assert result.name == "dormant"
        assert result.period.characteristics == "Minimal growth"

    def test_get_current_flush_dormant_after_year_start(self) -> None:
        """Test getting current flush during dormant period after year start."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        # January 15 should still be in dormant period (ends Mar 14)
        result = calculator.get_current_flush(calendar, date(2025, 1, 15))

        assert result is not None
        assert result.name == "dormant"

    def test_get_current_flush_at_period_start(self) -> None:
        """Test getting current flush on first day of period."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar, date(2025, 3, 15))

        assert result is not None
        assert result.name == "first_flush"

    def test_get_current_flush_at_period_end(self) -> None:
        """Test getting current flush on last day of period."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar, date(2025, 5, 15))

        assert result is not None
        assert result.name == "first_flush"

    def test_days_remaining_calculation(self) -> None:
        """Test days remaining is calculated correctly."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        # May 10 during first_flush (ends May 15)
        result = calculator.get_current_flush(calendar, date(2025, 5, 10))

        assert result is not None
        assert result.days_remaining == 5

    def test_days_remaining_spans_year(self) -> None:
        """Test days remaining calculation when period spans year end."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        # December 20 during dormant (ends Mar 14 of next year)
        result = calculator.get_current_flush(calendar, date(2025, 12, 20))

        assert result is not None
        assert result.name == "dormant"
        # Dec 20 to Mar 14: 11 (Dec) + 31 (Jan) + 28 (Feb) + 14 (Mar) = 84 days
        assert result.days_remaining == 84

    def test_get_current_flush_uses_today_by_default(self) -> None:
        """Test that get_current_flush defaults to today's date."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_current_flush(calendar)

        # Should return a result (today is always in some period with valid calendar)
        assert result is not None
        assert result.name in ["first_flush", "monsoon_flush", "autumn_flush", "dormant"]

    def test_get_next_flush_from_first_flush(self) -> None:
        """Test getting next flush when in first flush."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_next_flush(calendar, date(2025, 4, 1))

        assert result is not None
        assert result.name == "monsoon_flush"

    def test_get_next_flush_from_dormant(self) -> None:
        """Test getting next flush when in dormant (wraps to first_flush)."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        result = calculator.get_next_flush(calendar, date(2025, 1, 15))

        assert result is not None
        assert result.name == "first_flush"


class TestFlushCalculatorEdgeCases:
    """Edge case tests for FlushCalculator."""

    def test_leap_year_handling(self) -> None:
        """Test handling of leap year dates."""
        calculator = FlushCalculator()
        calendar = create_test_flush_calendar()

        # Feb 29 of a leap year (2024 was a leap year)
        result = calculator.get_current_flush(calendar, date(2024, 2, 29))

        assert result is not None
        assert result.name == "dormant"

    def test_gap_between_periods(self) -> None:
        """Test date in gap between defined periods returns None.

        Note: With a properly configured calendar, there should be no gaps.
        This test uses a calendar with intentional gaps.
        """
        # Create calendar with gap between periods
        gapped_calendar = FlushCalendar(
            first_flush=FlushPeriod(start="03-15", end="05-15", characteristics=""),
            monsoon_flush=FlushPeriod(start="07-01", end="09-30", characteristics=""),  # Gap in June
            autumn_flush=FlushPeriod(start="10-15", end="12-15", characteristics=""),
            dormant=FlushPeriod(start="12-16", end="03-14", characteristics=""),
        )

        calculator = FlushCalculator()
        result = calculator.get_current_flush(gapped_calendar, date(2025, 6, 15))

        # June 15 is not in any period
        assert result is None
