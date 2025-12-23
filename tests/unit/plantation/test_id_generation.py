"""Unit tests for ID generation utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from plantation_model.domain.models.id_generator import IDGenerator


class TestIDGenerator:
    """Tests for ID generation."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create a mock MongoDB database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def id_generator(self, mock_db: MagicMock) -> IDGenerator:
        """Create an ID generator with mock database."""
        return IDGenerator(mock_db)

    @pytest.mark.asyncio
    async def test_generate_factory_id_first(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test generating the first factory ID."""
        # Mock the counter returning seq=1
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "factory", "seq": 1}
        )

        factory_id = await id_generator.generate_factory_id()

        assert factory_id == "KEN-FAC-001"

    @pytest.mark.asyncio
    async def test_generate_factory_id_sequence(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test factory ID sequence numbering."""
        # Mock counter returning seq=42
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "factory", "seq": 42}
        )

        factory_id = await id_generator.generate_factory_id()

        assert factory_id == "KEN-FAC-042"

    @pytest.mark.asyncio
    async def test_generate_factory_id_triple_digits(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test factory ID with triple-digit sequence."""
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "factory", "seq": 999}
        )

        factory_id = await id_generator.generate_factory_id()

        assert factory_id == "KEN-FAC-999"

    @pytest.mark.asyncio
    async def test_generate_collection_point_id_first(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test generating the first collection point ID for a region."""
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "cp_nyeri-highland", "seq": 1}
        )

        cp_id = await id_generator.generate_collection_point_id("nyeri-highland")

        assert cp_id == "nyeri-highland-cp-001"

    @pytest.mark.asyncio
    async def test_generate_collection_point_id_different_regions(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test collection point IDs are unique per region."""
        # First region
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "cp_region-a", "seq": 5}
        )
        cp_id_a = await id_generator.generate_collection_point_id("region-a")

        # Second region (reset sequence)
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "cp_region-b", "seq": 1}
        )
        cp_id_b = await id_generator.generate_collection_point_id("region-b")

        assert cp_id_a == "region-a-cp-005"
        assert cp_id_b == "region-b-cp-001"

    @pytest.mark.asyncio
    async def test_generate_collection_point_id_sequence(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test collection point ID sequence numbering."""
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "cp_test-region", "seq": 123}
        )

        cp_id = await id_generator.generate_collection_point_id("test-region")

        assert cp_id == "test-region-cp-123"

    @pytest.mark.asyncio
    async def test_factory_id_format(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test factory ID format is correct (KEN-FAC-XXX)."""
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "factory", "seq": 7}
        )

        factory_id = await id_generator.generate_factory_id()

        # Verify format
        assert factory_id.startswith("KEN-FAC-")
        assert len(factory_id) == 11  # KEN-FAC-XXX
        assert factory_id[-3:].isdigit()

    @pytest.mark.asyncio
    async def test_collection_point_id_format(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test collection point ID format is correct ({region}-cp-XXX)."""
        mock_db["id_counters"].find_one_and_update = AsyncMock(
            return_value={"_id": "cp_test", "seq": 15}
        )

        cp_id = await id_generator.generate_collection_point_id("test")

        # Verify format
        assert cp_id.startswith("test-cp-")
        assert cp_id.endswith("-015")
        assert "-cp-" in cp_id

    @pytest.mark.asyncio
    async def test_mongodb_upsert_called(
        self, id_generator: IDGenerator, mock_db: MagicMock
    ) -> None:
        """Test that MongoDB upsert is called correctly."""
        mock_update = AsyncMock(return_value={"_id": "factory", "seq": 1})
        mock_db["id_counters"].find_one_and_update = mock_update

        await id_generator.generate_factory_id()

        # Verify upsert was called with correct parameters
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == {"_id": "factory"}
        assert call_args[0][1] == {"$inc": {"seq": 1}}
        assert call_args[1]["upsert"] is True
