"""E2E Tests: Platform Admin Factory Management UI Flows.

Story 9.3: Tests for factory management UI flows via BFF admin endpoints.
These tests verify the API operations that the platform-admin frontend relies on.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Test Data Relationships:
    - REG-E2E-001 (Kericho Highland): FAC-E2E-001
    - REG-E2E-002 (Nandi Hills): FAC-E2E-002
    - FAC-E2E-001: CP-E2E-001, CP-E2E-002
    - FAC-E2E-002: CP-E2E-003
"""

import uuid
from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient


@pytest.mark.e2e
class TestFactoryListView:
    """E2E tests for Factory List page (AC1)."""

    @pytest.mark.asyncio
    async def test_factory_list_loads_with_seed_data(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that factory list loads and displays seed data factories."""
        result = await bff_api.admin_list_factories()

        # Verify response structure (matches FactoryListResponse)
        assert "data" in result
        assert "pagination" in result

        # Should have at least the seeded factories
        factories = result["data"]
        assert len(factories) >= 1, "Expected at least 1 factory from seed data"

        # Verify factory summary structure matches what frontend expects
        for factory in factories:
            assert "id" in factory
            assert "name" in factory
            assert "code" in factory
            assert "region_id" in factory
            assert "collection_point_count" in factory
            assert "farmer_count" in factory
            assert "is_active" in factory

    @pytest.mark.asyncio
    async def test_factory_list_pagination(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test pagination controls work correctly."""
        # Test with small page size
        result = await bff_api.admin_list_factories(page=1, page_size=10)

        pagination = result["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10

    @pytest.mark.asyncio
    async def test_factory_list_region_filter(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering factories by region (AC1 region dropdown)."""
        # First get available regions
        regions_result = await bff_api.admin_list_regions()
        if not regions_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = regions_result["data"][0]["id"]

        # Filter factories by region
        result = await bff_api.admin_list_factories(region_id=region_id)

        # All returned factories should belong to the specified region
        for factory in result["data"]:
            assert factory["region_id"] == region_id

    @pytest.mark.asyncio
    async def test_factory_list_active_filter(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering factories by active status (AC1 Active/All toggle)."""
        # Get only active factories
        result = await bff_api.admin_list_factories(is_active=True)

        # All returned factories should be active
        for factory in result["data"]:
            assert factory["is_active"] is True


@pytest.mark.e2e
class TestFactoryDetailView:
    """E2E tests for Factory Detail page (AC2)."""

    @pytest.mark.asyncio
    async def test_factory_detail_loads(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test clicking factory row navigates to detail and loads data."""
        # First get a factory from the list
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]

        # Get factory detail (simulates navigation to /factories/{factoryId})
        result = await bff_api.admin_get_factory(factory_id)

        # Verify detail structure matches FactoryDetail type
        assert result["id"] == factory_id
        assert "name" in result
        assert "code" in result
        assert "region_id" in result
        assert "location" in result
        assert "contact" in result
        assert "processing_capacity_kg" in result
        assert "quality_thresholds" in result
        assert "payment_policy" in result
        assert "collection_point_count" in result
        assert "farmer_count" in result
        assert "is_active" in result

    @pytest.mark.asyncio
    async def test_factory_detail_quality_thresholds(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test quality thresholds card displays correctly (AC2)."""
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]
        result = await bff_api.admin_get_factory(factory_id)

        # Verify quality thresholds structure
        thresholds = result["quality_thresholds"]
        assert "tier_1" in thresholds
        assert "tier_2" in thresholds
        assert "tier_3" in thresholds

        # Thresholds should be in order: tier_1 > tier_2 > tier_3
        assert thresholds["tier_1"] > thresholds["tier_2"]
        assert thresholds["tier_2"] > thresholds["tier_3"]

    @pytest.mark.asyncio
    async def test_factory_detail_payment_policy(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test payment policy card displays correctly (AC2)."""
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]
        result = await bff_api.admin_get_factory(factory_id)

        # Verify payment policy structure
        policy = result["payment_policy"]
        assert "policy_type" in policy
        assert policy["policy_type"] in [
            "feedback_only",
            "split_payment",
            "weekly_bonus",
            "delayed_payment",
        ]
        assert "tier_1_adjustment" in policy
        assert "tier_2_adjustment" in policy
        assert "tier_3_adjustment" in policy
        assert "below_tier_3_adjustment" in policy

    @pytest.mark.asyncio
    async def test_factory_detail_404_not_found(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when factory not found (AC8)."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/factories/KEN-FAC-999",  # Valid format but doesn't exist
        )

        # Should return 404 for non-existent factory
        assert response.status_code == 404


@pytest.mark.e2e
class TestFactoryCreateFlow:
    """E2E tests for Factory Create page (AC3)."""

    @pytest.mark.asyncio
    async def test_factory_create_success(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test creating a new factory (AC3 form submission)."""
        # Get a region for the new factory
        regions_result = await bff_api.admin_list_regions()
        if not regions_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = regions_result["data"][0]["id"]

        # Generate unique code to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:3].upper()
        factory_data = {
            "name": f"E2E Test Factory {unique_suffix}",
            "code": f"E2E-{unique_suffix}",
            "region_id": region_id,
            "location": {"latitude": -0.5, "longitude": 35.5},
            "contact": {
                "phone": "+254700000000",
                "email": "test@factory.co.ke",
                "address": "Test Address",
            },
            "processing_capacity_kg": 5000,
            "quality_thresholds": {"tier_1": 85, "tier_2": 70, "tier_3": 50},
            "payment_policy": {
                "policy_type": "feedback_only",
                "tier_1_adjustment": 0,
                "tier_2_adjustment": 0,
                "tier_3_adjustment": 0,
                "below_tier_3_adjustment": 0,
            },
        }

        result = await bff_api.admin_create_factory(factory_data)

        # Verify created factory has correct data
        assert result["name"] == factory_data["name"]
        assert result["code"] == factory_data["code"]
        assert result["region_id"] == region_id
        assert result["processing_capacity_kg"] == 5000
        assert result["is_active"] is True  # Default to active
        assert "id" in result  # Should have generated ID

    @pytest.mark.asyncio
    async def test_factory_create_with_defaults(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test creating factory uses default thresholds (AC3)."""
        regions_result = await bff_api.admin_list_regions()
        if not regions_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = regions_result["data"][0]["id"]
        unique_suffix = str(uuid.uuid4())[:3].upper()

        # Minimal data - quality_thresholds and payment_policy should default
        factory_data = {
            "name": f"E2E Minimal Factory {unique_suffix}",
            "code": f"MIN-{unique_suffix}",
            "region_id": region_id,
            "location": {"latitude": -0.4, "longitude": 35.4},
        }

        result = await bff_api.admin_create_factory(factory_data)

        # Verify defaults are applied
        assert result["quality_thresholds"]["tier_1"] == 85
        assert result["quality_thresholds"]["tier_2"] == 70
        assert result["quality_thresholds"]["tier_3"] == 50


@pytest.mark.e2e
class TestFactoryEditFlow:
    """E2E tests for Factory Edit page (AC4, AC5)."""

    @pytest.mark.asyncio
    async def test_factory_edit_update_name(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing factory name (AC4)."""
        # Get an existing factory
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory = list_result["data"][0]
        factory_id = factory["id"]
        original_name = factory["name"]

        # Update the name
        new_name = f"{original_name} (Updated)"
        update_data = {"name": new_name}

        result = await bff_api.admin_update_factory(factory_id, update_data)

        # Verify update was applied
        assert result["name"] == new_name
        assert result["id"] == factory_id

        # Restore original name
        await bff_api.admin_update_factory(factory_id, {"name": original_name})

    @pytest.mark.asyncio
    async def test_factory_edit_update_capacity(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing factory processing capacity (AC4)."""
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]
        original = await bff_api.admin_get_factory(factory_id)
        original_capacity = original["processing_capacity_kg"]

        # Update capacity
        new_capacity = original_capacity + 1000
        result = await bff_api.admin_update_factory(factory_id, {"processing_capacity_kg": new_capacity})

        assert result["processing_capacity_kg"] == new_capacity

        # Restore original
        await bff_api.admin_update_factory(factory_id, {"processing_capacity_kg": original_capacity})

    @pytest.mark.asyncio
    async def test_factory_edit_update_quality_thresholds(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing factory quality thresholds (AC4)."""
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]
        original = await bff_api.admin_get_factory(factory_id)
        original_thresholds = original["quality_thresholds"]

        # Update thresholds
        new_thresholds = {"tier_1": 90, "tier_2": 75, "tier_3": 55}
        result = await bff_api.admin_update_factory(factory_id, {"quality_thresholds": new_thresholds})

        assert result["quality_thresholds"]["tier_1"] == 90
        assert result["quality_thresholds"]["tier_2"] == 75
        assert result["quality_thresholds"]["tier_3"] == 55

        # Restore original
        await bff_api.admin_update_factory(factory_id, {"quality_thresholds": original_thresholds})

    @pytest.mark.asyncio
    async def test_factory_deactivate(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test deactivating a factory (AC5)."""
        # Create a test factory to deactivate (don't modify seed data)
        regions_result = await bff_api.admin_list_regions()
        if not regions_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = regions_result["data"][0]["id"]
        unique_suffix = str(uuid.uuid4())[:3].upper()

        factory_data = {
            "name": f"E2E Deactivate Test {unique_suffix}",
            "code": f"DEA-{unique_suffix}",
            "region_id": region_id,
            "location": {"latitude": -0.6, "longitude": 35.6},
        }

        created = await bff_api.admin_create_factory(factory_data)
        factory_id = created["id"]
        assert created["is_active"] is True

        # Deactivate the factory
        result = await bff_api.admin_update_factory(factory_id, {"is_active": False})

        assert result["is_active"] is False


@pytest.mark.e2e
class TestCollectionPointQuickAdd:
    """E2E tests for Collection Point Quick-Add from Factory Detail (AC6)."""

    @pytest.mark.asyncio
    async def test_create_collection_point_under_factory(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test creating a collection point from factory detail (AC6)."""
        # Get a factory
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory = list_result["data"][0]
        factory_id = factory["id"]
        region_id = factory["region_id"]

        # Create collection point under this factory
        unique_suffix = str(uuid.uuid4())[:3].upper()
        cp_data = {
            "name": f"E2E Test CP {unique_suffix}",
            "location": {"latitude": -0.45, "longitude": 35.45},
            "region_id": region_id,
            "status": "active",
        }

        # Use raw request since admin_create_collection_point may not exist
        response = await bff_api.admin_request_raw(
            "POST",
            f"/api/admin/factories/{factory_id}/collection-points",
            json=cp_data,
        )

        # Should succeed with 200 or 201
        assert response.status_code in [200, 201]

        result = response.json()
        assert result["name"] == cp_data["name"]
        assert result["factory_id"] == factory_id
        assert result["region_id"] == region_id


@pytest.mark.e2e
class TestErrorHandling:
    """E2E tests for error handling (AC8)."""

    @pytest.mark.asyncio
    async def test_invalid_factory_id_format(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 error for invalid factory ID format."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/factories/invalid-format",
        )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_factory_create_missing_required_fields(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 error when creating factory without required fields."""
        # Missing name, code, region_id, location
        response = await bff_api.admin_request_raw(
            "POST",
            "/api/admin/factories",
            json={"processing_capacity_kg": 1000},
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_factory_update_nonexistent(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when updating non-existent factory."""
        response = await bff_api.admin_request_raw(
            "PUT",
            "/api/admin/factories/KEN-FAC-999",
            json={"name": "Updated Name"},
        )

        # Should return 404 for non-existent factory
        assert response.status_code == 404
