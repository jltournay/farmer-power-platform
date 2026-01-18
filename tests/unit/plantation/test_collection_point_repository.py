"""Unit tests for CollectionPoint repository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models import (
    CollectionPoint,
    CollectionPointCapacity,
    GeoLocation,
    OperatingHours,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)


class TestCollectionPointRepository:
    """Tests for CollectionPointRepository CRUD operations."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def repository(self, mock_db: MagicMock) -> CollectionPointRepository:
        """Create a collection point repository with mock database."""
        return CollectionPointRepository(mock_db)

    @pytest.fixture
    def sample_cp(self) -> CollectionPoint:
        """Create a sample collection point for testing."""
        return CollectionPoint(
            id="test-region-cp-001",
            name="Test Collection Point",
            factory_id="KEN-FAC-001",
            location=GeoLocation(
                latitude=-0.5,
                longitude=36.5,
                altitude_meters=1500.0,
            ),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700000000",
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_create_collection_point(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test creating a collection point."""
        mock_db["collection_points"].insert_one = AsyncMock()

        result = await repository.create(sample_cp)

        assert result.id == sample_cp.id
        assert result.name == sample_cp.name
        mock_db["collection_points"].insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a collection point by ID when it exists."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]
        mock_db["collection_points"].find_one = AsyncMock(return_value=cp_doc)

        result = await repository.get_by_id("test-region-cp-001")

        assert result is not None
        assert result.id == "test-region-cp-001"
        assert result.name == "Test Collection Point"
        assert result.factory_id == "KEN-FAC-001"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a collection point by ID when it doesn't exist."""
        mock_db["collection_points"].find_one = AsyncMock(return_value=None)

        result = await repository.get_by_id("nonexistent-cp-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_factory(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test listing collection points by factory_id."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        cps, next_token, total = await repository.list_by_factory("KEN-FAC-001")

        assert len(cps) == 1
        assert cps[0].factory_id == "KEN-FAC-001"
        mock_db["collection_points"].count_documents.assert_called_with({"factory_id": "KEN-FAC-001"})

    @pytest.mark.asyncio
    async def test_list_by_factory_active_only(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test listing only active collection points for a factory."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        await repository.list_by_factory("KEN-FAC-001", active_only=True)

        mock_db["collection_points"].count_documents.assert_called_with(
            {"factory_id": "KEN-FAC-001", "status": "active"}
        )

    @pytest.mark.asyncio
    async def test_list_by_region(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test listing collection points by region."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        cps, _, _ = await repository.list_by_region("test-region")

        assert len(cps) == 1
        mock_db["collection_points"].count_documents.assert_called_with({"region_id": "test-region"})

    @pytest.mark.asyncio
    async def test_list_by_clerk(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test listing collection points by clerk_id."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        cps, _, _ = await repository.list_by_clerk("CLK-001")

        assert len(cps) == 1
        mock_db["collection_points"].count_documents.assert_called_with({"clerk_id": "CLK-001"})

    @pytest.mark.asyncio
    async def test_update_collection_point(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test updating a collection point."""
        updated_doc = sample_cp.model_dump()
        updated_doc["clerk_id"] = "NEW-CLK-001"
        updated_doc["_id"] = updated_doc["id"]
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await repository.update(
            "test-region-cp-001",
            {"clerk_id": "NEW-CLK-001"},
        )

        assert result is not None
        assert result.clerk_id == "NEW-CLK-001"

    @pytest.mark.asyncio
    async def test_update_operating_hours(
        self,
        repository: CollectionPointRepository,
        sample_cp: CollectionPoint,
        mock_db: MagicMock,
    ) -> None:
        """Test updating operating hours."""
        updated_doc = sample_cp.model_dump()
        updated_doc["operating_hours"]["weekdays"] = "07:00-12:00"
        updated_doc["_id"] = updated_doc["id"]
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await repository.update(
            "test-region-cp-001",
            {"operating_hours": {"weekdays": "07:00-12:00", "weekends": "08:00-10:00"}},
        )

        assert result is not None
        assert result.operating_hours.weekdays == "07:00-12:00"

    @pytest.mark.asyncio
    async def test_delete_collection_point(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test deleting a collection point."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db["collection_points"].delete_one = AsyncMock(return_value=mock_result)

        result = await repository.delete("test-region-cp-001")

        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that indexes are created."""
        mock_db["collection_points"].create_index = AsyncMock()

        await repository.ensure_indexes()

        # Should create 6 indexes (Story 9.5a: added farmer_ids index)
        assert mock_db["collection_points"].create_index.call_count == 6


class TestCollectionPointFarmerAssignment:
    """Tests for farmer assignment operations (Story 9.5a).

    Tests the N:M relationship between Farmers and Collection Points.
    """

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def repository(self, mock_db: MagicMock) -> CollectionPointRepository:
        """Create a collection point repository with mock database."""
        return CollectionPointRepository(mock_db)

    @pytest.fixture
    def sample_cp(self) -> CollectionPoint:
        """Create a sample collection point for testing."""
        return CollectionPoint(
            id="test-region-cp-001",
            name="Test Collection Point",
            factory_id="KEN-FAC-001",
            location=GeoLocation(
                latitude=-0.5,
                longitude=36.5,
                altitude_meters=1500.0,
            ),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700000000",
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
            farmer_ids=[],  # Story 9.5a: N:M relationship
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_cp_with_farmers(self, sample_cp: CollectionPoint) -> CollectionPoint:
        """Create a sample collection point with farmers assigned."""
        return CollectionPoint(
            id=sample_cp.id,
            name=sample_cp.name,
            factory_id=sample_cp.factory_id,
            location=sample_cp.location,
            region_id=sample_cp.region_id,
            clerk_id=sample_cp.clerk_id,
            clerk_phone=sample_cp.clerk_phone,
            operating_hours=sample_cp.operating_hours,
            collection_days=sample_cp.collection_days,
            capacity=sample_cp.capacity,
            status=sample_cp.status,
            farmer_ids=["WM-0001", "WM-0002"],  # Story 9.5a: farmers assigned
            created_at=sample_cp.created_at,
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_add_farmer_success(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
        sample_cp_with_farmers: CollectionPoint,
    ) -> None:
        """Test adding a farmer to a collection point."""
        cp_doc = sample_cp_with_farmers.model_dump()
        cp_doc["_id"] = cp_doc["id"]
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=cp_doc)

        result = await repository.add_farmer("test-region-cp-001", "WM-0001")

        assert result is not None
        assert "WM-0001" in result.farmer_ids

        # Verify $addToSet is used for idempotency
        call_args = mock_db["collection_points"].find_one_and_update.call_args
        update_doc = call_args[0][1]
        assert "$addToSet" in update_doc
        assert update_doc["$addToSet"]["farmer_ids"] == "WM-0001"

    @pytest.mark.asyncio
    async def test_add_farmer_cp_not_found(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test adding a farmer to a non-existent collection point."""
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=None)

        result = await repository.add_farmer("nonexistent-cp", "WM-0001")

        assert result is None

    @pytest.mark.asyncio
    async def test_remove_farmer_success(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
        sample_cp: CollectionPoint,
    ) -> None:
        """Test removing a farmer from a collection point."""
        cp_doc = sample_cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=cp_doc)

        result = await repository.remove_farmer("test-region-cp-001", "WM-0001")

        assert result is not None

        # Verify $pull is used for idempotency
        call_args = mock_db["collection_points"].find_one_and_update.call_args
        update_doc = call_args[0][1]
        assert "$pull" in update_doc
        assert update_doc["$pull"]["farmer_ids"] == "WM-0001"

    @pytest.mark.asyncio
    async def test_remove_farmer_cp_not_found(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test removing a farmer from a non-existent collection point."""
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=None)

        result = await repository.remove_farmer("nonexistent-cp", "WM-0001")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_farmer_success(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
        sample_cp_with_farmers: CollectionPoint,
    ) -> None:
        """Test listing collection points by farmer ID."""
        cp_doc = sample_cp_with_farmers.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        cps, next_token, total = await repository.list_by_farmer("WM-0001")

        assert len(cps) == 1
        assert "WM-0001" in cps[0].farmer_ids
        assert total == 1

        # Verify query uses farmer_id in farmer_ids
        call_args = mock_db["collection_points"].count_documents.call_args
        query_filter = call_args[0][0]
        assert query_filter["farmer_ids"] == "WM-0001"

    @pytest.mark.asyncio
    async def test_list_by_farmer_empty(
        self,
        repository: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test listing collection points for farmer with no assignments."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=0)

        cps, next_token, total = await repository.list_by_farmer("WM-9999")

        assert len(cps) == 0
        assert total == 0
