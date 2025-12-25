"""Unit tests for Factory repository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)


class TestFactoryRepository:
    """Tests for FactoryRepository CRUD operations."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def repository(self, mock_db: MagicMock) -> FactoryRepository:
        """Create a factory repository with mock database."""
        return FactoryRepository(mock_db)

    @pytest.fixture
    def sample_factory(self) -> Factory:
        """Create a sample factory for testing."""
        return Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
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
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_create_factory(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test creating a factory."""
        mock_db["factories"].insert_one = AsyncMock()

        result = await repository.create(sample_factory)

        assert result.id == sample_factory.id
        assert result.name == sample_factory.name
        mock_db["factories"].insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a factory by ID when it exists."""
        factory_doc = sample_factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]
        mock_db["factories"].find_one = AsyncMock(return_value=factory_doc)

        result = await repository.get_by_id("KEN-FAC-001")

        assert result is not None
        assert result.id == "KEN-FAC-001"
        assert result.name == "Test Factory"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a factory by ID when it doesn't exist."""
        mock_db["factories"].find_one = AsyncMock(return_value=None)

        result = await repository.get_by_id("KEN-FAC-999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_code_found(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a factory by code when it exists."""
        factory_doc = sample_factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]
        mock_db["factories"].find_one = AsyncMock(return_value=factory_doc)

        result = await repository.get_by_code("TF")

        assert result is not None
        assert result.code == "TF"
        mock_db["factories"].find_one.assert_called_with({"code": "TF"})

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test getting a factory by code when it doesn't exist."""
        mock_db["factories"].find_one = AsyncMock(return_value=None)

        result = await repository.get_by_code("NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_factory(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test updating a factory."""
        updated_doc = sample_factory.model_dump()
        updated_doc["name"] = "Updated Factory"
        updated_doc["_id"] = updated_doc["id"]
        mock_db["factories"].find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await repository.update(
            "KEN-FAC-001",
            {"name": "Updated Factory"},
        )

        assert result is not None
        assert result.name == "Updated Factory"

    @pytest.mark.asyncio
    async def test_update_factory_not_found(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test updating a factory that doesn't exist."""
        mock_db["factories"].find_one_and_update = AsyncMock(return_value=None)

        result = await repository.update("KEN-FAC-999", {"name": "Updated"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_factory(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test deleting a factory."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db["factories"].delete_one = AsyncMock(return_value=mock_result)

        result = await repository.delete("KEN-FAC-001")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_factory_not_found(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test deleting a factory that doesn't exist."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db["factories"].delete_one = AsyncMock(return_value=mock_result)

        result = await repository.delete("KEN-FAC-999")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_factories(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test listing factories."""
        factory_doc = sample_factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[factory_doc])
        mock_db["factories"].find = MagicMock(return_value=mock_cursor)
        mock_db["factories"].count_documents = AsyncMock(return_value=1)

        factories, next_token, total = await repository.list()

        assert len(factories) == 1
        assert factories[0].id == "KEN-FAC-001"
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_by_region(
        self,
        repository: FactoryRepository,
        sample_factory: Factory,
        mock_db: MagicMock,
    ) -> None:
        """Test listing factories by region."""
        factory_doc = sample_factory.model_dump()
        factory_doc["_id"] = factory_doc["id"]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[factory_doc])
        mock_db["factories"].find = MagicMock(return_value=mock_cursor)
        mock_db["factories"].count_documents = AsyncMock(return_value=1)

        factories, next_token, total = await repository.list_by_region(
            "test-region",
            active_only=True,
        )

        assert len(factories) == 1
        mock_db["factories"].count_documents.assert_called_with(
            {"region_id": "test-region", "is_active": True}
        )

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: FactoryRepository,
        mock_db: MagicMock,
    ) -> None:
        """Test that indexes are created."""
        mock_db["factories"].create_index = AsyncMock()

        await repository.ensure_indexes()

        # Should create 4 indexes
        assert mock_db["factories"].create_index.call_count == 4
