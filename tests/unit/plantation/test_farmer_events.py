"""Unit tests for Farmer domain events."""

from datetime import UTC, datetime

from plantation_model.domain.events.farmer_events import (
    FarmerDeactivatedEvent,
    FarmerRegisteredEvent,
    FarmerUpdatedEvent,
)


class TestFarmerRegisteredEvent:
    """Tests for FarmerRegisteredEvent model."""

    def test_event_creation_with_all_fields(self) -> None:
        """Test creating FarmerRegisteredEvent with all required fields."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        assert event.farmer_id == "WM-0001"
        assert event.phone == "+254712345678"
        assert event.collection_point_id == "nyeri-highland-cp-001"
        assert event.factory_id == "KEN-FAC-001"
        assert event.region_id == "nyeri-highland"
        assert event.farm_scale == "medium"

    def test_event_has_default_event_type(self) -> None:
        """Test FarmerRegisteredEvent has correct default event_type."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
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
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
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
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
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
                collection_point_id="test-cp",
                factory_id="KEN-FAC-001",
                region_id="test-region",
                farm_scale=scale,
            )
            assert event.farm_scale == scale


class TestFarmerUpdatedEvent:
    """Tests for FarmerUpdatedEvent model."""

    def test_event_creation_with_updated_fields(self) -> None:
        """Test creating FarmerUpdatedEvent with updated_fields."""
        event = FarmerUpdatedEvent(
            farmer_id="WM-0001",
            updated_fields=["first_name", "phone"],
        )

        assert event.farmer_id == "WM-0001"
        assert event.updated_fields == ["first_name", "phone"]

    def test_event_has_default_event_type(self) -> None:
        """Test FarmerUpdatedEvent has correct default event_type."""
        event = FarmerUpdatedEvent(
            farmer_id="WM-0001",
            updated_fields=["first_name"],
        )

        assert event.event_type == "plantation.farmer.updated"

    def test_event_has_auto_timestamp(self) -> None:
        """Test FarmerUpdatedEvent auto-generates timestamp."""
        event = FarmerUpdatedEvent(
            farmer_id="WM-0001",
            updated_fields=["first_name"],
        )

        assert event.timestamp is not None
        assert event.timestamp.tzinfo is not None  # Timezone-aware

    def test_event_empty_updated_fields(self) -> None:
        """Test FarmerUpdatedEvent with empty updated_fields list."""
        event = FarmerUpdatedEvent(
            farmer_id="WM-0001",
            updated_fields=[],
        )

        assert event.updated_fields == []

    def test_event_serialization_json(self) -> None:
        """Test FarmerUpdatedEvent serializes to JSON correctly."""
        event = FarmerUpdatedEvent(
            farmer_id="WM-0001",
            updated_fields=["phone", "farm_size_hectares"],
        )

        data = event.model_dump(mode="json")

        assert data["event_type"] == "plantation.farmer.updated"
        assert data["farmer_id"] == "WM-0001"
        assert data["updated_fields"] == ["phone", "farm_size_hectares"]


class TestFarmerDeactivatedEvent:
    """Tests for FarmerDeactivatedEvent model."""

    def test_event_creation_with_reason(self) -> None:
        """Test creating FarmerDeactivatedEvent with reason."""
        event = FarmerDeactivatedEvent(
            farmer_id="WM-0001",
            reason="Farmer relocated outside service area",
        )

        assert event.farmer_id == "WM-0001"
        assert event.reason == "Farmer relocated outside service area"

    def test_event_has_default_event_type(self) -> None:
        """Test FarmerDeactivatedEvent has correct default event_type."""
        event = FarmerDeactivatedEvent(
            farmer_id="WM-0001",
            reason="Test",
        )

        assert event.event_type == "plantation.farmer.deactivated"

    def test_event_has_auto_timestamp(self) -> None:
        """Test FarmerDeactivatedEvent auto-generates timestamp."""
        event = FarmerDeactivatedEvent(
            farmer_id="WM-0001",
        )

        assert event.timestamp is not None

    def test_event_default_empty_reason(self) -> None:
        """Test FarmerDeactivatedEvent has default empty reason."""
        event = FarmerDeactivatedEvent(
            farmer_id="WM-0001",
        )

        assert event.reason == ""

    def test_event_serialization_json(self) -> None:
        """Test FarmerDeactivatedEvent serializes to JSON correctly."""
        event = FarmerDeactivatedEvent(
            farmer_id="WM-0001",
            reason="Inactive for 12 months",
        )

        data = event.model_dump(mode="json")

        assert data["event_type"] == "plantation.farmer.deactivated"
        assert data["farmer_id"] == "WM-0001"
        assert data["reason"] == "Inactive for 12 months"
