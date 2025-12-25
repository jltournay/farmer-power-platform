"""Unit tests for FarmerRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models.farmer import Farmer, FarmScale
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)


@pytest.fixture
def sample_farmer() -> Farmer:
    """Create a sample farmer for testing."""
    return Farmer(
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


@pytest.fixture
def sample_farmer_doc() -> dict:
    """Create a sample farmer document as stored in MongoDB."""
    return {
        "_id": "WM-0001",
        "id": "WM-0001",
        "first_name": "Wanjiku",
        "last_name": "Kamau",
        "region_id": "nyeri-highland",
        "collection_point_id": "nyeri-highland-cp-001",
        "farm_location": {
            "latitude": -0.4197,
            "longitude": 36.9553,
            "altitude_meters": 1950.0,
        },
        "contact": {"phone": "+254712345678", "email": "", "address": ""},
        "farm_size_hectares": 1.5,
        "farm_scale": "medium",
        "national_id": "12345678",
        "is_active": True,
        "grower_number": None,
        "created_at": datetime(2025, 12, 23, 10, 0, 0, tzinfo=UTC),
        "updated_at": datetime(2025, 12, 23, 10, 0, 0, tzinfo=UTC),
    }


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock MongoDB database."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def farmer_repository(mock_db: MagicMock) -> FarmerRepository:
    """Create a FarmerRepository with mock database."""
    return FarmerRepository(mock_db)


class TestFarmerRepositoryCreate:
    """Tests for FarmerRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_farmer_inserts_document(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer: Farmer,
    ) -> None:
        """Test creating a farmer inserts document into MongoDB."""
        collection = mock_db["farmers"]
        collection.insert_one = AsyncMock()

        result = await farmer_repository.create(sample_farmer)

        collection.insert_one.assert_called_once()
        call_args = collection.insert_one.call_args[0][0]
        assert call_args["_id"] == "WM-0001"
        assert call_args["id"] == "WM-0001"
        assert call_args["first_name"] == "Wanjiku"
        assert result.id == sample_farmer.id


class TestFarmerRepositoryGetById:
    """Tests for FarmerRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test getting a farmer by ID when found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=sample_farmer_doc.copy())

        result = await farmer_repository.get_by_id("WM-0001")

        assert result is not None
        assert result.id == "WM-0001"
        assert result.first_name == "Wanjiku"
        collection.find_one.assert_called_once_with({"_id": "WM-0001"})

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a farmer by ID when not found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=None)

        result = await farmer_repository.get_by_id("WM-9999")

        assert result is None


class TestFarmerRepositoryGetByPhone:
    """Tests for FarmerRepository.get_by_phone method."""

    @pytest.mark.asyncio
    async def test_get_by_phone_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test getting a farmer by phone number when found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=sample_farmer_doc.copy())

        result = await farmer_repository.get_by_phone("+254712345678")

        assert result is not None
        assert result.contact.phone == "+254712345678"
        collection.find_one.assert_called_once_with({"contact.phone": "+254712345678"})

    @pytest.mark.asyncio
    async def test_get_by_phone_not_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a farmer by phone when not found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=None)

        result = await farmer_repository.get_by_phone("+254700000000")

        assert result is None


class TestFarmerRepositoryGetByNationalId:
    """Tests for FarmerRepository.get_by_national_id method."""

    @pytest.mark.asyncio
    async def test_get_by_national_id_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test getting a farmer by national ID when found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=sample_farmer_doc.copy())

        result = await farmer_repository.get_by_national_id("12345678")

        assert result is not None
        assert result.national_id == "12345678"
        collection.find_one.assert_called_once_with({"national_id": "12345678"})

    @pytest.mark.asyncio
    async def test_get_by_national_id_not_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a farmer by national ID when not found."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=None)

        result = await farmer_repository.get_by_national_id("99999999")

        assert result is None


class TestFarmerRepositoryUpdate:
    """Tests for FarmerRepository.update method."""

    @pytest.mark.asyncio
    async def test_update_farmer_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test updating a farmer when found."""
        collection = mock_db["farmers"]
        updated_doc = sample_farmer_doc.copy()
        updated_doc["first_name"] = "Updated"
        collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await farmer_repository.update("WM-0001", {"first_name": "Updated"})

        assert result is not None
        assert result.first_name == "Updated"

    @pytest.mark.asyncio
    async def test_update_farmer_not_found(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test updating a farmer when not found."""
        collection = mock_db["farmers"]
        collection.find_one_and_update = AsyncMock(return_value=None)

        result = await farmer_repository.update("WM-9999", {"first_name": "Updated"})

        assert result is None


class TestFarmerRepositoryList:
    """Tests for FarmerRepository list methods."""

    @pytest.mark.asyncio
    async def test_list_by_collection_point(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test listing farmers by collection point."""
        collection = mock_db["farmers"]
        collection.count_documents = AsyncMock(return_value=1)

        cursor_mock = MagicMock()
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        cursor_mock.limit = MagicMock(return_value=cursor_mock)
        cursor_mock.to_list = AsyncMock(return_value=[sample_farmer_doc.copy()])
        collection.find = MagicMock(return_value=cursor_mock)

        farmers, next_token, total = await farmer_repository.list_by_collection_point(
            "nyeri-highland-cp-001"
        )

        assert len(farmers) == 1
        assert farmers[0].collection_point_id == "nyeri-highland-cp-001"
        assert total == 1
        # Verify filter includes collection_point_id and is_active
        collection.find.assert_called_once()
        call_filters = collection.find.call_args[0][0]
        assert call_filters["collection_point_id"] == "nyeri-highland-cp-001"
        assert call_filters["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_by_region(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test listing farmers by region."""
        collection = mock_db["farmers"]
        collection.count_documents = AsyncMock(return_value=1)

        cursor_mock = MagicMock()
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        cursor_mock.limit = MagicMock(return_value=cursor_mock)
        cursor_mock.to_list = AsyncMock(return_value=[sample_farmer_doc.copy()])
        collection.find = MagicMock(return_value=cursor_mock)

        farmers, next_token, total = await farmer_repository.list_by_region(
            "nyeri-highland"
        )

        assert len(farmers) == 1
        assert farmers[0].region_id == "nyeri-highland"
        call_filters = collection.find.call_args[0][0]
        assert call_filters["region_id"] == "nyeri-highland"

    @pytest.mark.asyncio
    async def test_list_by_farm_scale(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test listing farmers by farm scale."""
        collection = mock_db["farmers"]
        collection.count_documents = AsyncMock(return_value=1)

        cursor_mock = MagicMock()
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        cursor_mock.limit = MagicMock(return_value=cursor_mock)
        cursor_mock.to_list = AsyncMock(return_value=[sample_farmer_doc.copy()])
        collection.find = MagicMock(return_value=cursor_mock)

        farmers, next_token, total = await farmer_repository.list_by_farm_scale(
            "medium"
        )

        assert len(farmers) == 1
        assert farmers[0].farm_scale == FarmScale.MEDIUM
        call_filters = collection.find.call_args[0][0]
        assert call_filters["farm_scale"] == "medium"


class TestFarmerRepositoryDuplicateDetection:
    """Tests for duplicate detection scenarios."""

    @pytest.mark.asyncio
    async def test_phone_duplicate_detection(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test phone duplicate detection returns existing farmer."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=sample_farmer_doc.copy())

        existing = await farmer_repository.get_by_phone("+254712345678")

        assert existing is not None
        assert existing.id == "WM-0001"
        # This simulates the service checking for duplicates before create

    @pytest.mark.asyncio
    async def test_phone_no_duplicate(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test phone duplicate detection returns None when no duplicate."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=None)

        existing = await farmer_repository.get_by_phone("+254799999999")

        assert existing is None

    @pytest.mark.asyncio
    async def test_national_id_duplicate_detection(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
        sample_farmer_doc: dict,
    ) -> None:
        """Test national ID duplicate detection returns existing farmer."""
        collection = mock_db["farmers"]
        collection.find_one = AsyncMock(return_value=sample_farmer_doc.copy())

        existing = await farmer_repository.get_by_national_id("12345678")

        assert existing is not None
        assert existing.id == "WM-0001"


class TestFarmerRepositoryIndexes:
    """Tests for index creation."""

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_required_indexes(
        self,
        farmer_repository: FarmerRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test ensure_indexes creates all required indexes."""
        collection = mock_db["farmers"]
        collection.create_index = AsyncMock()

        await farmer_repository.ensure_indexes()

        # Should create 7 indexes
        assert collection.create_index.call_count == 7

        # Verify specific indexes were created
        index_names = [
            call.kwargs["name"]
            for call in collection.create_index.call_args_list
        ]
        assert "idx_farmer_id" in index_names
        assert "idx_farmer_phone" in index_names
        assert "idx_farmer_national_id" in index_names
        assert "idx_farmer_collection_point" in index_names
        assert "idx_farmer_region" in index_names
        assert "idx_farmer_farm_scale" in index_names
        assert "idx_farmer_active" in index_names
