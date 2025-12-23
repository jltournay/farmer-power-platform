"""Integration tests for Factory CRUD flow."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.google_elevation import GoogleElevationClient


@pytest.mark.integration
class TestFactoryCRUDFlow:
    """Integration tests for Factory CRUD lifecycle."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def factory_repo(self, mock_db: MagicMock) -> FactoryRepository:
        """Create a factory repository with mock database."""
        return FactoryRepository(mock_db)

    @pytest.fixture
    def id_generator(self, mock_db: MagicMock) -> IDGenerator:
        """Create an ID generator with mock database."""
        return IDGenerator(mock_db)

    @pytest.fixture
    def elevation_client(self) -> GoogleElevationClient:
        """Create a mock elevation client."""
        client = GoogleElevationClient("")
        return client

    @pytest.mark.asyncio
    async def test_full_factory_lifecycle(
        self,
        factory_repo: FactoryRepository,
        id_generator: IDGenerator,
        mock_db: MagicMock,
    ) -> None:
        """Test complete Factory create -> read -> update -> delete flow."""
        # Setup mocks for ID generation
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "factory", "seq": 1}
        )

        # 1. Generate ID
        factory_id = await id_generator.generate_factory_id()
        assert factory_id == "KEN-FAC-001"

        # 2. Create Factory
        factory = Factory(
            id=factory_id,
            name="Integration Test Factory",
            code="ITF",
            region_id="test-region",
            location=GeoLocation(
                latitude=-0.5,
                longitude=36.5,
                altitude_meters=1500.0,
            ),
            contact=ContactInfo(
                phone="+254700000000",
                email="test@factory.co.ke",
                address="Test Address",
            ),
            processing_capacity_kg=50000,
        )

        mock_db["factories"].insert_one = AsyncMock()
        await factory_repo.create(factory)
        mock_db["factories"].insert_one.assert_called_once()

        # 3. Read Factory
        factory_doc = factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]
        mock_db["factories"].find_one = AsyncMock(return_value=factory_doc)

        retrieved = await factory_repo.get_by_id(factory_id)
        assert retrieved is not None
        assert retrieved.id == factory_id
        assert retrieved.name == "Integration Test Factory"

        # 4. Update Factory
        updated_doc = factory.model_dump()
        updated_doc["name"] = "Updated Factory Name"
        updated_doc["processing_capacity_kg"] = 75000
        updated_doc["_id"] = updated_doc["id"]
        mock_db["factories"].find_one_and_update = AsyncMock(return_value=updated_doc)

        updated = await factory_repo.update(
            factory_id,
            {"name": "Updated Factory Name", "processing_capacity_kg": 75000},
        )
        assert updated is not None
        assert updated.name == "Updated Factory Name"
        assert updated.processing_capacity_kg == 75000

        # 5. Delete Factory
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db["factories"].delete_one = AsyncMock(return_value=mock_result)

        deleted = await factory_repo.delete(factory_id)
        assert deleted is True

        # 6. Verify deletion
        mock_db["factories"].find_one = AsyncMock(return_value=None)
        retrieved_after_delete = await factory_repo.get_by_id(factory_id)
        assert retrieved_after_delete is None

    @pytest.mark.asyncio
    async def test_factory_duplicate_code_prevention(
        self,
        factory_repo: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that duplicate factory codes are detected."""
        # Setup existing factory with code
        existing_factory = Factory(
            id="KEN-FAC-001",
            name="Existing Factory",
            code="EXF",
            region_id="test-region",
            location=GeoLocation(latitude=0, longitude=0),
        )
        existing_doc = existing_factory.model_dump()
        existing_doc["_id"] = existing_doc["id"]

        mock_db["factories"].find_one = AsyncMock(return_value=existing_doc)

        # Try to get by code should return existing
        result = await factory_repo.get_by_code("EXF")
        assert result is not None
        assert result.code == "EXF"

    @pytest.mark.asyncio
    async def test_factory_list_by_region(
        self,
        factory_repo: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test listing factories by region."""
        factory1 = Factory(
            id="KEN-FAC-001",
            name="Factory 1",
            code="F1",
            region_id="nyeri-highland",
            location=GeoLocation(latitude=-0.4, longitude=36.9),
        )
        factory2 = Factory(
            id="KEN-FAC-002",
            name="Factory 2",
            code="F2",
            region_id="nyeri-highland",
            location=GeoLocation(latitude=-0.5, longitude=37.0),
        )

        docs = []
        for f in [factory1, factory2]:
            doc = f.model_dump()
            doc["_id"] = doc["id"]
            docs.append(doc)

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=docs)
        mock_db["factories"].find = MagicMock(return_value=mock_cursor)
        mock_db["factories"].count_documents = AsyncMock(return_value=2)

        factories, _, total = await factory_repo.list_by_region("nyeri-highland")

        assert total == 2
        assert len(factories) == 2
        assert all(f.region_id == "nyeri-highland" for f in factories)

    @pytest.mark.asyncio
    async def test_elevation_api_integration(
        self,
        elevation_client: GoogleElevationClient,
    ) -> None:
        """Test elevation client returns default when no API key."""
        # Without API key, should return None
        result = await elevation_client.get_altitude(-0.5, 36.5)
        assert result is None  # No API key configured

    @pytest.mark.asyncio
    async def test_elevation_api_with_mock_response(self) -> None:
        """Test elevation client with mocked API response."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "OK",
                "results": [{"elevation": 1850.5}],
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                client = GoogleElevationClient("test-api-key")
                altitude = await client.get_altitude(-0.5, 36.5)

                assert altitude == 1850.5
