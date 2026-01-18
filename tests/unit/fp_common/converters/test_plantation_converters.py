"""Unit tests for plantation_converters module.

Tests verify Proto-to-Pydantic conversion correctness including:
- Basic field mapping
- Enum conversion (Proto uppercase -> Pydantic lowercase)
- Nested message handling
- Optional field defaults
- Round-trip validation (proto -> pydantic -> model_dump)
"""

from fp_common.converters import (
    collection_point_from_proto,
    factory_from_proto,
    farmer_from_proto,
    farmer_summary_from_proto,
    region_from_proto,
)
from fp_common.models import (
    CollectionPoint,
    Factory,
    Farmer,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
    Region,
    TrendDirection,
)
from fp_proto.plantation.v1 import plantation_pb2


class TestFarmerFromProto:
    """Tests for farmer_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped.

        Story 9.5a: collection_point_id removed from Farmer
        """
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            farm_size_hectares=1.5,
            farm_scale=plantation_pb2.FARM_SCALE_MEDIUM,
            national_id="12345678",
            is_active=True,
        )

        farmer = farmer_from_proto(proto)

        assert isinstance(farmer, Farmer)
        assert farmer.id == "WM-0001"
        assert farmer.first_name == "Wanjiku"
        assert farmer.last_name == "Kamau"
        assert farmer.region_id == "nyeri-highland"
        assert farmer.farm_size_hectares == 1.5
        assert farmer.farm_scale == FarmScale.MEDIUM
        assert farmer.national_id == "12345678"
        assert farmer.is_active is True

    def test_enum_conversion_farm_scale(self):
        """Farm scale enum is correctly converted."""
        # Test SMALLHOLDER
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            farm_scale=plantation_pb2.FARM_SCALE_SMALLHOLDER,
        )
        farmer = farmer_from_proto(proto)
        assert farmer.farm_scale == FarmScale.SMALLHOLDER

        # Test ESTATE
        proto.farm_scale = plantation_pb2.FARM_SCALE_ESTATE
        farmer = farmer_from_proto(proto)
        assert farmer.farm_scale == FarmScale.ESTATE

    def test_enum_conversion_notification_channel(self):
        """Notification channel enum is correctly converted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
        )
        farmer = farmer_from_proto(proto)
        assert farmer.notification_channel == NotificationChannel.SMS

        proto.notification_channel = plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP
        farmer = farmer_from_proto(proto)
        assert farmer.notification_channel == NotificationChannel.WHATSAPP

    def test_enum_conversion_interaction_pref(self):
        """Interaction preference enum is correctly converted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_VOICE,
        )
        farmer = farmer_from_proto(proto)
        assert farmer.interaction_pref == InteractionPreference.VOICE

    def test_enum_conversion_pref_lang(self):
        """Preferred language enum is correctly converted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_SW,
        )
        farmer = farmer_from_proto(proto)
        assert farmer.pref_lang == PreferredLanguage.SWAHILI

        proto.pref_lang = plantation_pb2.PREFERRED_LANGUAGE_KI
        farmer = farmer_from_proto(proto)
        assert farmer.pref_lang == PreferredLanguage.KIKUYU

        proto.pref_lang = plantation_pb2.PREFERRED_LANGUAGE_LUO
        farmer = farmer_from_proto(proto)
        assert farmer.pref_lang == PreferredLanguage.LUO

        proto.pref_lang = plantation_pb2.PREFERRED_LANGUAGE_EN
        farmer = farmer_from_proto(proto)
        assert farmer.pref_lang == PreferredLanguage.ENGLISH

    def test_nested_contact_info(self):
        """Nested contact info is correctly extracted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            contact=plantation_pb2.ContactInfo(
                phone="+254712345678",
                email="test@example.com",
                address="123 Test St",
            ),
        )

        farmer = farmer_from_proto(proto)

        assert farmer.contact.phone == "+254712345678"
        assert farmer.contact.email == "test@example.com"
        assert farmer.contact.address == "123 Test St"

    def test_nested_farm_location(self):
        """Nested farm location is correctly extracted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            farm_location=plantation_pb2.GeoLocation(
                latitude=-0.4197,
                longitude=36.9553,
                altitude_meters=1950.0,
            ),
        )

        farmer = farmer_from_proto(proto)

        assert farmer.farm_location.latitude == -0.4197
        assert farmer.farm_location.longitude == 36.9553
        assert farmer.farm_location.altitude_meters == 1950.0

    def test_missing_optional_fields(self):
        """Missing optional fields use defaults."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
        )

        farmer = farmer_from_proto(proto)

        # Contact info defaults to empty strings
        assert farmer.contact.phone == ""
        assert farmer.contact.email == ""
        # Farm location defaults to 0,0
        assert farmer.farm_location.latitude == 0.0
        assert farmer.farm_location.longitude == 0.0
        # is_active defaults to False (Proto default)
        assert farmer.is_active is False

    def test_grower_number_optional(self):
        """Grower number is optional and mapped correctly."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            national_id="123",
            grower_number="GN-12345",
        )
        farmer = farmer_from_proto(proto)
        assert farmer.grower_number == "GN-12345"

        # Without grower_number
        proto.grower_number = ""
        farmer = farmer_from_proto(proto)
        assert farmer.grower_number is None


class TestFactoryFromProto:
    """Tests for factory_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Nyeri Tea Factory",
            code="NTF",
            region_id="nyeri-highland",
            processing_capacity_kg=50000,
            is_active=True,
        )

        factory = factory_from_proto(proto)

        assert isinstance(factory, Factory)
        assert factory.id == "KEN-FAC-001"
        assert factory.name == "Nyeri Tea Factory"
        assert factory.code == "NTF"
        assert factory.region_id == "nyeri-highland"
        assert factory.processing_capacity_kg == 50000
        assert factory.is_active is True

    def test_quality_thresholds_present(self):
        """Quality thresholds are extracted when present."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            quality_thresholds=plantation_pb2.QualityThresholds(
                tier_1=90.0,
                tier_2=75.0,
                tier_3=60.0,
            ),
        )

        factory = factory_from_proto(proto)

        assert factory.quality_thresholds.tier_1 == 90.0
        assert factory.quality_thresholds.tier_2 == 75.0
        assert factory.quality_thresholds.tier_3 == 60.0

    def test_quality_thresholds_defaults(self):
        """Quality thresholds use defaults when not set."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
        )

        factory = factory_from_proto(proto)

        # Defaults from QualityThresholds model
        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0

    def test_payment_policy_present(self):
        """Payment policy is extracted when present."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            payment_policy=plantation_pb2.PaymentPolicy(
                policy_type=plantation_pb2.PAYMENT_POLICY_TYPE_SPLIT_PAYMENT,
                tier_1_adjustment=0.15,
                tier_2_adjustment=0.0,
                tier_3_adjustment=-0.05,
                below_tier_3_adjustment=-0.10,
            ),
        )

        factory = factory_from_proto(proto)

        assert factory.payment_policy.policy_type.value == "split_payment"
        assert factory.payment_policy.tier_1_adjustment == 0.15
        assert factory.payment_policy.tier_2_adjustment == 0.0
        assert factory.payment_policy.tier_3_adjustment == -0.05
        assert factory.payment_policy.below_tier_3_adjustment == -0.10

    def test_nested_location(self):
        """Nested location is correctly extracted."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            location=plantation_pb2.GeoLocation(
                latitude=-0.4232,
                longitude=36.9587,
                altitude_meters=1950.0,
            ),
        )

        factory = factory_from_proto(proto)

        assert factory.location.latitude == -0.4232
        assert factory.location.longitude == 36.9587
        assert factory.location.altitude_meters == 1950.0


class TestCollectionPointFromProto:
    """Tests for collection_point_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = plantation_pb2.CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Kamakwa Collection Point",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            status="active",
        )

        cp = collection_point_from_proto(proto)

        assert isinstance(cp, CollectionPoint)
        assert cp.id == "nyeri-highland-cp-001"
        assert cp.name == "Kamakwa Collection Point"
        assert cp.factory_id == "KEN-FAC-001"
        assert cp.region_id == "nyeri-highland"
        assert cp.status == "active"

    def test_operating_hours(self):
        """Operating hours are correctly extracted."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
            operating_hours=plantation_pb2.OperatingHours(
                weekdays="05:00-11:00",
                weekends="08:00-10:00",
            ),
        )

        cp = collection_point_from_proto(proto)

        assert cp.operating_hours.weekdays == "05:00-11:00"
        assert cp.operating_hours.weekends == "08:00-10:00"

    def test_capacity(self):
        """Capacity information is correctly extracted."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
            capacity=plantation_pb2.CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="refrigerated",
                has_weighing_scale=True,
                has_qc_device=True,
            ),
        )

        cp = collection_point_from_proto(proto)

        assert cp.capacity.max_daily_kg == 5000
        assert cp.capacity.storage_type == "refrigerated"
        assert cp.capacity.has_weighing_scale is True
        assert cp.capacity.has_qc_device is True

    def test_collection_days(self):
        """Collection days are correctly extracted."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
            collection_days=["mon", "tue", "wed"],
        )

        cp = collection_point_from_proto(proto)

        assert cp.collection_days == ["mon", "tue", "wed"]

    def test_clerk_info(self):
        """Clerk information is correctly extracted."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
            clerk_id="CLK-001",
            clerk_phone="+254712345679",
        )

        cp = collection_point_from_proto(proto)

        assert cp.clerk_id == "CLK-001"
        assert cp.clerk_phone == "+254712345679"

    def test_farmer_ids_mapped(self):
        """Farmer IDs are correctly extracted (Story 9.5a)."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
            farmer_ids=["WM-0001", "WM-0002", "WM-0003"],
        )

        cp = collection_point_from_proto(proto)

        assert cp.farmer_ids == ["WM-0001", "WM-0002", "WM-0003"]

    def test_farmer_ids_empty_default(self):
        """Farmer IDs defaults to empty list when not set (Story 9.5a)."""
        proto = plantation_pb2.CollectionPoint(
            id="cp-001",
            name="Test CP",
            factory_id="fac-001",
            region_id="test-highland",
        )

        cp = collection_point_from_proto(proto)

        assert cp.farmer_ids == []


class TestRegionFromProto:
    """Tests for region_from_proto converter."""

    def test_minimal_region_proto(self):
        """Minimal Region proto with only required fields uses defaults."""
        proto = plantation_pb2.Region(
            region_id="test-highland",  # Must match {{county}}-{{altitude_band}} format
            name="Test Region",
            county="Test",
        )
        # Don't set any nested messages - test default handling

        region = region_from_proto(proto)

        assert isinstance(region, Region)
        assert region.region_id == "test-highland"
        assert region.name == "Test Region"
        assert region.county == "Test"
        assert region.country == "Kenya"  # Default
        # Geography defaults
        assert region.geography.center_gps.lat == 0.0
        assert region.geography.center_gps.lng == 0.0
        assert region.geography.radius_km == 25.0  # Default
        # Flush calendar defaults
        assert region.flush_calendar.first_flush.start == "01-01"
        # Agronomic defaults
        assert region.agronomic.soil_type == "unknown"
        assert region.agronomic.typical_diseases == []
        # Weather config defaults
        assert region.weather_config.api_location.lat == 0.0

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
            country="Kenya",
            is_active=True,
        )
        # Add minimal required nested messages
        proto.geography.center_gps.lat = -0.4197
        proto.geography.center_gps.lng = 36.9553
        proto.geography.radius_km = 25.0
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = -0.4197
        proto.weather_config.api_location.lng = 36.9553
        proto.weather_config.altitude_for_api = 1950

        region = region_from_proto(proto)

        assert isinstance(region, Region)
        assert region.region_id == "nyeri-highland"
        assert region.name == "Nyeri Highland"
        assert region.county == "Nyeri"
        assert region.country == "Kenya"
        assert region.is_active is True

    def test_geography_nested(self):
        """Geography nested message is correctly extracted."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = -0.4197
        proto.geography.center_gps.lng = 36.9553
        proto.geography.radius_km = 30.0
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        # Add minimal flush calendar
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = -0.4197
        proto.weather_config.api_location.lng = 36.9553

        region = region_from_proto(proto)

        assert region.geography.center_gps.lat == -0.4197
        assert region.geography.center_gps.lng == 36.9553
        assert region.geography.radius_km == 30.0
        assert region.geography.altitude_band.min_meters == 1800
        assert region.geography.altitude_band.max_meters == 2200
        assert region.geography.altitude_band.label.value == "highland"

    def test_flush_calendar_nested(self):
        """Flush calendar nested message is correctly extracted."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = 0
        proto.geography.center_gps.lng = 0
        proto.geography.radius_km = 25
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.first_flush.characteristics = "Highest quality"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = 0
        proto.weather_config.api_location.lng = 0

        region = region_from_proto(proto)

        assert region.flush_calendar.first_flush.start == "03-15"
        assert region.flush_calendar.first_flush.end == "05-15"
        assert region.flush_calendar.first_flush.characteristics == "Highest quality"

    def test_agronomic_nested(self):
        """Agronomic nested message is correctly extracted."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = 0
        proto.geography.center_gps.lng = 0
        proto.geography.radius_km = 25
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.agronomic.typical_diseases.extend(["blister_blight", "grey_blight"])
        proto.agronomic.harvest_peak_hours = "06:00-10:00"
        proto.agronomic.frost_risk = True
        proto.weather_config.api_location.lat = 0
        proto.weather_config.api_location.lng = 0

        region = region_from_proto(proto)

        assert region.agronomic.soil_type == "volcanic_red"
        assert region.agronomic.typical_diseases == ["blister_blight", "grey_blight"]
        assert region.agronomic.harvest_peak_hours == "06:00-10:00"
        assert region.agronomic.frost_risk is True

    def test_weather_config_nested(self):
        """Weather config nested message is correctly extracted."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = 0
        proto.geography.center_gps.lng = 0
        proto.geography.radius_km = 25
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = -0.4197
        proto.weather_config.api_location.lng = 36.9553
        proto.weather_config.altitude_for_api = 1950
        proto.weather_config.collection_time = "07:00"

        region = region_from_proto(proto)

        assert region.weather_config.api_location.lat == -0.4197
        assert region.weather_config.api_location.lng == 36.9553
        assert region.weather_config.altitude_for_api == 1950
        assert region.weather_config.collection_time == "07:00"

    def test_geography_without_boundary(self):
        """Geography without boundary is correctly handled (Story 1.10)."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = -0.4197
        proto.geography.center_gps.lng = 36.9553
        proto.geography.radius_km = 25
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND
        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = 0
        proto.weather_config.api_location.lng = 0

        region = region_from_proto(proto)

        # Boundary should be None when not provided
        assert region.geography.boundary is None
        assert region.geography.area_km2 is None
        assert region.geography.perimeter_km is None

    def test_geography_with_boundary(self):
        """Geography with boundary is correctly extracted (Story 1.10)."""
        proto = plantation_pb2.Region(
            region_id="nyeri-highland",
            name="Nyeri Highland",
            county="Nyeri",
        )
        proto.geography.center_gps.lat = -0.4197
        proto.geography.center_gps.lng = 36.9553
        proto.geography.radius_km = 25
        proto.geography.altitude_band.min_meters = 1800
        proto.geography.altitude_band.max_meters = 2200
        proto.geography.altitude_band.label = plantation_pb2.ALTITUDE_BAND_HIGHLAND

        # Add polygon boundary (Story 1.10)
        proto.geography.boundary.type = "Polygon"
        ring = proto.geography.boundary.rings.add()
        # Add 4 points forming a closed triangle
        for lng, lat in [(36.9, -0.4), (37.0, -0.4), (36.95, -0.3), (36.9, -0.4)]:
            coord = ring.points.add()
            coord.longitude = lng
            coord.latitude = lat

        # Add optional computed values
        proto.geography.area_km2 = 150.5
        proto.geography.perimeter_km = 50.2

        proto.flush_calendar.first_flush.start = "03-15"
        proto.flush_calendar.first_flush.end = "05-15"
        proto.flush_calendar.monsoon_flush.start = "06-15"
        proto.flush_calendar.monsoon_flush.end = "09-30"
        proto.flush_calendar.autumn_flush.start = "10-15"
        proto.flush_calendar.autumn_flush.end = "12-15"
        proto.flush_calendar.dormant.start = "12-16"
        proto.flush_calendar.dormant.end = "03-14"
        proto.agronomic.soil_type = "volcanic_red"
        proto.weather_config.api_location.lat = 0
        proto.weather_config.api_location.lng = 0

        region = region_from_proto(proto)

        # Boundary should be present
        assert region.geography.boundary is not None
        assert region.geography.boundary.type == "Polygon"
        assert len(region.geography.boundary.rings) == 1
        assert len(region.geography.boundary.exterior.points) == 4

        # First point should match
        assert region.geography.boundary.exterior.points[0].longitude == 36.9
        assert region.geography.boundary.exterior.points[0].latitude == -0.4

        # Computed values should be present
        assert region.geography.area_km2 == 150.5
        assert region.geography.perimeter_km == 50.2


class TestFarmerSummaryFromProto:
    """Tests for farmer_summary_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped.

        Story 9.5a: collection_point_id removed from FarmerSummary
        """
        proto = plantation_pb2.FarmerSummary(
            farmer_id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            phone="+254712345678",
            farm_size_hectares=1.5,
            farm_scale=plantation_pb2.FARM_SCALE_MEDIUM,
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            trend_direction=plantation_pb2.TREND_DIRECTION_IMPROVING,
        )

        summary = farmer_summary_from_proto(proto)

        assert summary["farmer_id"] == "WM-0001"
        assert summary["first_name"] == "Wanjiku"
        assert summary["last_name"] == "Kamau"
        assert summary["phone"] == "+254712345678"
        assert summary["farm_size_hectares"] == 1.5
        assert summary["farm_scale"] == FarmScale.MEDIUM
        assert summary["grading_model_id"] == "tbk_kenya_tea_v1"
        assert summary["grading_model_version"] == "1.0.0"
        assert summary["trend_direction"] == TrendDirection.IMPROVING

    def test_communication_prefs(self):
        """Communication preferences are correctly extracted."""
        proto = plantation_pb2.FarmerSummary(
            farmer_id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_VOICE,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_KI,
        )

        summary = farmer_summary_from_proto(proto)

        assert summary["notification_channel"] == NotificationChannel.WHATSAPP
        assert summary["interaction_pref"] == InteractionPreference.VOICE
        assert summary["pref_lang"] == PreferredLanguage.KIKUYU

    def test_historical_metrics_present(self):
        """Historical metrics are correctly extracted when present."""
        proto = plantation_pb2.FarmerSummary(
            farmer_id="WM-0001",
            first_name="Test",
            last_name="Farmer",
        )
        # Set historical metrics
        proto.historical.grade_distribution_30d["Primary"] = 120
        proto.historical.grade_distribution_30d["Secondary"] = 30
        proto.historical.primary_percentage_30d = 80.0
        proto.historical.total_kg_30d = 450.0
        proto.historical.improvement_trend = plantation_pb2.TREND_DIRECTION_IMPROVING

        summary = farmer_summary_from_proto(proto)

        assert summary["historical"] is not None
        assert summary["historical"].grade_distribution_30d["Primary"] == 120
        assert summary["historical"].grade_distribution_30d["Secondary"] == 30
        assert summary["historical"].primary_percentage_30d == 80.0
        assert summary["historical"].total_kg_30d == 450.0
        assert summary["historical"].improvement_trend == TrendDirection.IMPROVING

    def test_today_metrics_present(self):
        """Today metrics are correctly extracted when present."""
        proto = plantation_pb2.FarmerSummary(
            farmer_id="WM-0001",
            first_name="Test",
            last_name="Farmer",
        )
        # Set today metrics
        proto.today.deliveries = 3
        proto.today.total_kg = 45.0
        proto.today.grade_counts["Primary"] = 3
        proto.today.metrics_date = "2026-01-06"

        summary = farmer_summary_from_proto(proto)

        assert summary["today"] is not None
        assert summary["today"].deliveries == 3
        assert summary["today"].total_kg == 45.0
        assert summary["today"].grade_counts["Primary"] == 3


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_farmer_round_trip(self):
        """Proto -> Pydantic -> dict produces expected structure.

        Story 9.5a: collection_point_id removed from Farmer
        """
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            farm_size_hectares=1.5,
            farm_scale=plantation_pb2.FARM_SCALE_MEDIUM,
            national_id="12345678",
            is_active=True,
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
        )
        proto.contact.phone = "+254712345678"

        farmer = farmer_from_proto(proto)
        data = farmer.model_dump()

        # Verify key fields in dict
        assert data["id"] == "WM-0001"
        assert data["first_name"] == "Wanjiku"
        assert data["last_name"] == "Kamau"
        assert data["farm_scale"] == "medium"  # Enum serialized as value
        assert data["notification_channel"] == "sms"
        assert data["contact"]["phone"] == "+254712345678"
        assert data["is_active"] is True

    def test_factory_round_trip(self):
        """Proto -> Pydantic -> dict produces expected structure."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Nyeri Tea Factory",
            code="NTF",
            region_id="nyeri-highland",
            processing_capacity_kg=50000,
            is_active=True,
        )
        proto.quality_thresholds.tier_1 = 90.0
        proto.quality_thresholds.tier_2 = 75.0
        proto.quality_thresholds.tier_3 = 60.0

        factory = factory_from_proto(proto)
        data = factory.model_dump()

        assert data["id"] == "KEN-FAC-001"
        assert data["name"] == "Nyeri Tea Factory"
        assert data["quality_thresholds"]["tier_1"] == 90.0
        assert data["quality_thresholds"]["tier_2"] == 75.0
        assert data["quality_thresholds"]["tier_3"] == 60.0

    def test_collection_point_round_trip(self):
        """Proto -> Pydantic -> dict produces expected structure."""
        proto = plantation_pb2.CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Kamakwa CP",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            status="active",
        )
        proto.location.latitude = -0.4150
        proto.location.longitude = 36.9500

        cp = collection_point_from_proto(proto)
        data = cp.model_dump()

        assert data["id"] == "nyeri-highland-cp-001"
        assert data["name"] == "Kamakwa CP"
        assert data["location"]["latitude"] == -0.4150
        assert data["location"]["longitude"] == 36.9500
        assert data["status"] == "active"
