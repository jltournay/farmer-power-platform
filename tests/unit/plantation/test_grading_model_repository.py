"""Unit tests for GradingModelRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.domain.models.grading_model import (
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock MongoDB database."""
    return MagicMock()


@pytest.fixture
def grading_model_repo(mock_db: MagicMock) -> GradingModelRepository:
    """Create a GradingModelRepository with mocked database."""
    return GradingModelRepository(mock_db)


@pytest.fixture
def sample_grading_model() -> GradingModel:
    """Create a sample grading model for testing."""
    return GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="1.0.0",
        regulatory_authority="Tea Board of Kenya (TBK)",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={
            "leaf_type": GradingAttribute(
                num_classes=3,
                classes=["good", "medium", "bad"],
            ),
        },
        grade_rules=GradeRules(
            reject_conditions={"leaf_type": ["bad"]},
        ),
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        active_at_factory=["factory-001"],
    )


class TestGradingModelRepository:
    """Tests for GradingModelRepository."""

    @pytest.mark.asyncio
    async def test_create_grading_model(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test creating a grading model."""
        grading_model_repo._collection.insert_one = AsyncMock()

        result = await grading_model_repo.create(sample_grading_model)

        grading_model_repo._collection.insert_one.assert_called_once()
        assert result == sample_grading_model

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test retrieving a grading model by ID."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        grading_model_repo._collection.find_one = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.get_by_id(sample_grading_model.model_id)

        assert result is not None
        assert result.model_id == sample_grading_model.model_id
        assert result.model_version == sample_grading_model.model_version

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, grading_model_repo: GradingModelRepository) -> None:
        """Test retrieving a non-existent grading model."""
        grading_model_repo._collection.find_one = AsyncMock(return_value=None)

        result = await grading_model_repo.get_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_and_version_found(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test retrieving a grading model by ID and version (Story 1.7)."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        grading_model_repo._collection.find_one = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.get_by_id_and_version(
            sample_grading_model.model_id, sample_grading_model.model_version
        )

        assert result is not None
        assert result.model_id == sample_grading_model.model_id
        assert result.model_version == sample_grading_model.model_version
        # Verify query includes both model_id and model_version
        grading_model_repo._collection.find_one.assert_called_once_with(
            {"model_id": sample_grading_model.model_id, "model_version": sample_grading_model.model_version}
        )

    @pytest.mark.asyncio
    async def test_get_by_id_and_version_not_found(self, grading_model_repo: GradingModelRepository) -> None:
        """Test retrieving non-existent model version (Story 1.7)."""
        grading_model_repo._collection.find_one = AsyncMock(return_value=None)

        result = await grading_model_repo.get_by_id_and_version("tbk_kenya_tea_v1", "2.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_and_version_wrong_version(self, grading_model_repo: GradingModelRepository) -> None:
        """Test retrieving model with mismatched version (Story 1.7)."""
        grading_model_repo._collection.find_one = AsyncMock(return_value=None)

        result = await grading_model_repo.get_by_id_and_version("tbk_kenya_tea_v1", "99.99.99")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_factory_found(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test retrieving a grading model by factory ID."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        grading_model_repo._collection.find_one = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.get_by_factory("factory-001")

        grading_model_repo._collection.find_one.assert_called_once()
        assert result is not None
        assert result.model_id == sample_grading_model.model_id

    @pytest.mark.asyncio
    async def test_get_by_factory_not_found(self, grading_model_repo: GradingModelRepository) -> None:
        """Test retrieving grading model for factory with no assignment."""
        grading_model_repo._collection.find_one = AsyncMock(return_value=None)

        result = await grading_model_repo.get_by_factory("nonexistent-factory")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_factory_assignment(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test adding a factory to grading model's active_at_factory list."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        mock_doc["active_at_factory"] = ["factory-001", "factory-002"]
        grading_model_repo._collection.find_one_and_update = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.add_factory_assignment(sample_grading_model.model_id, "factory-002")

        assert result is not None
        assert "factory-002" in result.active_at_factory

    @pytest.mark.asyncio
    async def test_remove_factory_assignment(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test removing a factory from grading model's active_at_factory list."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        mock_doc["active_at_factory"] = []
        grading_model_repo._collection.find_one_and_update = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.remove_factory_assignment(sample_grading_model.model_id, "factory-001")

        assert result is not None
        assert "factory-001" not in result.active_at_factory

    @pytest.mark.asyncio
    async def test_update_grading_model(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test updating a grading model."""
        updated_doc = sample_grading_model.model_dump()
        updated_doc["_id"] = sample_grading_model.model_id
        updated_doc["model_version"] = "1.1.0"
        grading_model_repo._collection.find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await grading_model_repo.update(
            sample_grading_model.model_id,
            {"model_version": "1.1.0"},
        )

        assert result is not None
        assert result.model_version == "1.1.0"
        grading_model_repo._collection.find_one_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_grading_model_not_found(self, grading_model_repo: GradingModelRepository) -> None:
        """Test updating a non-existent grading model."""
        grading_model_repo._collection.find_one_and_update = AsyncMock(return_value=None)

        result = await grading_model_repo.update("nonexistent", {"model_version": "2.0.0"})

        assert result is None

    @pytest.mark.asyncio
    async def test_update_empty_updates(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test updating with empty updates returns current model."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id
        grading_model_repo._collection.find_one = AsyncMock(return_value=mock_doc)

        result = await grading_model_repo.update(sample_grading_model.model_id, {})

        assert result is not None
        assert result.model_id == sample_grading_model.model_id

    @pytest.mark.asyncio
    async def test_list_all_grading_models(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test listing all grading models."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
        grading_model_repo._collection.find = MagicMock(return_value=mock_cursor)
        grading_model_repo._collection.count_documents = AsyncMock(return_value=1)

        result, next_token, total = await grading_model_repo.list_all()

        assert len(result) == 1
        assert result[0].model_id == sample_grading_model.model_id
        assert total == 1
        assert next_token is None

    @pytest.mark.asyncio
    async def test_list_all_with_filters(
        self, grading_model_repo: GradingModelRepository, sample_grading_model: GradingModel
    ) -> None:
        """Test listing grading models with filters."""
        mock_doc = sample_grading_model.model_dump()
        mock_doc["_id"] = sample_grading_model.model_id

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
        grading_model_repo._collection.find = MagicMock(return_value=mock_cursor)
        grading_model_repo._collection.count_documents = AsyncMock(return_value=1)

        result, next_token, total = await grading_model_repo.list_all(filters={"market_name": "Kenya_TBK"})

        assert len(result) == 1
        # Verify filter was applied
        grading_model_repo._collection.count_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_indexes(self, grading_model_repo: GradingModelRepository) -> None:
        """Test index creation."""
        grading_model_repo._collection.create_index = AsyncMock()

        await grading_model_repo.ensure_indexes()

        # Should create at least the model_id index and active_at_factory index
        assert grading_model_repo._collection.create_index.call_count >= 2
