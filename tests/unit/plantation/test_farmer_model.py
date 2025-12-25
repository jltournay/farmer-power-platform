"""Unit tests for Farmer domain model."""


import pytest
from plantation_model.domain.models.farmer import (
    Farmer,
    FarmerCreate,
    FarmerUpdate,
    FarmScale,
)
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from pydantic import ValidationError


class TestFarmScale:
    """Tests for FarmScale enum and auto-calculation."""

    def test_farm_scale_smallholder_under_one_hectare(self) -> None:
        """Test farms under 1 hectare are classified as smallholder."""
        assert FarmScale.from_hectares(0.5) == FarmScale.SMALLHOLDER
        assert FarmScale.from_hectares(0.01) == FarmScale.SMALLHOLDER
        assert FarmScale.from_hectares(0.99) == FarmScale.SMALLHOLDER

    def test_farm_scale_medium_one_to_five_hectares(self) -> None:
        """Test farms between 1-5 hectares are classified as medium."""
        assert FarmScale.from_hectares(1.0) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(2.5) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(5.0) == FarmScale.MEDIUM

    def test_farm_scale_estate_over_five_hectares(self) -> None:
        """Test farms over 5 hectares are classified as estate."""
        assert FarmScale.from_hectares(5.1) == FarmScale.ESTATE
        assert FarmScale.from_hectares(10.0) == FarmScale.ESTATE
        assert FarmScale.from_hectares(100.0) == FarmScale.ESTATE

    def test_farm_scale_boundary_one_hectare(self) -> None:
        """Test exactly 1 hectare is medium (boundary condition)."""
        assert FarmScale.from_hectares(1.0) == FarmScale.MEDIUM

    def test_farm_scale_boundary_five_hectares(self) -> None:
        """Test exactly 5 hectares is medium (boundary condition)."""
        assert FarmScale.from_hectares(5.0) == FarmScale.MEDIUM

    def test_farm_scale_enum_values(self) -> None:
        """Test FarmScale enum string values."""
        assert FarmScale.SMALLHOLDER.value == "smallholder"
        assert FarmScale.MEDIUM.value == "medium"
        assert FarmScale.ESTATE.value == "estate"


class TestFarmer:
    """Tests for Farmer model validation."""

    def test_farmer_creation_valid(self) -> None:
        """Test creating a valid farmer."""
        farmer = Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(
                latitude=-0.4197,
                longitude=36.9553,
                altitude_meters=1950.0,
            ),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )

        assert farmer.id == "WM-0001"
        assert farmer.first_name == "Wanjiku"
        assert farmer.last_name == "Kamau"
        assert farmer.region_id == "nyeri-highland"
        assert farmer.collection_point_id == "nyeri-highland-cp-001"
        assert farmer.farm_location.latitude == -0.4197
        assert farmer.farm_size_hectares == 1.5
        assert farmer.farm_scale == FarmScale.MEDIUM
        assert farmer.national_id == "12345678"
        assert farmer.is_active is True

    def test_farmer_first_name_validation_empty(self) -> None:
        """Test farmer first name cannot be empty."""
        with pytest.raises(ValidationError):
            Farmer(
                id="WM-0001",
                first_name="",  # Empty name should fail
                last_name="Kamau",
                region_id="nyeri-highland",
                collection_point_id="nyeri-highland-cp-001",
                farm_location=GeoLocation(latitude=0, longitude=0),
                contact=ContactInfo(phone="+254712345678"),
                farm_size_hectares=1.5,
                farm_scale=FarmScale.MEDIUM,
                national_id="12345678",
            )

    def test_farmer_last_name_validation_empty(self) -> None:
        """Test farmer last name cannot be empty."""
        with pytest.raises(ValidationError):
            Farmer(
                id="WM-0001",
                first_name="Wanjiku",
                last_name="",  # Empty name should fail
                region_id="nyeri-highland",
                collection_point_id="nyeri-highland-cp-001",
                farm_location=GeoLocation(latitude=0, longitude=0),
                contact=ContactInfo(phone="+254712345678"),
                farm_size_hectares=1.5,
                farm_scale=FarmScale.MEDIUM,
                national_id="12345678",
            )

    def test_farmer_farm_size_validation_too_small(self) -> None:
        """Test farm size must be at least 0.01 hectares."""
        with pytest.raises(ValidationError):
            Farmer(
                id="WM-0001",
                first_name="Wanjiku",
                last_name="Kamau",
                region_id="nyeri-highland",
                collection_point_id="nyeri-highland-cp-001",
                farm_location=GeoLocation(latitude=0, longitude=0),
                contact=ContactInfo(phone="+254712345678"),
                farm_size_hectares=0.001,  # Too small
                farm_scale=FarmScale.SMALLHOLDER,
                national_id="12345678",
            )

    def test_farmer_farm_size_validation_too_large(self) -> None:
        """Test farm size must not exceed 1000 hectares."""
        with pytest.raises(ValidationError):
            Farmer(
                id="WM-0001",
                first_name="Wanjiku",
                last_name="Kamau",
                region_id="nyeri-highland",
                collection_point_id="nyeri-highland-cp-001",
                farm_location=GeoLocation(latitude=0, longitude=0),
                contact=ContactInfo(phone="+254712345678"),
                farm_size_hectares=1001.0,  # Too large
                farm_scale=FarmScale.ESTATE,
                national_id="12345678",
            )

    def test_farmer_national_id_validation_empty(self) -> None:
        """Test national ID cannot be empty."""
        with pytest.raises(ValidationError):
            Farmer(
                id="WM-0001",
                first_name="Wanjiku",
                last_name="Kamau",
                region_id="nyeri-highland",
                collection_point_id="nyeri-highland-cp-001",
                farm_location=GeoLocation(latitude=0, longitude=0),
                contact=ContactInfo(phone="+254712345678"),
                farm_size_hectares=1.5,
                farm_scale=FarmScale.MEDIUM,
                national_id="",  # Empty should fail
            )

    def test_farmer_default_values(self) -> None:
        """Test farmer default values."""
        farmer = Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            region_id="test-region",
            collection_point_id="test-cp",
            farm_location=GeoLocation(latitude=0, longitude=0),
            contact=ContactInfo(phone="+254700000000"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )

        assert farmer.is_active is True
        assert farmer.grower_number is None

    def test_farmer_with_optional_grower_number(self) -> None:
        """Test farmer with optional grower number."""
        farmer = Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            region_id="test-region",
            collection_point_id="test-cp",
            farm_location=GeoLocation(latitude=0, longitude=0),
            contact=ContactInfo(phone="+254700000000"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            grower_number="GN-12345",
        )

        assert farmer.grower_number == "GN-12345"

    def test_farmer_model_dump(self) -> None:
        """Test farmer serialization with model_dump (Pydantic 2.0)."""
        farmer = Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(
                latitude=-0.4197,
                longitude=36.9553,
                altitude_meters=1950.0,
            ),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )

        data = farmer.model_dump()

        assert data["id"] == "WM-0001"
        assert data["first_name"] == "Wanjiku"
        assert data["farm_location"]["latitude"] == -0.4197
        assert data["farm_scale"] == "medium"


class TestFarmerCreate:
    """Tests for FarmerCreate model."""

    def test_farmer_create_valid(self) -> None:
        """Test valid farmer creation request."""
        create_req = FarmerCreate(
            first_name="Wanjiku",
            last_name="Kamau",
            phone="+254712345678",
            national_id="12345678",
            farm_size_hectares=1.5,
            latitude=-0.4197,
            longitude=36.9553,
            collection_point_id="nyeri-highland-cp-001",
        )

        assert create_req.first_name == "Wanjiku"
        assert create_req.last_name == "Kamau"
        assert create_req.phone == "+254712345678"
        assert create_req.national_id == "12345678"
        assert create_req.farm_size_hectares == 1.5
        assert create_req.collection_point_id == "nyeri-highland-cp-001"

    def test_farmer_create_with_grower_number(self) -> None:
        """Test farmer creation with optional grower number."""
        create_req = FarmerCreate(
            first_name="Wanjiku",
            last_name="Kamau",
            phone="+254712345678",
            national_id="12345678",
            farm_size_hectares=1.5,
            latitude=-0.4197,
            longitude=36.9553,
            collection_point_id="nyeri-highland-cp-001",
            grower_number="GN-12345",
        )

        assert create_req.grower_number == "GN-12345"

    def test_farmer_create_phone_validation(self) -> None:
        """Test phone number validation in create request."""
        with pytest.raises(ValidationError):
            FarmerCreate(
                first_name="Wanjiku",
                last_name="Kamau",
                phone="123",  # Too short
                national_id="12345678",
                farm_size_hectares=1.5,
                latitude=0,
                longitude=0,
                collection_point_id="test-cp",
            )

    def test_farmer_create_latitude_validation(self) -> None:
        """Test latitude must be in valid range."""
        with pytest.raises(ValidationError):
            FarmerCreate(
                first_name="Wanjiku",
                last_name="Kamau",
                phone="+254712345678",
                national_id="12345678",
                farm_size_hectares=1.5,
                latitude=91.0,  # Invalid latitude
                longitude=0,
                collection_point_id="test-cp",
            )

    def test_farmer_create_longitude_validation(self) -> None:
        """Test longitude must be in valid range."""
        with pytest.raises(ValidationError):
            FarmerCreate(
                first_name="Wanjiku",
                last_name="Kamau",
                phone="+254712345678",
                national_id="12345678",
                farm_size_hectares=1.5,
                latitude=0,
                longitude=181.0,  # Invalid longitude
                collection_point_id="test-cp",
            )


class TestFarmerUpdate:
    """Tests for FarmerUpdate model."""

    def test_farmer_update_partial(self) -> None:
        """Test partial farmer update."""
        update = FarmerUpdate(first_name="Updated Name")

        assert update.first_name == "Updated Name"
        assert update.last_name is None
        assert update.phone is None
        assert update.farm_size_hectares is None
        assert update.is_active is None

    def test_farmer_update_all_fields(self) -> None:
        """Test updating all fields."""
        update = FarmerUpdate(
            first_name="Updated First",
            last_name="Updated Last",
            phone="+254700000000",
            farm_size_hectares=2.5,
            is_active=False,
        )

        assert update.first_name == "Updated First"
        assert update.last_name == "Updated Last"
        assert update.phone == "+254700000000"
        assert update.farm_size_hectares == 2.5
        assert update.is_active is False

    def test_farmer_update_empty(self) -> None:
        """Test update with no fields."""
        update = FarmerUpdate()

        assert update.first_name is None
        assert update.last_name is None
        assert update.phone is None
        assert update.farm_size_hectares is None
        assert update.is_active is None
