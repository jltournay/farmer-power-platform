"""Unit tests for Farmer Communication Preferences gRPC operations (Story 1.5).

Design Decision: Split notification channel from interaction preference
- notification_channel: How we PUSH notifications (sms, whatsapp)
- interaction_pref: How farmer prefers to CONSUME information (text, voice)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.domain.models.farmer import (
    Farmer,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.google_elevation import GoogleElevationClient
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from fp_proto.plantation.v1 import plantation_pb2


class TestFarmerCommunicationPreferences:
    """Tests for farmer communication preferences (Story 1.5)."""

    @pytest.fixture
    def mock_factory_repo(self) -> MagicMock:
        """Create a mock factory repository."""
        return MagicMock(spec=FactoryRepository)

    @pytest.fixture
    def mock_cp_repo(self) -> MagicMock:
        """Create a mock collection point repository."""
        return MagicMock(spec=CollectionPointRepository)

    @pytest.fixture
    def mock_farmer_repo(self) -> MagicMock:
        """Create a mock farmer repository."""
        return MagicMock(spec=FarmerRepository)

    @pytest.fixture
    def mock_id_generator(self) -> MagicMock:
        """Create a mock ID generator."""
        return MagicMock(spec=IDGenerator)

    @pytest.fixture
    def mock_elevation_client(self) -> MagicMock:
        """Create a mock elevation client."""
        return MagicMock(spec=GoogleElevationClient)

    @pytest.fixture
    def mock_dapr_client(self) -> MagicMock:
        """Create a mock Dapr pub/sub client."""
        return MagicMock(spec=DaprPubSubClient)

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        context.abort = AsyncMock(side_effect=grpc.RpcError())
        return context

    @pytest.fixture
    def servicer(
        self,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_dapr_client: MagicMock,
    ) -> PlantationServiceServicer:
        """Create a servicer with mock dependencies."""
        return PlantationServiceServicer(
            factory_repo=mock_factory_repo,
            collection_point_repo=mock_cp_repo,
            farmer_repo=mock_farmer_repo,
            id_generator=mock_id_generator,
            elevation_client=mock_elevation_client,
            dapr_client=mock_dapr_client,
        )

    @pytest.fixture
    def sample_farmer(self) -> Farmer:
        """Create a sample farmer with default preferences for testing."""
        return Farmer(
            id="WM-0001",
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(
                latitude=-0.4, longitude=36.9, altitude_meters=1800.0
            ),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            is_active=True,
            notification_channel=NotificationChannel.SMS,
            interaction_pref=InteractionPreference.TEXT,
            pref_lang=PreferredLanguage.SWAHILI,
        )

    @pytest.fixture
    def sample_farmer_updated(self) -> Farmer:
        """Create a sample farmer with updated preferences (whatsapp + voice)."""
        return Farmer(
            id="WM-0001",
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(
                latitude=-0.4, longitude=36.9, altitude_meters=1800.0
            ),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            is_active=True,
            notification_channel=NotificationChannel.WHATSAPP,
            interaction_pref=InteractionPreference.VOICE,
            pref_lang=PreferredLanguage.ENGLISH,
        )

    # =========================================================================
    # AC #1: Default preferences on farmer creation
    # =========================================================================

    def test_farmer_model_has_default_preferences(self) -> None:
        """AC #1: New farmer model has defaults: notification_channel=sms, interaction_pref=text, pref_lang=sw."""
        farmer = Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            collection_point_id="test-cp",
            region_id="test-region",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9),
            contact=ContactInfo(phone="+254700000000"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="00000000",
        )

        # Verify defaults
        assert farmer.notification_channel == NotificationChannel.SMS
        assert farmer.interaction_pref == InteractionPreference.TEXT
        assert farmer.pref_lang == PreferredLanguage.SWAHILI

    # =========================================================================
    # AC #2: Update communication preferences via API
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_preferences_success(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
        sample_farmer_updated: Farmer,
    ) -> None:
        """AC #2: Can update to whatsapp + voice + en successfully."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_repo.update = AsyncMock(return_value=sample_farmer_updated)

        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_VOICE,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_EN,
        )

        result = await servicer.UpdateCommunicationPreferences(request, mock_context)

        assert result.farmer.id == "WM-0001"
        assert result.farmer.notification_channel == plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP
        assert result.farmer.interaction_pref == plantation_pb2.INTERACTION_PREFERENCE_VOICE
        assert result.farmer.pref_lang == plantation_pb2.PREFERRED_LANGUAGE_EN

        # Verify repository was called with correct updates
        mock_farmer_repo.update.assert_called_once()
        call_args = mock_farmer_repo.update.call_args
        assert call_args[0][0] == "WM-0001"  # farmer_id
        assert call_args[0][1]["notification_channel"] == "whatsapp"
        assert call_args[0][1]["interaction_pref"] == "voice"
        assert call_args[0][1]["pref_lang"] == "en"

    @pytest.mark.asyncio
    async def test_update_preferences_sms_text_luo(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """AC #2: Can update to sms + text + luo (low-literacy farmer who reads)."""
        updated_farmer = Farmer(
            id="WM-0001",
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1800.0),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            is_active=True,
            notification_channel=NotificationChannel.SMS,
            interaction_pref=InteractionPreference.TEXT,
            pref_lang=PreferredLanguage.LUO,
        )

        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_repo.update = AsyncMock(return_value=updated_farmer)

        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_LUO,
        )

        result = await servicer.UpdateCommunicationPreferences(request, mock_context)

        assert result.farmer.notification_channel == plantation_pb2.NOTIFICATION_CHANNEL_SMS
        assert result.farmer.interaction_pref == plantation_pb2.INTERACTION_PREFERENCE_TEXT
        assert result.farmer.pref_lang == plantation_pb2.PREFERRED_LANGUAGE_LUO

    @pytest.mark.asyncio
    async def test_update_preferences_sms_voice_kikuyu(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """Test: SMS notification + voice interaction (low-literacy farmer)."""
        updated_farmer = Farmer(
            id="WM-0001",
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1800.0),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            is_active=True,
            notification_channel=NotificationChannel.SMS,
            interaction_pref=InteractionPreference.VOICE,
            pref_lang=PreferredLanguage.KIKUYU,
        )

        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_repo.update = AsyncMock(return_value=updated_farmer)

        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_VOICE,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_KI,
        )

        result = await servicer.UpdateCommunicationPreferences(request, mock_context)

        assert result.farmer.notification_channel == plantation_pb2.NOTIFICATION_CHANNEL_SMS
        assert result.farmer.interaction_pref == plantation_pb2.INTERACTION_PREFERENCE_VOICE
        assert result.farmer.pref_lang == plantation_pb2.PREFERRED_LANGUAGE_KI

    # =========================================================================
    # AC #3: GetFarmer returns preferences
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_farmer_includes_preferences(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """AC #3: GetFarmer returns current notification_channel, interaction_pref, and pref_lang."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)

        request = plantation_pb2.GetFarmerRequest(id="WM-0001")
        result = await servicer.GetFarmer(request, mock_context)

        assert result.notification_channel == plantation_pb2.NOTIFICATION_CHANNEL_SMS
        assert result.interaction_pref == plantation_pb2.INTERACTION_PREFERENCE_TEXT
        assert result.pref_lang == plantation_pb2.PREFERRED_LANGUAGE_SW

    # =========================================================================
    # AC #4: Invalid preferences fail with validation error
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_channel(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """AC #4: Invalid channel returns INVALID_ARGUMENT with valid options."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)

        # NOTIFICATION_CHANNEL_UNSPECIFIED (0) is invalid
        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_UNSPECIFIED,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_SW,
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCommunicationPreferences(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "sms" in call_args[0][1].lower()
        assert "whatsapp" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_interaction(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """AC #4: Invalid interaction preference returns INVALID_ARGUMENT."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)

        # INTERACTION_PREFERENCE_UNSPECIFIED (0) is invalid
        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_UNSPECIFIED,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_SW,
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCommunicationPreferences(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "text" in call_args[0][1].lower()
        assert "voice" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_language(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """AC #4: Invalid language returns INVALID_ARGUMENT with valid options."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)

        # PREFERRED_LANGUAGE_UNSPECIFIED (0) is invalid
        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-0001",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_UNSPECIFIED,
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCommunicationPreferences(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "swahili" in call_args[0][1].lower()
        assert "kikuyu" in call_args[0][1].lower()
        assert "luo" in call_args[0][1].lower()
        assert "english" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_update_preferences_farmer_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """NOT_FOUND when farmer doesn't exist."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.UpdateCommunicationPreferencesRequest(
            farmer_id="WM-9999",
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_SW,
        )

        with pytest.raises(grpc.RpcError):
            await servicer.UpdateCommunicationPreferences(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND
        assert "WM-9999" in call_args[0][1]

    # =========================================================================
    # Enum tests
    # =========================================================================

    def test_notification_channel_enum_values(self) -> None:
        """Test NotificationChannel enum has correct values."""
        assert NotificationChannel.SMS.value == "sms"
        assert NotificationChannel.WHATSAPP.value == "whatsapp"
        # VOICE is NOT a notification channel (it's an interaction preference)

    def test_interaction_preference_enum_values(self) -> None:
        """Test InteractionPreference enum has correct values."""
        assert InteractionPreference.TEXT.value == "text"
        assert InteractionPreference.VOICE.value == "voice"

    def test_preferred_language_enum_values(self) -> None:
        """Test PreferredLanguage enum has correct values."""
        assert PreferredLanguage.SWAHILI.value == "sw"
        assert PreferredLanguage.KIKUYU.value == "ki"
        assert PreferredLanguage.LUO.value == "luo"
        assert PreferredLanguage.ENGLISH.value == "en"

    def test_preferred_language_display_name(self) -> None:
        """Test PreferredLanguage.get_display_name() method."""
        assert PreferredLanguage.get_display_name("sw") == "Swahili"
        assert PreferredLanguage.get_display_name("ki") == "Kikuyu"
        assert PreferredLanguage.get_display_name("luo") == "Luo"
        assert PreferredLanguage.get_display_name("en") == "English"
        # Unknown value returns the value itself
        assert PreferredLanguage.get_display_name("unknown") == "unknown"

    # =========================================================================
    # Design validation: Semantic correctness
    # =========================================================================

    def test_low_literacy_farmer_scenario(self) -> None:
        """Validate low-literacy farmer use case: SMS trigger + voice consumption."""
        # Low-literacy farmer: receives SMS notification, prefers to call IVR to listen
        farmer = Farmer(
            id="WM-0002",
            first_name="Wanjiku",
            last_name="Kamau",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9),
            contact=ContactInfo(phone="+254700000000"),
            farm_size_hectares=0.5,
            farm_scale=FarmScale.SMALLHOLDER,
            national_id="87654321",
            notification_channel=NotificationChannel.SMS,  # Receives SMS trigger
            interaction_pref=InteractionPreference.VOICE,  # Calls IVR to listen
            pref_lang=PreferredLanguage.KIKUYU,
        )

        # Semantic validation
        assert farmer.notification_channel == NotificationChannel.SMS
        assert farmer.interaction_pref == InteractionPreference.VOICE
        # This farmer will receive: "Your action plan is ready. Call 0800-XXX"
        # Then call IVR and listen to their plan in Kikuyu

    def test_smartphone_farmer_scenario(self) -> None:
        """Validate smartphone farmer use case: WhatsApp + text consumption."""
        # Smartphone farmer: receives full action plan via WhatsApp, reads it
        farmer = Farmer(
            id="WM-0003",
            first_name="James",
            last_name="Ochieng",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9),
            contact=ContactInfo(phone="+254711111111"),
            farm_size_hectares=3.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="11111111",
            notification_channel=NotificationChannel.WHATSAPP,  # Full plan via WhatsApp
            interaction_pref=InteractionPreference.TEXT,  # Reads the message
            pref_lang=PreferredLanguage.ENGLISH,
        )

        # Semantic validation
        assert farmer.notification_channel == NotificationChannel.WHATSAPP
        assert farmer.interaction_pref == InteractionPreference.TEXT
        # This farmer receives full action plan via WhatsApp and reads it
