"""Integration tests for GradingModel repository with real MongoDB.

These tests validate that GradingModel CRUD operations work correctly
with a real MongoDB instance.

Prerequisites:
    docker-compose -f tests/docker-compose.test.yaml up -d

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_grading_model_mongodb.py -v
"""

import pytest
from plantation_model.domain.models import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)


def create_test_grading_model(
    model_id: str = "tbk_kenya_tea_v1",
    factory_ids: list[str] | None = None,
) -> GradingModel:
    """Create a test grading model with realistic TBK Kenya Tea structure."""
    return GradingModel(
        model_id=model_id,
        model_version="1.0.0",
        regulatory_authority="Tea Board of Kenya (TBK)",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={
            "leaf_type": GradingAttribute(
                num_classes=7,
                classes=[
                    "bud",
                    "one_leaf_bud",
                    "two_leaves_bud",
                    "three_plus_leaves_bud",
                    "single_soft_leaf",
                    "coarse_leaf",
                    "banji",
                ],
            ),
            "banji_hardness": GradingAttribute(
                num_classes=2,
                classes=["soft", "hard"],
            ),
        },
        grade_rules=GradeRules(
            reject_conditions={
                "leaf_type": ["three_plus_leaves_bud", "coarse_leaf"],
            },
            conditional_reject=[
                ConditionalReject(
                    if_attribute="leaf_type",
                    if_value="banji",
                    then_attribute="banji_hardness",
                    reject_values=["hard"],
                ),
            ],
        ),
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        active_at_factory=factory_ids or [],
    )


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestGradingModelRepository:
    """Integration tests for GradingModelRepository."""

    async def test_create_grading_model(self, test_db) -> None:
        """Test grading model creation persists to MongoDB correctly."""
        repo = GradingModelRepository(test_db)

        # Create model
        model = create_test_grading_model()
        created = await repo.create(model)

        # Verify returned model matches
        assert created.model_id == "tbk_kenya_tea_v1"
        assert created.model_version == "1.0.0"
        assert created.grading_type == GradingType.BINARY
        assert len(created.attributes) == 2
        assert "leaf_type" in created.attributes
        assert "banji_hardness" in created.attributes

    async def test_get_by_id_returns_correct_model(self, test_db) -> None:
        """Test grading model retrieval returns correct data types."""
        repo = GradingModelRepository(test_db)

        # Create and retrieve
        original = create_test_grading_model()
        await repo.create(original)

        retrieved = await repo.get_by_id("tbk_kenya_tea_v1")

        # Verify all fields
        assert retrieved is not None
        assert retrieved.model_id == original.model_id
        assert retrieved.model_version == original.model_version
        assert retrieved.regulatory_authority == original.regulatory_authority
        assert retrieved.crops_name == original.crops_name
        assert retrieved.market_name == original.market_name
        assert retrieved.grading_type == GradingType.BINARY

        # Verify attributes structure
        assert retrieved.attributes["leaf_type"].num_classes == 7
        assert retrieved.attributes["leaf_type"].classes[0] == "bud"
        assert retrieved.attributes["banji_hardness"].num_classes == 2

        # Verify grade rules
        assert "leaf_type" in retrieved.grade_rules.reject_conditions
        assert len(retrieved.grade_rules.conditional_reject) == 1
        assert retrieved.grade_rules.conditional_reject[0].if_attribute == "leaf_type"

        # Verify grade labels
        assert retrieved.grade_labels["ACCEPT"] == "Primary"
        assert retrieved.grade_labels["REJECT"] == "Secondary"

    async def test_get_by_id_returns_none_for_missing(self, test_db) -> None:
        """Test retrieval returns None for non-existent model."""
        repo = GradingModelRepository(test_db)

        result = await repo.get_by_id("non_existent_model")

        assert result is None

    async def test_get_by_factory_with_assignment(self, test_db) -> None:
        """Test factory grading model lookup works with indexes."""
        repo = GradingModelRepository(test_db)

        # Create model assigned to factory
        model = create_test_grading_model(factory_ids=["factory-001"])
        await repo.create(model)

        # Lookup by factory
        result = await repo.get_by_factory("factory-001")

        assert result is not None
        assert result.model_id == "tbk_kenya_tea_v1"
        assert "factory-001" in result.active_at_factory

    async def test_get_by_factory_returns_none_for_unassigned(self, test_db) -> None:
        """Test factory lookup returns None when no model assigned."""
        repo = GradingModelRepository(test_db)

        # Create model without factory assignment
        model = create_test_grading_model(factory_ids=[])
        await repo.create(model)

        # Lookup should return None
        result = await repo.get_by_factory("factory-999")

        assert result is None

    async def test_add_factory_assignment(self, test_db) -> None:
        """Test adding factory to grading model."""
        repo = GradingModelRepository(test_db)

        # Create model without factory
        model = create_test_grading_model(factory_ids=[])
        await repo.create(model)

        # Add factory assignment
        updated = await repo.add_factory_assignment("tbk_kenya_tea_v1", "new-factory")

        assert updated is not None
        assert "new-factory" in updated.active_at_factory

        # Verify in DB
        retrieved = await repo.get_by_id("tbk_kenya_tea_v1")
        assert "new-factory" in retrieved.active_at_factory

    async def test_remove_factory_assignment(self, test_db) -> None:
        """Test removing factory from grading model."""
        repo = GradingModelRepository(test_db)

        # Create model with factory
        model = create_test_grading_model(factory_ids=["factory-001", "factory-002"])
        await repo.create(model)

        # Remove one factory
        updated = await repo.remove_factory_assignment("tbk_kenya_tea_v1", "factory-001")

        assert updated is not None
        assert "factory-001" not in updated.active_at_factory
        assert "factory-002" in updated.active_at_factory

    async def test_update_grading_model(self, test_db) -> None:
        """Test updating grading model fields."""
        repo = GradingModelRepository(test_db)

        # Create model
        model = create_test_grading_model()
        await repo.create(model)

        # Update version
        updated = await repo.update("tbk_kenya_tea_v1", {"model_version": "1.1.0"})

        assert updated is not None
        assert updated.model_version == "1.1.0"
        assert updated.model_id == "tbk_kenya_tea_v1"  # Other fields unchanged

    async def test_list_all_grading_models(self, test_db) -> None:
        """Test listing all grading models."""
        repo = GradingModelRepository(test_db)

        # Create multiple models
        for i in range(3):
            model = create_test_grading_model(model_id=f"model_{i}")
            await repo.create(model)

        # List all
        models, next_token, total = await repo.list_all()

        assert total == 3
        assert len(models) == 3
        assert next_token is None  # No more pages

    async def test_list_with_pagination(self, test_db) -> None:
        """Test pagination works correctly."""
        repo = GradingModelRepository(test_db)

        # Create 5 models
        for i in range(5):
            model = create_test_grading_model(model_id=f"model_{i:02d}")
            await repo.create(model)

        # Get first page
        page1, next_token, total = await repo.list_all(page_size=2)

        assert total == 5
        assert len(page1) == 2
        assert next_token is not None

        # Get second page
        page2, next_token2, _ = await repo.list_all(page_size=2, page_token=next_token)

        assert len(page2) == 2
        assert next_token2 is not None

        # Verify no overlap
        page1_ids = {m.model_id for m in page1}
        page2_ids = {m.model_id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_ensure_indexes(self, test_db) -> None:
        """Test index creation happens correctly."""
        repo = GradingModelRepository(test_db)

        # Create indexes
        await repo.ensure_indexes()

        # Verify indexes exist
        indexes = await test_db["grading_models"].index_information()

        assert "idx_grading_model_id" in indexes
        assert "idx_grading_model_factory" in indexes
        assert "idx_grading_model_market" in indexes
        assert "idx_grading_model_type" in indexes

    async def test_unique_model_id_constraint(self, test_db) -> None:
        """Test duplicate model_id is rejected."""
        repo = GradingModelRepository(test_db)
        await repo.ensure_indexes()

        # Create first model
        model1 = create_test_grading_model(model_id="duplicate_test")
        await repo.create(model1)

        # Try to create duplicate - should raise
        model2 = create_test_grading_model(model_id="duplicate_test")
        with pytest.raises(Exception):  # DuplicateKeyError
            await repo.create(model2)
