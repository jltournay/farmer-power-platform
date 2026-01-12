"""Unit tests for ThresholdRepository.

Story 13.3: Cost Repository and Budget Monitor

Tests:
- Threshold configuration persistence
- Partial updates
- Upsert behavior
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from platform_cost.infrastructure.repositories.threshold_repository import (
    COLLECTION_NAME,
    THRESHOLD_CONFIG_ID,
    ThresholdConfig,
    ThresholdRepository,
)


@pytest.fixture
def mock_db(mock_mongodb_client):
    """Get mock MongoDB database."""
    return mock_mongodb_client["platform_cost"]


@pytest.fixture
def threshold_repository(mock_db):
    """Create ThresholdRepository with mock database."""
    return ThresholdRepository(db=mock_db)


class TestThresholdConfig:
    """Tests for ThresholdConfig model."""

    def test_defaults_to_zero(self) -> None:
        """Test that thresholds default to zero (disabled)."""
        config = ThresholdConfig()

        assert config.daily_threshold_usd == Decimal("0")
        assert config.monthly_threshold_usd == Decimal("0")
        assert config.updated_by == "system"

    def test_accepts_decimal_values(self) -> None:
        """Test that config accepts Decimal values."""
        config = ThresholdConfig(
            daily_threshold_usd=Decimal("10.50"),
            monthly_threshold_usd=Decimal("100.00"),
        )

        assert config.daily_threshold_usd == Decimal("10.50")
        assert config.monthly_threshold_usd == Decimal("100.00")


class TestGetThresholds:
    """Tests for get_thresholds method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_config(self, threshold_repository) -> None:
        """Test that get_thresholds returns None when no config exists."""
        config = await threshold_repository.get_thresholds()
        assert config is None

    @pytest.mark.asyncio
    async def test_returns_config_when_exists(self, threshold_repository, mock_db) -> None:
        """Test that get_thresholds returns stored config."""
        # Pre-insert config
        collection = mock_db[COLLECTION_NAME]
        await collection.insert_one(
            {
                "_id": THRESHOLD_CONFIG_ID,
                "daily_threshold_usd": "10.00",
                "monthly_threshold_usd": "100.00",
                "updated_at": datetime.now(UTC),
                "updated_by": "test-user",
            }
        )

        config = await threshold_repository.get_thresholds()

        assert config is not None
        assert config.daily_threshold_usd == Decimal("10.00")
        assert config.monthly_threshold_usd == Decimal("100.00")
        assert config.updated_by == "test-user"


class TestSetThresholds:
    """Tests for set_thresholds method."""

    @pytest.mark.asyncio
    async def test_creates_config_if_not_exists(self, threshold_repository) -> None:
        """Test that set_thresholds creates config via upsert."""
        config = await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("15.00"),
            monthly_threshold_usd=Decimal("150.00"),
            updated_by="admin",
        )

        assert config.daily_threshold_usd == Decimal("15.00")
        assert config.monthly_threshold_usd == Decimal("150.00")
        assert config.updated_by == "admin"

    @pytest.mark.asyncio
    async def test_updates_existing_config(self, threshold_repository) -> None:
        """Test that set_thresholds updates existing config."""
        # Create initial config
        await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("10.00"),
            monthly_threshold_usd=Decimal("100.00"),
        )

        # Update config
        config = await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("20.00"),
            monthly_threshold_usd=Decimal("200.00"),
            updated_by="supervisor",
        )

        assert config.daily_threshold_usd == Decimal("20.00")
        assert config.monthly_threshold_usd == Decimal("200.00")
        assert config.updated_by == "supervisor"

    @pytest.mark.asyncio
    async def test_partial_update_keeps_existing_values(self, threshold_repository) -> None:
        """Test that partial update preserves unspecified values."""
        # Create initial config
        await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("10.00"),
            monthly_threshold_usd=Decimal("100.00"),
        )

        # Partial update - only daily
        config = await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("25.00"),
        )

        assert config.daily_threshold_usd == Decimal("25.00")
        assert config.monthly_threshold_usd == Decimal("100.00")  # Unchanged

    @pytest.mark.asyncio
    async def test_partial_update_monthly_only(self, threshold_repository) -> None:
        """Test partial update of monthly threshold only."""
        # Create initial config
        await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("10.00"),
            monthly_threshold_usd=Decimal("100.00"),
        )

        # Partial update - only monthly
        config = await threshold_repository.set_thresholds(
            monthly_threshold_usd=Decimal("250.00"),
        )

        assert config.daily_threshold_usd == Decimal("10.00")  # Unchanged
        assert config.monthly_threshold_usd == Decimal("250.00")

    @pytest.mark.asyncio
    async def test_sets_updated_at(self, threshold_repository) -> None:
        """Test that set_thresholds sets updated_at timestamp."""
        before = datetime.now(UTC)

        config = await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("10.00"),
        )

        after = datetime.now(UTC)

        assert config.updated_at >= before
        assert config.updated_at <= after

    @pytest.mark.asyncio
    async def test_persists_to_database(self, threshold_repository) -> None:
        """Test that changes are persisted to database."""
        # Set thresholds
        await threshold_repository.set_thresholds(
            daily_threshold_usd=Decimal("30.00"),
            monthly_threshold_usd=Decimal("300.00"),
        )

        # Read back from database
        config = await threshold_repository.get_thresholds()

        assert config is not None
        assert config.daily_threshold_usd == Decimal("30.00")
        assert config.monthly_threshold_usd == Decimal("300.00")
