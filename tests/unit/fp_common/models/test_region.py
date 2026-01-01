"""Unit tests for Region model in fp_common."""

import pytest
from fp_common.models import Region, RegionCreate, RegionUpdate
from fp_common.models.value_objects import (
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


class TestAltitudeBandLabel:
    """Tests for AltitudeBandLabel enum."""

    def test_altitude_band_values(self):
        """AltitudeBandLabel enum has expected values."""
        assert AltitudeBandLabel.HIGHLAND.value == "highland"
        assert AltitudeBandLabel.MIDLAND.value == "midland"
        assert AltitudeBandLabel.LOWLAND.value == "lowland"


class TestGPS:
    """Tests for GPS value object."""

    def test_gps_valid(self):
        """GPS accepts valid coordinates."""
        gps = GPS(lat=-0.4197, lng=36.9553)
        assert gps.lat == -0.4197
        assert gps.lng == 36.9553

    def test_gps_rejects_invalid_lat(self):
        """GPS rejects latitude outside bounds."""
        with pytest.raises(ValidationError):
            GPS(lat=-100.0, lng=36.9553)
        with pytest.raises(ValidationError):
            GPS(lat=100.0, lng=36.9553)

    def test_gps_rejects_invalid_lng(self):
        """GPS rejects longitude outside bounds."""
        with pytest.raises(ValidationError):
            GPS(lat=-0.4197, lng=-200.0)
        with pytest.raises(ValidationError):
            GPS(lat=-0.4197, lng=200.0)


class TestAltitudeBand:
    """Tests for AltitudeBand value object."""

    def test_altitude_band_valid(self):
        """AltitudeBand accepts valid data."""
        band = AltitudeBand(min_meters=1800, max_meters=2200, label=AltitudeBandLabel.HIGHLAND)
        assert band.min_meters == 1800
        assert band.max_meters == 2200
        assert band.label == AltitudeBandLabel.HIGHLAND

    def test_altitude_band_rejects_max_less_than_min(self):
        """AltitudeBand rejects max_meters < min_meters."""
        with pytest.raises(ValidationError) as exc_info:
            AltitudeBand(min_meters=2000, max_meters=1800, label=AltitudeBandLabel.HIGHLAND)
        assert "max_meters" in str(exc_info.value)


class TestFlushPeriod:
    """Tests for FlushPeriod value object."""

    def test_flush_period_valid(self):
        """FlushPeriod accepts valid MM-DD dates."""
        period = FlushPeriod(start="03-15", end="05-15", characteristics="High quality")
        assert period.start == "03-15"
        assert period.end == "05-15"
        assert period.characteristics == "High quality"

    def test_flush_period_rejects_invalid_format(self):
        """FlushPeriod rejects invalid date format."""
        with pytest.raises(ValidationError) as exc_info:
            FlushPeriod(start="2024-03-15", end="05-15")
        assert "Invalid date format" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            FlushPeriod(start="03-15", end="5-15")  # Missing leading zero
        assert "Invalid date format" in str(exc_info.value)


class TestWeatherConfig:
    """Tests for WeatherConfig value object."""

    def test_weather_config_valid(self):
        """WeatherConfig accepts valid data."""
        config = WeatherConfig(
            api_location=GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
            collection_time="06:00",
        )
        assert config.api_location.lat == -0.4197
        assert config.altitude_for_api == 1950
        assert config.collection_time == "06:00"

    def test_weather_config_rejects_invalid_time(self):
        """WeatherConfig rejects invalid collection_time format."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(
                api_location=GPS(lat=-0.4197, lng=36.9553),
                altitude_for_api=1950,
                collection_time="6:00",  # Missing leading zero
            )
        assert "Invalid time format" in str(exc_info.value)


class TestAgronomic:
    """Tests for Agronomic value object."""

    def test_agronomic_valid(self):
        """Agronomic accepts valid data."""
        agro = Agronomic(
            soil_type="volcanic_red",
            typical_diseases=["blister_blight", "grey_blight"],
            harvest_peak_hours="06:00-10:00",
            frost_risk=True,
        )
        assert agro.soil_type == "volcanic_red"
        assert len(agro.typical_diseases) == 2
        assert agro.frost_risk is True

    def test_agronomic_rejects_invalid_harvest_hours(self):
        """Agronomic rejects invalid harvest_peak_hours format."""
        with pytest.raises(ValidationError) as exc_info:
            Agronomic(soil_type="volcanic_red", harvest_peak_hours="6am-10am")
        assert "Invalid time range format" in str(exc_info.value)


@pytest.fixture
def valid_flush_calendar():
    """Valid flush calendar for testing."""
    return FlushCalendar(
        first_flush=FlushPeriod(start="03-15", end="05-15", characteristics="Highest quality"),
        monsoon_flush=FlushPeriod(start="06-15", end="09-30", characteristics="High volume"),
        autumn_flush=FlushPeriod(start="10-15", end="12-15", characteristics="Balanced"),
        dormant=FlushPeriod(start="12-16", end="03-14", characteristics="Minimal growth"),
    )


@pytest.fixture
def valid_geography():
    """Valid geography for testing."""
    return Geography(
        center_gps=GPS(lat=-0.4197, lng=36.9553),
        radius_km=25.0,
        altitude_band=AltitudeBand(min_meters=1800, max_meters=2200, label=AltitudeBandLabel.HIGHLAND),
    )


@pytest.fixture
def valid_weather_config():
    """Valid weather config for testing."""
    return WeatherConfig(
        api_location=GPS(lat=-0.4197, lng=36.9553),
        altitude_for_api=1950,
    )


@pytest.fixture
def valid_agronomic():
    """Valid agronomic for testing."""
    return Agronomic(soil_type="volcanic_red")


class TestRegionModel:
    """Tests for Region model."""

    def test_region_creation_valid(self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic):
        """Region model accepts valid data."""
        region = Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        assert region.region_id == "nyeri-highland"
        assert region.name == "Nyeri Highland"
        assert region.county == "Nyeri"
        assert region.country == "Kenya"  # Default

    def test_region_default_values(self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic):
        """Region model has correct default values."""
        region = Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        assert region.is_active is True
        assert region.country == "Kenya"

    def test_region_id_validation_valid_formats(
        self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic
    ):
        """Region accepts valid region_id formats."""
        for region_id in ["nyeri-highland", "kiambu-midland", "mombasa-lowland"]:
            region = Region(
                region_id=region_id,
                name="Test",
                county="Test",
                geography=valid_geography,
                flush_calendar=valid_flush_calendar,
                weather_config=valid_weather_config,
                agronomic=valid_agronomic,
            )
            assert region.region_id == region_id

    def test_region_id_validation_rejects_invalid(
        self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic
    ):
        """Region rejects invalid region_id formats."""
        invalid_ids = [
            "Nyeri-Highland",  # Uppercase
            "nyeri_highland",  # Underscore
            "nyeri-high",  # Invalid altitude band
            "nyeri",  # Missing altitude band
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                Region(
                    region_id=invalid_id,
                    name="Test",
                    county="Test",
                    geography=valid_geography,
                    flush_calendar=valid_flush_calendar,
                    weather_config=valid_weather_config,
                    agronomic=valid_agronomic,
                )
            assert "region_id" in str(exc_info.value)

    def test_region_get_altitude_band_label(
        self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic
    ):
        """get_altitude_band_label returns correct label."""
        region = Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        assert region.get_altitude_band_label() == AltitudeBandLabel.HIGHLAND

    def test_region_model_dump_produces_dict(
        self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic
    ):
        """model_dump() produces a dictionary."""
        region = Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        data = region.model_dump()
        assert isinstance(data, dict)
        assert data["region_id"] == "nyeri-highland"
        assert data["name"] == "Nyeri Highland"


class TestRegionCreate:
    """Tests for RegionCreate model."""

    def test_region_create_valid(self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic):
        """RegionCreate accepts valid data."""
        create_data = RegionCreate(
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        assert create_data.name == "Nyeri Highland"
        assert create_data.county == "Nyeri"

    def test_region_create_generate_region_id(
        self, valid_geography, valid_flush_calendar, valid_weather_config, valid_agronomic
    ):
        """generate_region_id creates proper ID from county and altitude band."""
        create_data = RegionCreate(
            name="Nyeri Highland",
            county="Nyeri",
            geography=valid_geography,
            flush_calendar=valid_flush_calendar,
            weather_config=valid_weather_config,
            agronomic=valid_agronomic,
        )
        assert create_data.generate_region_id() == "nyeri-highland"


class TestRegionUpdate:
    """Tests for RegionUpdate model."""

    def test_region_update_all_optional(self):
        """RegionUpdate fields are all optional."""
        update = RegionUpdate()
        assert update.name is None
        assert update.geography is None
        assert update.flush_calendar is None
        assert update.is_active is None

    def test_region_update_partial(self, valid_geography):
        """RegionUpdate accepts partial updates."""
        update = RegionUpdate(name="Updated Name", geography=valid_geography)
        assert update.name == "Updated Name"
        assert update.geography is not None
        assert update.flush_calendar is None
