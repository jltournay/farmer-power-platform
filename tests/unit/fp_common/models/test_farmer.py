"""Unit tests for Farmer model in fp_common."""

import pytest
from fp_common.models import (
    Farmer,
    FarmerCreate,
    FarmerUpdate,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from fp_common.models.value_objects import ContactInfo, GeoLocation
from pydantic import ValidationError


class TestFarmScale:
    """Tests for FarmScale enum."""

    def test_farm_scale_values(self):
        """FarmScale enum has expected values."""
        assert FarmScale.SMALLHOLDER.value == "smallholder"
        assert FarmScale.MEDIUM.value == "medium"
        assert FarmScale.ESTATE.value == "estate"

    def test_from_hectares_smallholder(self):
        """Farm < 1 hectare is smallholder."""
        assert FarmScale.from_hectares(0.5) == FarmScale.SMALLHOLDER
        assert FarmScale.from_hectares(0.99) == FarmScale.SMALLHOLDER

    def test_from_hectares_medium(self):
        """Farm 1-5 hectares is medium."""
        assert FarmScale.from_hectares(1.0) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(3.0) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(5.0) == FarmScale.MEDIUM

    def test_from_hectares_estate(self):
        """Farm > 5 hectares is estate."""
        assert FarmScale.from_hectares(5.1) == FarmScale.ESTATE
        assert FarmScale.from_hectares(100.0) == FarmScale.ESTATE


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_channel_values(self):
        """NotificationChannel enum has expected values."""
        assert NotificationChannel.SMS.value == "sms"
        assert NotificationChannel.WHATSAPP.value == "whatsapp"


class TestInteractionPreference:
    """Tests for InteractionPreference enum."""

    def test_preference_values(self):
        """InteractionPreference enum has expected values."""
        assert InteractionPreference.TEXT.value == "text"
        assert InteractionPreference.VOICE.value == "voice"


class TestPreferredLanguage:
    """Tests for PreferredLanguage enum."""

    def test_language_values(self):
        """PreferredLanguage enum has expected values."""
        assert PreferredLanguage.SWAHILI.value == "sw"
        assert PreferredLanguage.KIKUYU.value == "ki"
        assert PreferredLanguage.LUO.value == "luo"
        assert PreferredLanguage.ENGLISH.value == "en"

    def test_get_display_name(self):
        """get_display_name returns human-readable name."""
        assert PreferredLanguage.get_display_name("sw") == "Swahili"
        assert PreferredLanguage.get_display_name("ki") == "Kikuyu"
        assert PreferredLanguage.get_display_name("luo") == "Luo"
        assert PreferredLanguage.get_display_name("en") == "English"
        assert PreferredLanguage.get_display_name("unknown") == "unknown"


class TestFarmerModel:
    """Tests for Farmer model."""

    @pytest.fixture
    def valid_farmer_data(self):
        """Valid farmer data for testing."""
        return {
            "id": "WM-0001",
            "first_name": "Wanjiku",
            "last_name": "Kamau",
            "region_id": "nyeri-highland",
            "collection_point_id": "nyeri-highland-cp-001",
            "farm_location": GeoLocation(latitude=-0.4197, longitude=36.9553, altitude_meters=1950.0),
            "contact": ContactInfo(phone="+254712345678"),
            "farm_size_hectares": 1.5,
            "farm_scale": FarmScale.MEDIUM,
            "national_id": "12345678",
        }

    def test_farmer_creation_with_required_fields(self, valid_farmer_data):
        """Farmer model accepts valid required fields."""
        farmer = Farmer(**valid_farmer_data)
        assert farmer.id == "WM-0001"
        assert farmer.first_name == "Wanjiku"
        assert farmer.last_name == "Kamau"
        assert farmer.region_id == "nyeri-highland"
        assert farmer.farm_size_hectares == 1.5
        assert farmer.farm_scale == FarmScale.MEDIUM

    def test_farmer_default_values(self, valid_farmer_data):
        """Farmer model has correct default values."""
        farmer = Farmer(**valid_farmer_data)
        assert farmer.is_active is True
        assert farmer.notification_channel == NotificationChannel.SMS
        assert farmer.interaction_pref == InteractionPreference.TEXT
        assert farmer.pref_lang == PreferredLanguage.SWAHILI
        assert farmer.grower_number is None

    def test_farmer_with_all_preferences(self, valid_farmer_data):
        """Farmer model accepts all preference fields."""
        farmer = Farmer(
            **valid_farmer_data,
            notification_channel=NotificationChannel.WHATSAPP,
            interaction_pref=InteractionPreference.VOICE,
            pref_lang=PreferredLanguage.KIKUYU,
        )
        assert farmer.notification_channel == NotificationChannel.WHATSAPP
        assert farmer.interaction_pref == InteractionPreference.VOICE
        assert farmer.pref_lang == PreferredLanguage.KIKUYU

    def test_farmer_validation_rejects_empty_first_name(self, valid_farmer_data):
        """Farmer model rejects empty first name."""
        valid_farmer_data["first_name"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Farmer(**valid_farmer_data)
        assert "first_name" in str(exc_info.value)

    def test_farmer_validation_rejects_empty_last_name(self, valid_farmer_data):
        """Farmer model rejects empty last name."""
        valid_farmer_data["last_name"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Farmer(**valid_farmer_data)
        assert "last_name" in str(exc_info.value)

    def test_farmer_validation_rejects_invalid_farm_size(self, valid_farmer_data):
        """Farmer model rejects invalid farm size."""
        valid_farmer_data["farm_size_hectares"] = 0.001  # Too small
        with pytest.raises(ValidationError) as exc_info:
            Farmer(**valid_farmer_data)
        assert "farm_size_hectares" in str(exc_info.value)

        valid_farmer_data["farm_size_hectares"] = 1001.0  # Too large
        with pytest.raises(ValidationError) as exc_info:
            Farmer(**valid_farmer_data)
        assert "farm_size_hectares" in str(exc_info.value)

    def test_farmer_model_dump_produces_dict(self, valid_farmer_data):
        """model_dump() produces a dictionary."""
        farmer = Farmer(**valid_farmer_data)
        data = farmer.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "WM-0001"
        assert data["first_name"] == "Wanjiku"

    def test_farmer_model_dump_excludes_none(self, valid_farmer_data):
        """model_dump(exclude_none=True) excludes None values."""
        farmer = Farmer(**valid_farmer_data)
        data = farmer.model_dump(exclude_none=True)
        # grower_number is None by default and should be excluded
        assert "grower_number" not in data or data.get("grower_number") is not None


class TestFarmerCreate:
    """Tests for FarmerCreate model."""

    def test_farmer_create_valid(self):
        """FarmerCreate accepts valid data."""
        create_data = FarmerCreate(
            first_name="John",
            last_name="Doe",
            phone="+254712345678",
            national_id="12345678",
            farm_size_hectares=2.0,
            latitude=-0.4197,
            longitude=36.9553,
            collection_point_id="cp-001",
        )
        assert create_data.first_name == "John"
        assert create_data.farm_size_hectares == 2.0

    def test_farmer_create_rejects_invalid_phone(self):
        """FarmerCreate rejects phone too short."""
        with pytest.raises(ValidationError) as exc_info:
            FarmerCreate(
                first_name="John",
                last_name="Doe",
                phone="123",  # Too short
                national_id="12345678",
                farm_size_hectares=2.0,
                latitude=-0.4197,
                longitude=36.9553,
                collection_point_id="cp-001",
            )
        assert "phone" in str(exc_info.value)

    def test_farmer_create_rejects_invalid_latitude(self):
        """FarmerCreate rejects latitude outside bounds."""
        with pytest.raises(ValidationError) as exc_info:
            FarmerCreate(
                first_name="John",
                last_name="Doe",
                phone="+254712345678",
                national_id="12345678",
                farm_size_hectares=2.0,
                latitude=-100.0,  # Invalid
                longitude=36.9553,
                collection_point_id="cp-001",
            )
        assert "latitude" in str(exc_info.value)


class TestFarmerUpdate:
    """Tests for FarmerUpdate model."""

    def test_farmer_update_all_optional(self):
        """FarmerUpdate fields are all optional."""
        update = FarmerUpdate()
        assert update.first_name is None
        assert update.last_name is None
        assert update.phone is None
        assert update.farm_size_hectares is None
        assert update.is_active is None

    def test_farmer_update_partial(self):
        """FarmerUpdate accepts partial updates."""
        update = FarmerUpdate(first_name="Jane", is_active=False)
        assert update.first_name == "Jane"
        assert update.is_active is False
        assert update.last_name is None

    def test_farmer_update_preferences(self):
        """FarmerUpdate accepts preference updates."""
        update = FarmerUpdate(
            notification_channel=NotificationChannel.WHATSAPP,
            interaction_pref=InteractionPreference.VOICE,
            pref_lang=PreferredLanguage.LUO,
        )
        assert update.notification_channel == NotificationChannel.WHATSAPP
        assert update.interaction_pref == InteractionPreference.VOICE
        assert update.pref_lang == PreferredLanguage.LUO
