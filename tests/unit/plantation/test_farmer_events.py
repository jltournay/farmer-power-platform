"""Unit tests for Farmer domain events.

Story 9.5a: collection_point_id and factory_id removed from FarmerRegisteredEvent.
"""

from datetime import UTC, datetime

from plantation_model.domain.events.farmer_events import FarmerRegisteredEvent


class TestFarmerRegisteredEvent:
    """Tests for FarmerRegisteredEvent model.

    Story 9.5a: collection_point_id and factory_id removed - farmers assigned via separate API.
    """

    def test_event_creation_with_all_fields(self) -> None:
        """Test creating FarmerRegisteredEvent with all required fields."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        assert event.farmer_id == "WM-0001"
        assert event.phone == "+254712345678"
        # Story 9.5a: collection_point_id and factory_id removed
        assert event.region_id == "nyeri-highland"
        assert event.farm_scale == "medium"

    def test_event_has_default_event_type(self) -> None:
        """Test FarmerRegisteredEvent has correct default event_type."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        assert event.event_type == "plantation.farmer.registered"

    def test_event_has_auto_timestamp(self) -> None:
        """Test FarmerRegisteredEvent auto-generates timestamp."""
        before = datetime.now(UTC)

        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        after = datetime.now(UTC)

        assert event.timestamp is not None
        assert before <= event.timestamp <= after

    def test_event_serialization_json(self) -> None:
        """Test FarmerRegisteredEvent serializes to JSON correctly."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        data = event.model_dump(mode="json")

        assert data["event_type"] == "plantation.farmer.registered"
        assert data["farmer_id"] == "WM-0001"
        assert data["phone"] == "+254712345678"
        assert "timestamp" in data

    def test_event_farm_scale_values(self) -> None:
        """Test FarmerRegisteredEvent accepts valid farm_scale values."""
        for scale in ["smallholder", "medium", "estate"]:
            event = FarmerRegisteredEvent(
                farmer_id="WM-0001",
                phone="+254712345678",
                region_id="test-region",
                farm_scale=scale,
            )
            assert event.farm_scale == scale
