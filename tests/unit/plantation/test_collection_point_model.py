"""Unit tests for CollectionPoint domain model."""

import pytest
from pydantic import ValidationError

from plantation_model.domain.models.collection_point import (
    CollectionPoint,
    CollectionPointCreate,
    CollectionPointUpdate,
)
from plantation_model.domain.models.value_objects import (
    CollectionPointCapacity,
    GeoLocation,
    OperatingHours,
)


class TestCollectionPoint:
    """Tests for CollectionPoint model validation."""

    def test_collection_point_creation_valid(self) -> None:
        """Test creating a valid collection point."""
        cp = CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Kamakwa Collection Point",
            factory_id="KEN-FAC-001",
            location=GeoLocation(
                latitude=-0.4150,
                longitude=36.9500,
                altitude_meters=1850.0,
            ),
            region_id="nyeri-highland",
            clerk_id="CLK-001",
            clerk_phone="+254712345679",
            operating_hours=OperatingHours(
                weekdays="06:00-10:00",
                weekends="07:00-09:00",
            ),
            collection_days=["mon", "wed", "fri", "sat"],
            capacity=CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="covered_shed",
                has_weighing_scale=True,
                has_qc_device=False,
            ),
            status="active",
        )

        assert cp.id == "nyeri-highland-cp-001"
        assert cp.name == "Kamakwa Collection Point"
        assert cp.factory_id == "KEN-FAC-001"
        assert cp.region_id == "nyeri-highland"
        assert cp.clerk_id == "CLK-001"
        assert cp.status == "active"
        assert len(cp.collection_days) == 4

    def test_collection_point_name_validation(self) -> None:
        """Test collection point name validation."""
        with pytest.raises(ValidationError):
            CollectionPoint(
                id="test-cp-001",
                name="",  # Empty name should fail
                factory_id="KEN-FAC-001",
                location=GeoLocation(latitude=0, longitude=0),
                region_id="test",
            )

    def test_collection_point_default_values(self) -> None:
        """Test collection point default values."""
        cp = CollectionPoint(
            id="test-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=0, longitude=0),
            region_id="test",
        )

        assert cp.clerk_id is None
        assert cp.clerk_phone is None
        assert cp.status == "active"
        assert cp.collection_days == ["mon", "wed", "fri", "sat"]
        assert cp.operating_hours.weekdays == "06:00-10:00"
        assert cp.operating_hours.weekends == "07:00-09:00"
        assert cp.capacity.max_daily_kg == 0
        assert cp.capacity.storage_type == "covered_shed"
        assert cp.capacity.has_weighing_scale is False
        assert cp.capacity.has_qc_device is False

    def test_collection_point_with_optional_clerk(self) -> None:
        """Test collection point with optional clerk info."""
        cp = CollectionPoint(
            id="test-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=0, longitude=0),
            region_id="test",
            clerk_id="CLK-123",
            clerk_phone="+254700123456",
        )

        assert cp.clerk_id == "CLK-123"
        assert cp.clerk_phone == "+254700123456"

    def test_collection_point_model_dump(self) -> None:
        """Test collection point serialization with model_dump (Pydantic 2.0)."""
        cp = CollectionPoint(
            id="test-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-1.0, longitude=37.0, altitude_meters=1500.0),
            region_id="test",
        )

        data = cp.model_dump()

        assert data["id"] == "test-cp-001"
        assert data["factory_id"] == "KEN-FAC-001"
        assert data["location"]["altitude_meters"] == 1500.0
        assert data["operating_hours"]["weekdays"] == "06:00-10:00"


class TestCollectionPointCreate:
    """Tests for CollectionPointCreate model."""

    def test_create_valid(self) -> None:
        """Test valid collection point creation request."""
        create_req = CollectionPointCreate(
            name="New CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            region_id="test-region",
        )

        assert create_req.name == "New CP"
        assert create_req.factory_id == "KEN-FAC-001"
        assert create_req.status == "active"

    def test_create_with_full_details(self) -> None:
        """Test creation with all optional fields."""
        create_req = CollectionPointCreate(
            name="Full CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700000000",
            operating_hours=OperatingHours(weekdays="05:00-11:00"),
            collection_days=["mon", "tue", "wed"],
            capacity=CollectionPointCapacity(
                max_daily_kg=10000,
                storage_type="refrigerated",
                has_weighing_scale=True,
                has_qc_device=True,
            ),
        )

        assert create_req.clerk_id == "CLK-001"
        assert create_req.capacity.max_daily_kg == 10000
        assert create_req.collection_days == ["mon", "tue", "wed"]


class TestCollectionPointUpdate:
    """Tests for CollectionPointUpdate model."""

    def test_update_partial(self) -> None:
        """Test partial collection point update."""
        update = CollectionPointUpdate(clerk_id="NEW-CLK-001")

        assert update.clerk_id == "NEW-CLK-001"
        assert update.name is None
        assert update.status is None

    def test_update_operating_hours(self) -> None:
        """Test updating operating hours."""
        update = CollectionPointUpdate(
            operating_hours=OperatingHours(
                weekdays="07:00-12:00",
                weekends="08:00-10:00",
            )
        )

        assert update.operating_hours.weekdays == "07:00-12:00"
        assert update.operating_hours.weekends == "08:00-10:00"

    def test_update_status(self) -> None:
        """Test updating status."""
        update = CollectionPointUpdate(status="inactive")

        assert update.status == "inactive"


class TestValueObjects:
    """Tests for value objects."""

    def test_geo_location_validation(self) -> None:
        """Test GeoLocation validation."""
        # Valid location
        loc = GeoLocation(latitude=-1.2921, longitude=36.8219, altitude_meters=1660.0)
        assert loc.latitude == -1.2921
        assert loc.altitude_meters == 1660.0

        # Invalid latitude
        with pytest.raises(ValidationError):
            GeoLocation(latitude=91, longitude=0)  # > 90

        with pytest.raises(ValidationError):
            GeoLocation(latitude=-91, longitude=0)  # < -90

        # Invalid longitude
        with pytest.raises(ValidationError):
            GeoLocation(latitude=0, longitude=181)  # > 180

        with pytest.raises(ValidationError):
            GeoLocation(latitude=0, longitude=-181)  # < -180

    def test_geo_location_altitude_default(self) -> None:
        """Test GeoLocation altitude defaults to 0."""
        loc = GeoLocation(latitude=0, longitude=0)
        assert loc.altitude_meters == 0.0

    def test_operating_hours_defaults(self) -> None:
        """Test OperatingHours default values."""
        hours = OperatingHours()
        assert hours.weekdays == "06:00-10:00"
        assert hours.weekends == "07:00-09:00"

    def test_collection_point_capacity_validation(self) -> None:
        """Test CollectionPointCapacity validation."""
        capacity = CollectionPointCapacity(
            max_daily_kg=5000,
            storage_type="covered_shed",
            has_weighing_scale=True,
            has_qc_device=True,
        )

        assert capacity.max_daily_kg == 5000
        assert capacity.storage_type == "covered_shed"

        # Negative capacity should fail
        with pytest.raises(ValidationError):
            CollectionPointCapacity(max_daily_kg=-100)
