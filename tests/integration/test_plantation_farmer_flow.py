"""Integration tests for Farmer registration flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from plantation_model.domain.events.farmer_events import FarmerRegisteredEvent
from plantation_model.domain.models.farmer import Farmer, FarmScale
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from plantation_model.infrastructure.google_elevation import (
    GoogleElevationClient,
    assign_region_from_altitude,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)


@pytest.mark.integration
class TestFarmerRegistrationFlow:
    """Integration tests for Farmer registration lifecycle."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def farmer_repo(self, mock_db: MagicMock) -> FarmerRepository:
        """Create a farmer repository with mock database."""
        return FarmerRepository(mock_db)

    @pytest.fixture
    def id_generator(self, mock_db: MagicMock) -> IDGenerator:
        """Create an ID generator with mock database."""
        return IDGenerator(mock_db)

    @pytest.fixture
    def dapr_client(self) -> DaprPubSubClient:
        """Create a Dapr pub/sub client."""
        return DaprPubSubClient(dapr_host="localhost", dapr_http_port=3500)

    @pytest.mark.asyncio
    async def test_full_farmer_registration_flow(
        self,
        farmer_repo: FarmerRepository,
        id_generator: IDGenerator,
        mock_db: MagicMock,
    ) -> None:
        """Test complete Farmer registration flow with ID generation, region assignment, and persistence."""
        # 1. Generate Farmer ID
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "farmer", "seq": 1}
        )
        farmer_id = await id_generator.generate_farmer_id()
        assert farmer_id == "WM-0001"

        # 2. Determine region based on GPS + altitude
        latitude = -0.4197  # Nyeri County
        longitude = 36.9553
        altitude = 1950.0  # Highland altitude
        region_id = assign_region_from_altitude(latitude, longitude, altitude)
        assert region_id == "nyeri-highland"

        # 3. Calculate farm scale
        farm_size_hectares = 1.5
        farm_scale = FarmScale.from_hectares(farm_size_hectares)
        assert farm_scale == FarmScale.MEDIUM

        # 4. Create Farmer entity
        farmer = Farmer(
            id=farmer_id,
            first_name="Wanjiku",
            last_name="Kamau",
            region_id=region_id,
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(
                latitude=latitude,
                longitude=longitude,
                altitude_meters=altitude,
            ),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=farm_size_hectares,
            farm_scale=farm_scale,
            national_id="12345678",
        )

        # 5. Check for duplicate phone (should not exist)
        mock_db["farmers"].find_one = AsyncMock(return_value=None)
        existing = await farmer_repo.get_by_phone("+254712345678")
        assert existing is None

        # 6. Persist farmer
        mock_db["farmers"].insert_one = AsyncMock()
        created = await farmer_repo.create(farmer)
        assert created.id == farmer_id
        mock_db["farmers"].insert_one.assert_called_once()

        # 7. Verify farmer can be retrieved
        farmer_doc = farmer.model_dump()
        farmer_doc["_id"] = farmer_doc["id"]
        mock_db["farmers"].find_one = AsyncMock(return_value=farmer_doc)
        retrieved = await farmer_repo.get_by_id(farmer_id)
        assert retrieved is not None
        assert retrieved.first_name == "Wanjiku"
        assert retrieved.region_id == "nyeri-highland"
        assert retrieved.farm_scale == FarmScale.MEDIUM

    @pytest.mark.asyncio
    async def test_duplicate_phone_rejection(
        self,
        farmer_repo: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that duplicate phone numbers are detected before registration."""
        # Existing farmer with phone
        existing_farmer = Farmer(
            id="WM-0001",
            first_name="Existing",
            last_name="Farmer",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1900),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )
        existing_doc = existing_farmer.model_dump()
        existing_doc["_id"] = existing_doc["id"]
        existing_doc["contact"]["email"] = ""
        existing_doc["contact"]["address"] = ""

        # Setup mock to return existing farmer
        mock_db["farmers"].find_one = AsyncMock(return_value=existing_doc)

        # Check for duplicate phone
        existing = await farmer_repo.get_by_phone("+254712345678")
        assert existing is not None
        assert existing.id == "WM-0001"

        # A new farmer registration with same phone should be blocked
        # (this logic would be in the service layer)

    @pytest.mark.asyncio
    async def test_duplicate_national_id_rejection(
        self,
        farmer_repo: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that duplicate national IDs are detected before registration."""
        # Existing farmer with national_id
        existing_farmer = Farmer(
            id="WM-0001",
            first_name="Existing",
            last_name="Farmer",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1900),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )
        existing_doc = existing_farmer.model_dump()
        existing_doc["_id"] = existing_doc["id"]
        existing_doc["contact"]["email"] = ""
        existing_doc["contact"]["address"] = ""

        mock_db["farmers"].find_one = AsyncMock(return_value=existing_doc)

        # Check for duplicate national ID
        existing = await farmer_repo.get_by_national_id("12345678")
        assert existing is not None
        assert existing.national_id == "12345678"

    @pytest.mark.asyncio
    async def test_region_auto_assignment_highland(self) -> None:
        """Test region auto-assignment for highland altitude."""
        # Nyeri coordinates with highland altitude (>= 1800m)
        region = assign_region_from_altitude(-0.4197, 36.9553, 1950.0)
        assert region == "nyeri-highland"

        # Kericho with highland altitude
        region = assign_region_from_altitude(-0.5, 35.5, 2000.0)
        assert region == "kericho-highland"

    @pytest.mark.asyncio
    async def test_region_auto_assignment_midland(self) -> None:
        """Test region auto-assignment for midland altitude."""
        # Nandi coordinates with midland altitude (1400-1800m)
        region = assign_region_from_altitude(0.2, 35.0, 1600.0)
        assert region == "nandi-midland"

    @pytest.mark.asyncio
    async def test_region_auto_assignment_lowland(self) -> None:
        """Test region auto-assignment for lowland altitude."""
        # Kisii coordinates with lowland altitude (< 1400m)
        region = assign_region_from_altitude(-0.7, 34.8, 1200.0)
        assert region == "kisii-lowland"

    @pytest.mark.asyncio
    async def test_elevation_api_with_mock_response(self) -> None:
        """Test elevation client with mocked API response."""
        with patch(
            "plantation_model.infrastructure.google_elevation.httpx.AsyncClient"
        ) as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "OK",
                "results": [{"elevation": 1950.5}],
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            client = GoogleElevationClient("test-api-key")
            altitude = await client.get_altitude(-0.4197, 36.9553)

            assert altitude == 1950.5

    @pytest.mark.asyncio
    async def test_farm_scale_auto_calculation(self) -> None:
        """Test that farm scale is automatically calculated from hectares."""
        # Smallholder: < 1 hectare
        assert FarmScale.from_hectares(0.5) == FarmScale.SMALLHOLDER
        assert FarmScale.from_hectares(0.99) == FarmScale.SMALLHOLDER

        # Medium: 1-5 hectares
        assert FarmScale.from_hectares(1.0) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(3.0) == FarmScale.MEDIUM
        assert FarmScale.from_hectares(5.0) == FarmScale.MEDIUM

        # Estate: > 5 hectares
        assert FarmScale.from_hectares(5.1) == FarmScale.ESTATE
        assert FarmScale.from_hectares(100.0) == FarmScale.ESTATE

    @pytest.mark.asyncio
    async def test_farmer_event_publishing(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test FarmerRegisteredEvent publishing to Dapr."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        # Mock successful publish
        with patch(
            "plantation_model.infrastructure.dapr_client.httpx.AsyncClient"
        ) as mock_client_class:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "farmer-events" in str(call_args)

    @pytest.mark.asyncio
    async def test_farmer_list_by_collection_point(
        self,
        farmer_repo: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test listing farmers by collection point."""
        farmer1 = Farmer(
            id="WM-0001",
            first_name="Farmer",
            last_name="One",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1900),
            contact=ContactInfo(phone="+254711111111"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="11111111",
        )
        farmer2 = Farmer(
            id="WM-0002",
            first_name="Farmer",
            last_name="Two",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(latitude=-0.5, longitude=36.9, altitude_meters=1850),
            contact=ContactInfo(phone="+254722222222"),
            farm_size_hectares=2.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="22222222",
        )

        docs = []
        for f in [farmer1, farmer2]:
            doc = f.model_dump()
            doc["_id"] = doc["id"]
            doc["contact"]["email"] = ""
            doc["contact"]["address"] = ""
            docs.append(doc)

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=docs)
        mock_db["farmers"].find = MagicMock(return_value=mock_cursor)
        mock_db["farmers"].count_documents = AsyncMock(return_value=2)

        farmers, _, total = await farmer_repo.list_by_collection_point(
            "nyeri-highland-cp-001"
        )

        assert total == 2
        assert len(farmers) == 2
        assert all(f.collection_point_id == "nyeri-highland-cp-001" for f in farmers)

    @pytest.mark.asyncio
    async def test_farmer_update_flow(
        self,
        farmer_repo: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test farmer update flow."""
        # Original farmer
        farmer = Farmer(
            id="WM-0001",
            first_name="Original",
            last_name="Farmer",
            region_id="nyeri-highland",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1900),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.0,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
        )

        # Updated farmer doc
        updated_doc = farmer.model_dump()
        updated_doc["first_name"] = "Updated"
        updated_doc["farm_size_hectares"] = 2.5
        updated_doc["farm_scale"] = "medium"
        updated_doc["_id"] = updated_doc["id"]
        updated_doc["contact"]["email"] = ""
        updated_doc["contact"]["address"] = ""

        mock_db["farmers"].find_one_and_update = AsyncMock(return_value=updated_doc)

        updated = await farmer_repo.update(
            "WM-0001",
            {"first_name": "Updated", "farm_size_hectares": 2.5},
        )

        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.farm_size_hectares == 2.5
