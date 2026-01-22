"""E2E Tests: Platform Admin Grading Model Management UI Flows.

Story 9.6a: Tests for grading model management via BFF admin endpoints.
These tests verify the API operations that the platform-admin frontend relies on
for viewing and assigning grading models.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Test Data (from seed/grading_models.json):
    - tbk_kenya_tea_v1: Binary grading model for Kenya TBK market (assigned to FAC-E2E-001)
    - ktda_ternary_v1: Ternary grading model for Kenya KTDA market (assigned to FAC-E2E-002)
"""

from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient


@pytest.mark.e2e
class TestGradingModelList:
    """E2E tests for Grading Model List page (AC 9.6a.3.1)."""

    @pytest.mark.asyncio
    async def test_list_grading_models_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing grading models returns expected structure."""
        result = await bff_api.admin_list_grading_models()

        # Verify response structure (GradingModelListResponse)
        assert "data" in result
        assert "pagination" in result

        # Check pagination structure
        pagination = result["pagination"]
        assert "total_count" in pagination
        assert "has_next" in pagination

    @pytest.mark.asyncio
    async def test_list_grading_models_with_seed_data(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing grading models returns seed data models."""
        result = await bff_api.admin_list_grading_models()

        # Should have at least the seeded grading models
        models = result["data"]
        assert len(models) >= 2, "Expected at least 2 grading models in seed data"

        # Verify grading model summary structure
        for model in models:
            assert "model_id" in model
            assert "model_version" in model
            assert "crops_name" in model
            assert "market_name" in model
            assert "grading_type" in model
            assert "attribute_count" in model
            assert "factory_count" in model

    @pytest.mark.asyncio
    async def test_list_grading_models_includes_known_models(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that known seed data models are in the list."""
        result = await bff_api.admin_list_grading_models()

        model_ids = {m["model_id"] for m in result["data"]}
        assert "tbk_kenya_tea_v1" in model_ids, "Expected TBK binary model in list"
        assert "ktda_ternary_v1" in model_ids, "Expected KTDA ternary model in list"

    @pytest.mark.asyncio
    async def test_list_grading_models_filter_by_market(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering grading models by market name (AC 9.6a.3.1)."""
        result = await bff_api.admin_list_grading_models(market_name="Kenya_TBK")

        # All returned models should be for Kenya_TBK market
        for model in result["data"]:
            assert model["market_name"] == "Kenya_TBK"

    @pytest.mark.asyncio
    async def test_list_grading_models_filter_by_crops_name(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering grading models by crop name (AC 9.6a.3.1)."""
        result = await bff_api.admin_list_grading_models(crops_name="Tea")

        # All returned models should be for Tea
        for model in result["data"]:
            assert model["crops_name"] == "Tea"

    @pytest.mark.asyncio
    async def test_list_grading_models_filter_by_grading_type(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering grading models by grading type (AC 9.6a.3.1)."""
        # Filter for binary grading models
        result = await bff_api.admin_list_grading_models(grading_type="binary")

        # All returned models should be binary
        for model in result["data"]:
            assert model["grading_type"] == "binary"

    @pytest.mark.asyncio
    async def test_list_grading_models_pagination(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test pagination parameters work correctly (AC 9.6a.3.1)."""
        # Get first page with small page size
        result = await bff_api.admin_list_grading_models(page_size=1)

        pagination = result["pagination"]
        assert len(result["data"]) <= 1
        assert pagination["total_count"] >= 2  # We have at least 2 in seed

        # If more pages exist, we should be able to get next page
        if pagination["has_next"]:
            next_page = await bff_api.admin_list_grading_models(
                page_size=1,
                page_token=pagination.get("next_page_token"),
            )
            assert len(next_page["data"]) <= 1

    @pytest.mark.asyncio
    async def test_list_grading_models_combined_filters(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test combining multiple filters (AC 9.6a.3.1)."""
        result = await bff_api.admin_list_grading_models(
            market_name="Kenya_TBK",
            crops_name="Tea",
            grading_type="binary",
        )

        # All returned models should match all filters
        for model in result["data"]:
            assert model["market_name"] == "Kenya_TBK"
            assert model["crops_name"] == "Tea"
            assert model["grading_type"] == "binary"


@pytest.mark.e2e
class TestGradingModelDetail:
    """E2E tests for Grading Model Detail page (AC 9.6a.3.2)."""

    @pytest.mark.asyncio
    async def test_grading_model_detail_loads(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail page loads with full data (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify basic fields
        assert result["model_id"] == model_id
        assert "model_version" in result
        assert "regulatory_authority" in result
        assert "crops_name" in result
        assert "market_name" in result
        assert "grading_type" in result

    @pytest.mark.asyncio
    async def test_grading_model_detail_has_attributes(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail includes attributes (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify attributes structure
        assert "attributes" in result
        attributes = result["attributes"]
        assert isinstance(attributes, dict)
        assert len(attributes) > 0

        # Check attribute structure
        for _attr_name, attr_data in attributes.items():
            assert "num_classes" in attr_data
            assert "classes" in attr_data
            assert isinstance(attr_data["classes"], list)

    @pytest.mark.asyncio
    async def test_grading_model_detail_has_grade_rules(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail includes grade rules (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify grade rules structure
        assert "grade_rules" in result
        rules = result["grade_rules"]
        assert "reject_conditions" in rules
        assert "conditional_reject" in rules

    @pytest.mark.asyncio
    async def test_grading_model_detail_has_grade_labels(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail includes grade labels (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify grade labels
        assert "grade_labels" in result
        labels = result["grade_labels"]
        assert isinstance(labels, dict)
        assert len(labels) > 0  # Should have at least ACCEPT/REJECT labels

    @pytest.mark.asyncio
    async def test_grading_model_detail_has_factory_assignments(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail includes factory assignments (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify factory assignments structure
        assert "active_at_factories" in result
        factories = result["active_at_factories"]
        assert isinstance(factories, list)

        # Should be assigned to FAC-E2E-001 per seed data
        factory_ids = [f["factory_id"] for f in factories]
        assert "FAC-E2E-001" in factory_ids

        # Factory references should have id and optional name
        for factory in factories:
            assert "factory_id" in factory
            # name may be None if factory lookup failed

    @pytest.mark.asyncio
    async def test_grading_model_detail_has_timestamps(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test grading model detail includes timestamps (AC 9.6a.3.2)."""
        model_id = "tbk_kenya_tea_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify timestamps
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_grading_model_detail_ternary_model(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test detail for a ternary grading model."""
        model_id = "ktda_ternary_v1"
        result = await bff_api.admin_get_grading_model(model_id)

        # Verify it's a ternary model
        assert result["model_id"] == model_id
        assert result["grading_type"] == "ternary"
        assert result["market_name"] == "Kenya_KTDA"

        # Ternary models should have 3 grade labels
        labels = result["grade_labels"]
        assert len(labels) >= 3

    @pytest.mark.asyncio
    async def test_grading_model_detail_404_not_found(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when grading model not found (AC 9.6a.3.2)."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/grading-models/nonexistent_model_v1",
        )

        # Should return 404 for non-existent model
        assert response.status_code == 404


@pytest.mark.e2e
class TestGradingModelAssignment:
    """E2E tests for Grading Model Factory Assignment (AC 9.6a.3.3)."""

    @pytest.mark.asyncio
    async def test_assign_grading_model_to_factory(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test assigning a grading model to a factory (AC 9.6a.3.3).

        Note: This test uses ktda_ternary_v1 which is initially assigned to FAC-E2E-002.
        We assign it to FAC-E2E-001 and verify the assignment.
        """
        model_id = "ktda_ternary_v1"
        factory_id = "FAC-E2E-001"

        # Assign model to factory
        result = await bff_api.admin_assign_grading_model(
            model_id=model_id,
            factory_id=factory_id,
        )

        # Verify the model was returned with updated factory assignments
        assert result["model_id"] == model_id

        # Check that FAC-E2E-001 is now in the active_at_factories list
        factory_ids = [f["factory_id"] for f in result["active_at_factories"]]
        assert factory_id in factory_ids

    @pytest.mark.asyncio
    async def test_assign_grading_model_returns_full_detail(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that assignment returns full grading model detail."""
        model_id = "tbk_kenya_tea_v1"
        factory_id = "FAC-E2E-002"

        result = await bff_api.admin_assign_grading_model(
            model_id=model_id,
            factory_id=factory_id,
        )

        # Should return full detail, not just summary
        assert "model_id" in result
        assert "model_version" in result
        assert "attributes" in result
        assert "grade_rules" in result
        assert "grade_labels" in result
        assert "active_at_factories" in result

    @pytest.mark.asyncio
    async def test_assign_grading_model_not_found(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when assigning non-existent grading model."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/grading-models/nonexistent_model/assign",
            json={"factory_id": "FAC-E2E-001"},
        )

        # Should return 404 for non-existent model
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_grading_model_factory_not_found(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when assigning to non-existent factory."""
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/grading-models/tbk_kenya_tea_v1/assign",
            json={"factory_id": "NONEXISTENT-FACTORY"},
        )

        # Should return 404 for non-existent factory
        assert response.status_code == 404


@pytest.mark.e2e
class TestGradingModelErrorHandling:
    """E2E tests for Error Handling."""

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_grading_model_endpoints(
        self,
        bff_api: BFFClient,
    ):
        """Test that non-admin roles get 403 on grading model endpoints."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/grading-models",
            role="factory_manager",
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "insufficient_permissions"

    @pytest.mark.asyncio
    async def test_invalid_grading_type_filter(
        self,
        bff_api: BFFClient,
    ):
        """Test that invalid grading type filter doesn't crash (returns empty or all)."""
        # Invalid grading type should not crash - either returns empty or ignores filter
        result = await bff_api.admin_list_grading_models(grading_type="invalid_type")

        # Should return a valid response structure
        assert "data" in result
        assert "pagination" in result


@pytest.mark.e2e
class TestGradingModelUIIntegration:
    """E2E tests for UI integration scenarios."""

    @pytest.mark.asyncio
    async def test_list_to_detail_flow(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test navigation from list to detail (simulates row click)."""
        # List grading models
        list_result = await bff_api.admin_list_grading_models()
        assert len(list_result["data"]) > 0

        # Get first model's ID
        model_id = list_result["data"][0]["model_id"]

        # Navigate to detail
        detail = await bff_api.admin_get_grading_model(model_id)

        # Detail should have more info than summary
        assert detail["model_id"] == model_id
        assert "attributes" in detail
        assert "grade_rules" in detail
        assert "grade_labels" in detail
        assert "active_at_factories" in detail

    @pytest.mark.asyncio
    async def test_assign_and_verify_flow(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test assign flow (get detail, assign, verify)."""
        model_id = "tbk_kenya_tea_v1"
        factory_id = "FAC-E2E-002"

        # Get current state
        original = await bff_api.admin_get_grading_model(model_id)
        original_factory_ids = [f["factory_id"] for f in original["active_at_factories"]]

        # Assign to factory
        result = await bff_api.admin_assign_grading_model(
            model_id=model_id,
            factory_id=factory_id,
        )

        # Verify assignment was added
        new_factory_ids = [f["factory_id"] for f in result["active_at_factories"]]
        assert factory_id in new_factory_ids

        # Original factories should still be there (additive)
        for fid in original_factory_ids:
            assert fid in new_factory_ids

    @pytest.mark.asyncio
    async def test_filter_then_detail_flow(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering then viewing detail."""
        # Filter to binary models
        list_result = await bff_api.admin_list_grading_models(grading_type="binary")
        assert len(list_result["data"]) > 0

        # Get detail of first binary model
        model_id = list_result["data"][0]["model_id"]
        detail = await bff_api.admin_get_grading_model(model_id)

        # Should be a binary model
        assert detail["grading_type"] == "binary"
