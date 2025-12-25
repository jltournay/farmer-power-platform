"""Farmer domain model."""

from datetime import UTC, datetime
from enum import Enum

from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from pydantic import BaseModel, Field


class FarmScale(str, Enum):
    """Farm scale classification based on hectares.

    Classification:
    - SMALLHOLDER: < 1 hectare (family-operated, manual harvesting)
    - MEDIUM: 1-5 hectares (may employ seasonal labor)
    - ESTATE: > 5 hectares (commercial operation)
    """

    SMALLHOLDER = "smallholder"
    MEDIUM = "medium"
    ESTATE = "estate"

    @classmethod
    def from_hectares(cls, hectares: float) -> "FarmScale":
        """Calculate farm scale from hectares.

        Args:
            hectares: Farm size in hectares.

        Returns:
            FarmScale enum value based on size thresholds.
        """
        if hectares < 1.0:
            return cls.SMALLHOLDER
        elif hectares <= 5.0:
            return cls.MEDIUM
        else:
            return cls.ESTATE


class NotificationChannel(str, Enum):
    """Channel for pushing notifications to farmers (action plans, alerts).

    Channels:
    - SMS: Text messages via Africa's Talking (most common, default)
    - WHATSAPP: WhatsApp messages (requires WhatsApp registration)

    Note: This is distinct from InteractionPreference which controls how
    farmers consume detailed information (text vs voice).
    """

    SMS = "sms"
    WHATSAPP = "whatsapp"


class InteractionPreference(str, Enum):
    """Preferred mode for consuming detailed information.

    Preferences:
    - TEXT: Prefers reading SMS/WhatsApp messages (default, most common)
    - VOICE: Prefers listening via IVR/Voice AI (for low-literacy farmers)

    Note: Even voice-preferring farmers receive SMS triggers; they then
    call IVR to listen to their action plans.
    """

    TEXT = "text"
    VOICE = "voice"


# Backwards compatibility aliases
PreferredChannel = NotificationChannel


class PreferredLanguage(str, Enum):
    """Preferred language for farmer communications.

    Languages supported in Kenya:
    - SW: Swahili (national language, default)
    - KI: Kikuyu (Central Kenya)
    - LUO: Luo (Western Kenya)
    - EN: English (formal communications)
    """

    SWAHILI = "sw"
    KIKUYU = "ki"
    LUO = "luo"
    ENGLISH = "en"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        """Get human-readable language name.

        Args:
            value: Language code (sw, ki, luo, en).

        Returns:
            Human-readable language name.
        """
        names = {
            "sw": "Swahili",
            "ki": "Kikuyu",
            "luo": "Luo",
            "en": "English",
        }
        return names.get(value, value)


class Farmer(BaseModel):
    """Farmer entity - tea producer registered at a collection point.

    Farmer IDs follow the format: WM-XXXX (e.g., WM-0001)
    where WM is the prefix and XXXX is a zero-padded sequence number.

    Key relationships:
    - Farmers are registered at a primary collection_point_id
    - Region is auto-assigned based on GPS coordinates and altitude band
    - Farm scale is auto-calculated from farm_size_hectares
    """

    id: str = Field(description="Unique farmer ID (format: WM-XXXX)")
    grower_number: str | None = Field(default=None, description="External/legacy grower number")
    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")
    region_id: str = Field(description="Auto-assigned region based on GPS + altitude")
    collection_point_id: str = Field(description="Primary registration collection point")
    farm_location: GeoLocation = Field(description="Farm GPS coordinates with altitude")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="Contact information (phone required)")
    farm_size_hectares: float = Field(ge=0.01, le=1000.0, description="Farm size in hectares")
    farm_scale: FarmScale = Field(description="Auto-calculated from farm_size_hectares")
    national_id: str = Field(min_length=1, max_length=20, description="Government-issued national ID")
    registration_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Registration timestamp",
    )
    is_active: bool = Field(default=True, description="Whether farmer is active")
    notification_channel: NotificationChannel = Field(
        default=NotificationChannel.SMS,
        description="Channel for pushing notifications (sms, whatsapp)",
    )
    interaction_pref: InteractionPreference = Field(
        default=InteractionPreference.TEXT,
        description="Preferred mode for consuming information (text, voice)",
    )
    pref_lang: PreferredLanguage = Field(
        default=PreferredLanguage.SWAHILI,
        description="Preferred language for communications",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "WM-0001",
                "grower_number": "GN-12345",
                "first_name": "Wanjiku",
                "last_name": "Kamau",
                "region_id": "nyeri-highland",
                "collection_point_id": "nyeri-highland-cp-001",
                "farm_location": {
                    "latitude": -0.4197,
                    "longitude": 36.9553,
                    "altitude_meters": 1950.0,
                },
                "contact": {
                    "phone": "+254712345678",
                    "email": "",
                    "address": "",
                },
                "farm_size_hectares": 1.5,
                "farm_scale": "medium",
                "national_id": "12345678",
                "is_active": True,
                "notification_channel": "sms",
                "interaction_pref": "text",
                "pref_lang": "sw",
            }
        }
    }


class FarmerCreate(BaseModel):
    """Data required to create a new farmer.

    Note: region_id, farm_scale, and altitude are auto-calculated by the service:
    - altitude: Fetched from Google Elevation API based on GPS
    - region_id: Determined by county + altitude band
    - farm_scale: Calculated from farm_size_hectares
    """

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=10, max_length=15, description="Phone number")
    national_id: str = Field(min_length=1, max_length=20, description="Government ID")
    farm_size_hectares: float = Field(ge=0.01, le=1000.0)
    latitude: float = Field(ge=-90, le=90, description="Farm latitude")
    longitude: float = Field(ge=-180, le=180, description="Farm longitude")
    collection_point_id: str = Field(description="Primary collection point")
    grower_number: str | None = Field(default=None, description="External/legacy grower number")


class FarmerUpdate(BaseModel):
    """Data for updating an existing farmer.

    Note: If farm_size_hectares is updated, farm_scale will be recalculated.
    region_id cannot be changed after registration.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    farm_size_hectares: float | None = Field(default=None, ge=0.01, le=1000.0)
    is_active: bool | None = None
    notification_channel: NotificationChannel | None = Field(
        default=None, description="Channel for pushing notifications"
    )
    interaction_pref: InteractionPreference | None = Field(
        default=None, description="Preferred mode for consuming information"
    )
    pref_lang: PreferredLanguage | None = Field(default=None, description="Preferred language for communications")
