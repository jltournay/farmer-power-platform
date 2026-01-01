"""Unit tests for Flush model.

Story 0.6.1: Shared Pydantic Models in fp-common
"""

import pytest
from fp_common.models import Flush, FlushPeriod
from pydantic import ValidationError


class TestFlush:
    """Tests for Flush model."""

    def test_create_valid_flush(self) -> None:
        """Test creating a valid Flush."""
        period = FlushPeriod(
            start="03-15",
            end="05-15",
            characteristics="Highest quality, delicate flavor",
        )

        flush = Flush(
            name="first_flush",
            period=period,
            days_remaining=45,
            characteristics="Highest quality, delicate flavor",
        )

        assert flush.name == "first_flush"
        assert flush.period.start == "03-15"
        assert flush.period.end == "05-15"
        assert flush.days_remaining == 45
        assert flush.characteristics == "Highest quality, delicate flavor"

    def test_flush_from_period(self) -> None:
        """Test creating Flush using from_period class method."""
        period = FlushPeriod(
            start="06-15",
            end="09-30",
            characteristics="High volume, robust flavor",
        )

        flush = Flush.from_period(
            name="monsoon_flush",
            period=period,
            days_remaining=30,
        )

        assert flush.name == "monsoon_flush"
        assert flush.period == period
        assert flush.days_remaining == 30
        # characteristics should be copied from period
        assert flush.characteristics == "High volume, robust flavor"

    def test_flush_all_periods(self) -> None:
        """Test creating Flush for all flush period types."""
        flush_periods = [
            ("first_flush", "03-15", "05-15", "Highest quality"),
            ("monsoon_flush", "06-15", "09-30", "High volume"),
            ("autumn_flush", "10-15", "12-15", "Balanced quality"),
            ("dormant", "12-16", "03-14", "Minimal growth"),
        ]

        for name, start, end, desc in flush_periods:
            period = FlushPeriod(start=start, end=end, characteristics=desc)
            flush = Flush(
                name=name,
                period=period,
                days_remaining=10,
                characteristics=desc,
            )

            assert flush.name == name
            assert flush.period.start == start
            assert flush.period.end == end

    def test_days_remaining_must_be_non_negative(self) -> None:
        """Test that days_remaining must be >= 0."""
        period = FlushPeriod(start="03-15", end="05-15")

        with pytest.raises(ValidationError):
            Flush(
                name="first_flush",
                period=period,
                days_remaining=-1,  # Invalid
            )

    def test_flush_serialization(self) -> None:
        """Test Flush serialization to dict."""
        period = FlushPeriod(
            start="03-15",
            end="05-15",
            characteristics="Highest quality",
        )

        flush = Flush(
            name="first_flush",
            period=period,
            days_remaining=45,
            characteristics="Highest quality",
        )

        data = flush.model_dump()

        assert data["name"] == "first_flush"
        assert data["days_remaining"] == 45
        assert "period" in data
        assert data["period"]["start"] == "03-15"
        assert data["period"]["end"] == "05-15"

    def test_flush_characteristics_defaults_to_empty(self) -> None:
        """Test that characteristics defaults to empty string."""
        period = FlushPeriod(start="03-15", end="05-15")

        flush = Flush(
            name="test_flush",
            period=period,
            days_remaining=10,
        )

        assert flush.characteristics == ""
