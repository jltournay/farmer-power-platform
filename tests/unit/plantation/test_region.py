"""Unit tests for Region domain model and value objects (Story 1.8)."""

import pytest
from plantation_model.domain.models.region import Region, RegionCreate, RegionUpdate
from plantation_model.domain.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    FlushCalendar,
    FlushPeriod,
    Geography,
    WeatherConfig,
)
from pydantic import ValidationError

# ============================================================================
# Test Fixtures
# ============================================================================


def create_valid_flush_calendar() -> FlushCalendar:
    """Create a valid FlushCalendar for testing."""
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


def create_valid_geography(altitude_label: AltitudeBandLabel = AltitudeBandLabel.HIGHLAND) -> Geography:
    """Create a valid Geography for testing."""
    return Geography(
        center_gps=GPS(lat=-0.4197, lng=36.9553),
        radius_km=25,
        altitude_band=AltitudeBand(
            min_meters=1800,
            max_meters=2200,
            label=altitude_label,
        ),
    )


def create_valid_region() -> Region:
    """Create a valid Region for testing."""
    return Region(
        region_id="nyeri-highland",
        name="Nyeri Highland",
        county="Nyeri",
        country="Kenya",
        geography=create_valid_geography(),
        flush_calendar=create_valid_flush_calendar(),
        agronomic=Agronomic(
            soil_type="volcanic_red",
            typical_diseases=["blister_blight", "grey_blight"],
            harvest_peak_hours="06:00-10:00",
            frost_risk=True,
        ),
        weather_config=WeatherConfig(
            api_location=GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
            collection_time="06:00",
        ),
    )


# ============================================================================
# GPS Value Object Tests
# ============================================================================


class TestGPS:
    """Tests for GPS value object."""

    def test_gps_valid(self) -> None:
        """Test creating a valid GPS coordinate."""
        gps = GPS(lat=-0.4197, lng=36.9553)
        assert gps.lat == -0.4197
        assert gps.lng == 36.9553

    def test_gps_latitude_range(self) -> None:
        """Test latitude must be between -90 and 90."""
        with pytest.raises(ValidationError):
            GPS(lat=-91.0, lng=0.0)
        with pytest.raises(ValidationError):
            GPS(lat=91.0, lng=0.0)

    def test_gps_longitude_range(self) -> None:
        """Test longitude must be between -180 and 180."""
        with pytest.raises(ValidationError):
            GPS(lat=0.0, lng=-181.0)
        with pytest.raises(ValidationError):
            GPS(lat=0.0, lng=181.0)


# ============================================================================
# AltitudeBand Value Object Tests
# ============================================================================


class TestAltitudeBand:
    """Tests for AltitudeBand value object."""

    def test_altitude_band_valid_highland(self) -> None:
        """Test creating a valid highland altitude band."""
        band = AltitudeBand(min_meters=1800, max_meters=2200, label=AltitudeBandLabel.HIGHLAND)
        assert band.min_meters == 1800
        assert band.max_meters == 2200
        assert band.label == AltitudeBandLabel.HIGHLAND

    def test_altitude_band_valid_midland(self) -> None:
        """Test creating a valid midland altitude band."""
        band = AltitudeBand(min_meters=1400, max_meters=1800, label=AltitudeBandLabel.MIDLAND)
        assert band.label == AltitudeBandLabel.MIDLAND

    def test_altitude_band_valid_lowland(self) -> None:
        """Test creating a valid lowland altitude band."""
        band = AltitudeBand(min_meters=1000, max_meters=1400, label=AltitudeBandLabel.LOWLAND)
        assert band.label == AltitudeBandLabel.LOWLAND

    def test_altitude_band_max_less_than_min_fails(self) -> None:
        """Test max_meters must be >= min_meters."""
        with pytest.raises(ValidationError) as exc_info:
            AltitudeBand(min_meters=2000, max_meters=1800, label=AltitudeBandLabel.HIGHLAND)
        assert "max_meters" in str(exc_info.value)

    def test_altitude_band_negative_altitude_fails(self) -> None:
        """Test altitude values must be non-negative."""
        with pytest.raises(ValidationError):
            AltitudeBand(min_meters=-100, max_meters=1800, label=AltitudeBandLabel.MIDLAND)

    def test_altitude_band_invalid_label_fails(self) -> None:
        """Test altitude band label must be valid enum value."""
        with pytest.raises(ValidationError):
            AltitudeBand(min_meters=1800, max_meters=2200, label="invalid")


# ============================================================================
# FlushPeriod Value Object Tests
# ============================================================================


class TestFlushPeriod:
    """Tests for FlushPeriod value object."""

    def test_flush_period_valid(self) -> None:
        """Test creating a valid flush period."""
        period = FlushPeriod(start="03-15", end="05-15", characteristics="Highest quality")
        assert period.start == "03-15"
        assert period.end == "05-15"
        assert period.characteristics == "Highest quality"

    def test_flush_period_invalid_start_format(self) -> None:
        """Test start date must be MM-DD format."""
        with pytest.raises(ValidationError) as exc_info:
            FlushPeriod(start="3-15", end="05-15")
        assert "MM-DD" in str(exc_info.value)

    def test_flush_period_invalid_end_format(self) -> None:
        """Test end date must be MM-DD format."""
        with pytest.raises(ValidationError) as exc_info:
            FlushPeriod(start="03-15", end="05/15")
        assert "MM-DD" in str(exc_info.value)

    def test_flush_period_invalid_month(self) -> None:
        """Test month must be 01-12."""
        with pytest.raises(ValidationError):
            FlushPeriod(start="13-15", end="05-15")

    def test_flush_period_invalid_day(self) -> None:
        """Test day must be 01-31."""
        with pytest.raises(ValidationError):
            FlushPeriod(start="03-32", end="05-15")


# ============================================================================
# WeatherConfig Value Object Tests
# ============================================================================


class TestWeatherConfig:
    """Tests for WeatherConfig value object."""

    def test_weather_config_valid(self) -> None:
        """Test creating a valid weather config."""
        config = WeatherConfig(
            api_location=GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
            collection_time="06:00",
        )
        assert config.api_location.lat == -0.4197
        assert config.altitude_for_api == 1950
        assert config.collection_time == "06:00"

    def test_weather_config_default_collection_time(self) -> None:
        """Test default collection time is 06:00."""
        config = WeatherConfig(
            api_location=GPS(lat=0, lng=0),
            altitude_for_api=1500,
        )
        assert config.collection_time == "06:00"

    def test_weather_config_invalid_time_format(self) -> None:
        """Test collection time must be HH:MM format."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(
                api_location=GPS(lat=0, lng=0),
                altitude_for_api=1500,
                collection_time="6:00",  # Invalid - should be 06:00
            )
        assert "HH:MM" in str(exc_info.value)

    def test_weather_config_negative_altitude_fails(self) -> None:
        """Test altitude must be non-negative."""
        with pytest.raises(ValidationError):
            WeatherConfig(
                api_location=GPS(lat=0, lng=0),
                altitude_for_api=-100,
            )


# ============================================================================
# Agronomic Value Object Tests
# ============================================================================


class TestAgronomic:
    """Tests for Agronomic value object."""

    def test_agronomic_valid(self) -> None:
        """Test creating valid agronomic data."""
        agronomic = Agronomic(
            soil_type="volcanic_red",
            typical_diseases=["blister_blight", "grey_blight"],
            harvest_peak_hours="06:00-10:00",
            frost_risk=True,
        )
        assert agronomic.soil_type == "volcanic_red"
        assert len(agronomic.typical_diseases) == 2
        assert agronomic.frost_risk is True

    def test_agronomic_default_harvest_hours(self) -> None:
        """Test default harvest hours."""
        agronomic = Agronomic(soil_type="clay")
        assert agronomic.harvest_peak_hours == "06:00-10:00"

    def test_agronomic_invalid_harvest_hours_format(self) -> None:
        """Test harvest hours must be HH:MM-HH:MM format."""
        with pytest.raises(ValidationError) as exc_info:
            Agronomic(soil_type="clay", harvest_peak_hours="6:00-10:00")
        assert "HH:MM-HH:MM" in str(exc_info.value)

    def test_agronomic_empty_diseases_list(self) -> None:
        """Test empty diseases list is valid."""
        agronomic = Agronomic(soil_type="sandy")
        assert agronomic.typical_diseases == []


# ============================================================================
# Region Entity Tests
# ============================================================================


class TestRegion:
    """Tests for Region entity."""

    def test_region_creation_valid(self) -> None:
        """Test creating a valid region."""
        region = create_valid_region()

        assert region.region_id == "nyeri-highland"
        assert region.name == "Nyeri Highland"
        assert region.county == "Nyeri"
        assert region.country == "Kenya"
        assert region.geography.center_gps.lat == -0.4197
        assert region.is_active is True

    def test_region_id_format_valid_highland(self) -> None:
        """Test region_id format with highland."""
        region = create_valid_region()
        assert region.region_id == "nyeri-highland"

    def test_region_id_format_valid_midland(self) -> None:
        """Test region_id format with midland."""
        region = Region(
            region_id="kericho-midland",
            name="Kericho Midland",
            county="Kericho",
            geography=create_valid_geography(AltitudeBandLabel.MIDLAND),
            flush_calendar=create_valid_flush_calendar(),
            agronomic=Agronomic(soil_type="red_clay"),
            weather_config=WeatherConfig(api_location=GPS(lat=0, lng=35), altitude_for_api=1600),
        )
        assert region.region_id == "kericho-midland"

    def test_region_id_format_valid_lowland(self) -> None:
        """Test region_id format with lowland."""
        region = Region(
            region_id="mombasa-lowland",
            name="Mombasa Lowland",
            county="Mombasa",
            geography=create_valid_geography(AltitudeBandLabel.LOWLAND),
            flush_calendar=create_valid_flush_calendar(),
            agronomic=Agronomic(soil_type="sandy"),
            weather_config=WeatherConfig(api_location=GPS(lat=-4, lng=39), altitude_for_api=50),
        )
        assert region.region_id == "mombasa-lowland"

    def test_region_id_invalid_format_uppercase(self) -> None:
        """Test region_id must be lowercase."""
        with pytest.raises(ValidationError) as exc_info:
            Region(
                region_id="Nyeri-Highland",  # Invalid - uppercase
                name="Nyeri Highland",
                county="Nyeri",
                geography=create_valid_geography(),
                flush_calendar=create_valid_flush_calendar(),
                agronomic=Agronomic(soil_type="volcanic"),
                weather_config=WeatherConfig(api_location=GPS(lat=0, lng=0), altitude_for_api=1500),
            )
        assert "region_id" in str(exc_info.value).lower()

    def test_region_id_invalid_format_wrong_suffix(self) -> None:
        """Test region_id must end with valid altitude band."""
        with pytest.raises(ValidationError) as exc_info:
            Region(
                region_id="nyeri-upland",  # Invalid - upland is not a valid band
                name="Nyeri Upland",
                county="Nyeri",
                geography=create_valid_geography(),
                flush_calendar=create_valid_flush_calendar(),
                agronomic=Agronomic(soil_type="volcanic"),
                weather_config=WeatherConfig(api_location=GPS(lat=0, lng=0), altitude_for_api=1500),
            )
        assert "highland" in str(exc_info.value) or "midland" in str(exc_info.value)

    def test_region_id_invalid_format_no_hyphen(self) -> None:
        """Test region_id must have hyphen separator."""
        with pytest.raises(ValidationError):
            Region(
                region_id="nyerihighland",  # Invalid - no hyphen
                name="Nyeri Highland",
                county="Nyeri",
                geography=create_valid_geography(),
                flush_calendar=create_valid_flush_calendar(),
                agronomic=Agronomic(soil_type="volcanic"),
                weather_config=WeatherConfig(api_location=GPS(lat=0, lng=0), altitude_for_api=1500),
            )

    def test_region_name_validation(self) -> None:
        """Test region name must not be empty."""
        with pytest.raises(ValidationError):
            Region(
                region_id="nyeri-highland",
                name="",  # Empty name should fail
                county="Nyeri",
                geography=create_valid_geography(),
                flush_calendar=create_valid_flush_calendar(),
                agronomic=Agronomic(soil_type="volcanic"),
                weather_config=WeatherConfig(api_location=GPS(lat=0, lng=0), altitude_for_api=1500),
            )

    def test_region_model_dump(self) -> None:
        """Test region serialization with model_dump (Pydantic 2.0)."""
        region = create_valid_region()
        data = region.model_dump()

        assert data["region_id"] == "nyeri-highland"
        assert data["name"] == "Nyeri Highland"
        assert data["geography"]["center_gps"]["lat"] == -0.4197
        assert data["flush_calendar"]["first_flush"]["start"] == "03-15"
        assert data["agronomic"]["frost_risk"] is True

    def test_region_get_altitude_band_label(self) -> None:
        """Test getting altitude band label from region."""
        region = create_valid_region()
        assert region.get_altitude_band_label() == AltitudeBandLabel.HIGHLAND


# ============================================================================
# RegionCreate Tests
# ============================================================================


class TestRegionCreate:
    """Tests for RegionCreate model."""

    def test_region_create_valid(self) -> None:
        """Test valid region creation request."""
        create_req = RegionCreate(
            name="New Region",
            county="Nakuru",
            geography=create_valid_geography(),
            flush_calendar=create_valid_flush_calendar(),
            agronomic=Agronomic(soil_type="loamy"),
            weather_config=WeatherConfig(api_location=GPS(lat=-0.3, lng=36.0), altitude_for_api=1900),
        )

        assert create_req.name == "New Region"
        assert create_req.county == "Nakuru"
        assert create_req.country == "Kenya"  # Default

    def test_region_create_generate_region_id(self) -> None:
        """Test generating region_id from county and altitude band."""
        create_req = RegionCreate(
            name="Nakuru Highland",
            county="Nakuru",
            geography=create_valid_geography(AltitudeBandLabel.HIGHLAND),
            flush_calendar=create_valid_flush_calendar(),
            agronomic=Agronomic(soil_type="loamy"),
            weather_config=WeatherConfig(api_location=GPS(lat=-0.3, lng=36.0), altitude_for_api=1900),
        )

        region_id = create_req.generate_region_id()
        assert region_id == "nakuru-highland"

    def test_region_create_generate_region_id_with_spaces(self) -> None:
        """Test generating region_id handles spaces in county name."""
        create_req = RegionCreate(
            name="Mount Kenya Midland",
            county="Mount Kenya",
            geography=create_valid_geography(AltitudeBandLabel.MIDLAND),
            flush_calendar=create_valid_flush_calendar(),
            agronomic=Agronomic(soil_type="volcanic"),
            weather_config=WeatherConfig(api_location=GPS(lat=-0.15, lng=37.3), altitude_for_api=1600),
        )

        region_id = create_req.generate_region_id()
        assert region_id == "mountkenya-midland"


# ============================================================================
# RegionUpdate Tests
# ============================================================================


class TestRegionUpdate:
    """Tests for RegionUpdate model."""

    def test_region_update_partial(self) -> None:
        """Test partial region update."""
        update = RegionUpdate(name="Updated Name")

        assert update.name == "Updated Name"
        assert update.geography is None
        assert update.is_active is None

    def test_region_update_all_fields(self) -> None:
        """Test updating all fields."""
        update = RegionUpdate(
            name="Updated Name",
            geography=create_valid_geography(),
            is_active=False,
        )

        assert update.name == "Updated Name"
        assert update.geography is not None
        assert update.is_active is False
