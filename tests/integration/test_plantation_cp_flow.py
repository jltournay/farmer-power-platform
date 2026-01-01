"""Integration tests for CollectionPoint CRUD flow."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models import (
    CollectionPoint,
    CollectionPointCapacity,
    Factory,
    GeoLocation,
    OperatingHours,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)


@pytest.mark.integration
class TestCollectionPointCRUDFlow:
    """Integration tests for CollectionPoint CRUD lifecycle."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def cp_repo(self, mock_db: MagicMock) -> CollectionPointRepository:
        """Create a collection point repository with mock database."""
        return CollectionPointRepository(mock_db)

    @pytest.fixture
    def factory_repo(self, mock_db: MagicMock) -> FactoryRepository:
        """Create a factory repository with mock database."""
        return FactoryRepository(mock_db)

    @pytest.fixture
    def id_generator(self, mock_db: MagicMock) -> IDGenerator:
        """Create an ID generator with mock database."""
        return IDGenerator(mock_db)

    @pytest.mark.asyncio
    async def test_full_collection_point_lifecycle(
        self,
        cp_repo: CollectionPointRepository,
        id_generator: IDGenerator,
        mock_db: MagicMock,
    ) -> None:
        """Test complete CollectionPoint create -> read -> update -> delete flow."""
        # Setup mocks for ID generation
        mock_db["id_counters"].find_one_and_update = AsyncMock(return_value={"_id": "cp_nyeri-highland", "seq": 1})

        # 1. Generate ID
        cp_id = await id_generator.generate_collection_point_id("nyeri-highland")
        assert cp_id == "nyeri-highland-cp-001"

        # 2. Create CollectionPoint
        cp = CollectionPoint(
            id=cp_id,
            name="Test Collection Point",
            factory_id="KEN-FAC-001",
            location=GeoLocation(
                latitude=-0.45,
                longitude=36.95,
                altitude_meters=1800.0,
            ),
            region_id="nyeri-highland",
            clerk_id="CLK-001",
            clerk_phone="+254700111222",
            operating_hours=OperatingHours(
                weekdays="06:00-10:00",
                weekends="07:00-09:00",
            ),
            collection_days=["mon", "wed", "fri"],
            capacity=CollectionPointCapacity(
                max_daily_kg=5000,
                storage_type="covered_shed",
                has_weighing_scale=True,
                has_qc_device=False,
            ),
            status="active",
        )

        mock_db["collection_points"].insert_one = AsyncMock()
        await cp_repo.create(cp)
        mock_db["collection_points"].insert_one.assert_called_once()

        # 3. Read CollectionPoint
        cp_doc = cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]
        mock_db["collection_points"].find_one = AsyncMock(return_value=cp_doc)

        retrieved = await cp_repo.get_by_id(cp_id)
        assert retrieved is not None
        assert retrieved.id == cp_id
        assert retrieved.name == "Test Collection Point"
        assert retrieved.factory_id == "KEN-FAC-001"

        # 4. Update CollectionPoint
        updated_doc = cp.model_dump()
        updated_doc["clerk_id"] = "CLK-002"
        updated_doc["status"] = "inactive"
        updated_doc["_id"] = updated_doc["id"]
        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=updated_doc)

        updated = await cp_repo.update(
            cp_id,
            {"clerk_id": "CLK-002", "status": "inactive"},
        )
        assert updated is not None
        assert updated.clerk_id == "CLK-002"
        assert updated.status == "inactive"

        # 5. Delete CollectionPoint
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db["collection_points"].delete_one = AsyncMock(return_value=mock_result)

        deleted = await cp_repo.delete(cp_id)
        assert deleted is True

        # 6. Verify deletion
        mock_db["collection_points"].find_one = AsyncMock(return_value=None)
        retrieved_after_delete = await cp_repo.get_by_id(cp_id)
        assert retrieved_after_delete is None

    @pytest.mark.asyncio
    async def test_collection_point_factory_relationship(
        self,
        cp_repo: CollectionPointRepository,
        factory_repo: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that collection points are correctly linked to factories."""
        # Setup factory
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="nyeri-highland",
            location=GeoLocation(latitude=-0.5, longitude=36.9),
        )
        factory_doc = factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]

        # Setup collection points for this factory
        cp1 = CollectionPoint(
            id="nyeri-highland-cp-001",
            name="CP 1",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.45, longitude=36.95),
            region_id="nyeri-highland",
        )
        cp2 = CollectionPoint(
            id="nyeri-highland-cp-002",
            name="CP 2",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.48, longitude=36.92),
            region_id="nyeri-highland",
        )

        cp_docs = []
        for cp in [cp1, cp2]:
            doc = cp.model_dump()
            doc["_id"] = doc["id"]
            cp_docs.append(doc)

        # Mock factory exists check
        mock_db["factories"].find_one = AsyncMock(return_value=factory_doc)

        # Mock list collection points by factory
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=cp_docs)
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=2)

        # Verify factory exists
        factory_result = await factory_repo.get_by_id("KEN-FAC-001")
        assert factory_result is not None

        # List collection points for this factory
        cps, _, total = await cp_repo.list_by_factory("KEN-FAC-001")

        assert total == 2
        assert len(cps) == 2
        assert all(cp.factory_id == "KEN-FAC-001" for cp in cps)

    @pytest.mark.asyncio
    async def test_collection_point_status_filtering(
        self,
        cp_repo: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test filtering collection points by status."""
        # Setup active and inactive collection points
        active_cp = CollectionPoint(
            id="region-cp-001",
            name="Active CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.9),
            region_id="test-region",
            status="active",
        )
        inactive_cp = CollectionPoint(
            id="region-cp-002",
            name="Inactive CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.6, longitude=36.8),
            region_id="test-region",
            status="inactive",
        )

        active_doc = active_cp.model_dump()
        active_doc["_id"] = active_doc["id"]

        # Mock returning only active CPs
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[active_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        # List only active collection points
        cps, _, total = await cp_repo.list_by_factory("KEN-FAC-001", active_only=True)

        assert total == 1
        assert len(cps) == 1
        assert cps[0].status == "active"

        # Verify the filter was applied correctly
        mock_db["collection_points"].count_documents.assert_called_with(
            {"factory_id": "KEN-FAC-001", "status": "active"}
        )

    @pytest.mark.asyncio
    async def test_collection_point_region_isolation(
        self,
        cp_repo: CollectionPointRepository,
        id_generator: IDGenerator,
        mock_db: MagicMock,
    ) -> None:
        """Test that collection point IDs are region-specific."""
        # Generate IDs for different regions
        mock_db["id_counters"].find_one_and_update = AsyncMock(return_value={"_id": "cp_region-a", "seq": 5})
        cp_id_a = await id_generator.generate_collection_point_id("region-a")

        mock_db["id_counters"].find_one_and_update = AsyncMock(return_value={"_id": "cp_region-b", "seq": 1})
        cp_id_b = await id_generator.generate_collection_point_id("region-b")

        # IDs should include region prefix
        assert cp_id_a.startswith("region-a-")
        assert cp_id_b.startswith("region-b-")
        assert cp_id_a == "region-a-cp-005"
        assert cp_id_b == "region-b-cp-001"

    @pytest.mark.asyncio
    async def test_collection_point_clerk_assignment(
        self,
        cp_repo: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test listing collection points by clerk."""
        cp = CollectionPoint(
            id="region-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.9),
            region_id="test-region",
            clerk_id="CLK-001",
            clerk_phone="+254700000000",
        )
        cp_doc = cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[cp_doc])
        mock_db["collection_points"].find = MagicMock(return_value=mock_cursor)
        mock_db["collection_points"].count_documents = AsyncMock(return_value=1)

        # List collection points by clerk
        cps, _, total = await cp_repo.list_by_clerk("CLK-001")

        assert total == 1
        assert len(cps) == 1
        assert cps[0].clerk_id == "CLK-001"

        # Verify correct filter
        mock_db["collection_points"].count_documents.assert_called_with({"clerk_id": "CLK-001"})

    @pytest.mark.asyncio
    async def test_collection_point_capacity_and_equipment(
        self,
        cp_repo: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test collection point capacity and equipment tracking."""
        cp = CollectionPoint(
            id="region-cp-001",
            name="Full Equipment CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.9),
            region_id="test-region",
            capacity=CollectionPointCapacity(
                max_daily_kg=10000,
                storage_type="cold_storage",
                has_weighing_scale=True,
                has_qc_device=True,
            ),
        )
        cp_doc = cp.model_dump()
        cp_doc["_id"] = cp_doc["id"]

        mock_db["collection_points"].find_one = AsyncMock(return_value=cp_doc)

        result = await cp_repo.get_by_id("region-cp-001")

        assert result is not None
        assert result.capacity.max_daily_kg == 10000
        assert result.capacity.storage_type == "cold_storage"
        assert result.capacity.has_weighing_scale is True
        assert result.capacity.has_qc_device is True

    @pytest.mark.asyncio
    async def test_update_operating_hours(
        self,
        cp_repo: CollectionPointRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test updating collection point operating hours."""
        cp = CollectionPoint(
            id="region-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.5, longitude=36.9),
            region_id="test-region",
            operating_hours=OperatingHours(
                weekdays="06:00-10:00",
                weekends="07:00-09:00",
            ),
        )

        updated_doc = cp.model_dump()
        updated_doc["operating_hours"]["weekdays"] = "05:00-11:00"
        updated_doc["operating_hours"]["weekends"] = "06:00-10:00"
        updated_doc["_id"] = updated_doc["id"]

        mock_db["collection_points"].find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await cp_repo.update(
            "region-cp-001",
            {
                "operating_hours": {
                    "weekdays": "05:00-11:00",
                    "weekends": "06:00-10:00",
                }
            },
        )

        assert result is not None
        assert result.operating_hours.weekdays == "05:00-11:00"
        assert result.operating_hours.weekends == "06:00-10:00"
