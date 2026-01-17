"""E2E Tests: Platform Admin Collection Point Management UI Flows.

Story 9.4: Tests for collection point management UI flows via BFF admin endpoints.
These tests verify the API operations that the platform-admin frontend relies on.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Test Data Relationships (from seed):
    - REG-E2E-001 (Kericho Highland): FAC-E2E-001
    - REG-E2E-002 (Nandi Hills): FAC-E2E-002
    - FAC-E2E-001: kericho-highland-cp-001, kericho-highland-cp-002
    - FAC-E2E-002: nandi-highland-cp-001
"""

from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient


@pytest.mark.e2e
class TestCollectionPointList:
    """E2E tests for Collection Point list within Factory Detail (AC5)."""

    @pytest.mark.asyncio
    async def test_list_collection_points_for_factory(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing collection points for a factory displays embedded list."""
        # First get a factory with collection points
        factories_result = await bff_api.admin_list_factories()
        if not factories_result["data"]:
            pytest.skip("No factories in seed data")

        # Find a factory with collection points
        factory_with_cps = None
        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                factory_with_cps = factory
                break

        if not factory_with_cps:
            pytest.skip("No factories with collection points in seed data")

        factory_id = factory_with_cps["id"]

        # List collection points for this factory
        result = await bff_api.admin_list_collection_points(factory_id=factory_id)

        # Verify response structure (matches CollectionPointListResponse)
        assert "data" in result
        assert "pagination" in result

        # Should have at least one collection point
        collection_points = result["data"]
        assert len(collection_points) >= 1, "Expected at least 1 collection point"

        # Verify summary structure matches what frontend expects
        for cp in collection_points:
            assert "id" in cp
            assert "name" in cp
            assert "factory_id" in cp
            assert cp["factory_id"] == factory_id
            assert "region_id" in cp
            assert "farmer_count" in cp
            assert "status" in cp

    @pytest.mark.asyncio
    async def test_collection_points_have_valid_status(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test collection point status values are valid (active/inactive/seasonal)."""
        factories_result = await bff_api.admin_list_factories()
        if not factories_result["data"]:
            pytest.skip("No factories in seed data")

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                for cp in result["data"]:
                    assert cp["status"] in ["active", "inactive", "seasonal"], f"Invalid status: {cp['status']}"
                break


@pytest.mark.e2e
class TestCollectionPointDetail:
    """E2E tests for Collection Point Detail page (AC1)."""

    @pytest.mark.asyncio
    async def test_collection_point_detail_loads(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test clicking CP row navigates to detail and loads full data."""
        # First get a factory with collection points
        factories_result = await bff_api.admin_list_factories()
        cp_id = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Get collection point detail (simulates navigation to /factories/{factoryId}/collection-points/{cpId})
        result = await bff_api.admin_get_collection_point(cp_id)

        # Verify detail structure matches CollectionPointDetailFull
        assert result["id"] == cp_id
        assert "name" in result
        assert "factory_id" in result
        assert "region_id" in result
        assert "location" in result
        assert "operating_hours" in result
        assert "collection_days" in result
        assert "capacity" in result
        assert "farmer_count" in result
        assert "status" in result
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_collection_point_detail_operating_hours_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test operating hours display correctly (AC1 - operating hours panel)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        result = await bff_api.admin_get_collection_point(cp_id)

        # Verify operating_hours structure
        operating_hours = result["operating_hours"]
        assert "weekdays" in operating_hours
        assert "weekends" in operating_hours

        # Format should be HH:MM-HH:MM
        import re

        time_pattern = r"^\d{2}:\d{2}-\d{2}:\d{2}$"
        assert re.match(time_pattern, operating_hours["weekdays"]), (
            f"Invalid weekday hours format: {operating_hours['weekdays']}"
        )
        assert re.match(time_pattern, operating_hours["weekends"]), (
            f"Invalid weekend hours format: {operating_hours['weekends']}"
        )

    @pytest.mark.asyncio
    async def test_collection_point_detail_capacity_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test capacity & equipment displays correctly (AC1 - capacity panel)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        result = await bff_api.admin_get_collection_point(cp_id)

        # Verify capacity structure
        capacity = result["capacity"]
        assert "max_daily_kg" in capacity
        assert "storage_type" in capacity
        assert "has_weighing_scale" in capacity
        assert "has_qc_device" in capacity

        # Validate storage type
        assert capacity["storage_type"] in ["open_air", "covered_shed", "refrigerated"]

        # Validate boolean flags
        assert isinstance(capacity["has_weighing_scale"], bool)
        assert isinstance(capacity["has_qc_device"], bool)

    @pytest.mark.asyncio
    async def test_collection_point_detail_collection_days(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test collection days displays correctly (AC1 - collection days)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        result = await bff_api.admin_get_collection_point(cp_id)

        # Verify collection_days is a list of valid days
        collection_days = result["collection_days"]
        assert isinstance(collection_days, list)

        valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        for day in collection_days:
            assert day in valid_days, f"Invalid collection day: {day}"

    @pytest.mark.asyncio
    async def test_collection_point_404_not_found(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 error when collection point not found (AC7)."""
        # Use a valid format ID that doesn't exist in seed data
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/collection-points/nonexistent-region-cp-999",
        )

        # Should return 404 for non-existent collection point
        assert response.status_code == 404


@pytest.mark.e2e
class TestCollectionPointEdit:
    """E2E tests for Collection Point Edit page (AC3)."""

    @pytest.mark.asyncio
    async def test_update_collection_point_name(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing collection point name (AC3 - pre-populate form, save changes)."""
        # Get a collection point
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_name = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp = cp_result["data"][0]
                    cp_id = cp["id"]
                    # Get full detail for original name
                    detail = await bff_api.admin_get_collection_point(cp_id)
                    original_name = detail["name"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Update the name
        new_name = f"{original_name} (E2E Updated)"
        result = await bff_api.admin_update_collection_point(cp_id, {"name": new_name})

        # Verify update was applied
        assert result["name"] == new_name
        assert result["id"] == cp_id

        # Restore original name
        await bff_api.admin_update_collection_point(cp_id, {"name": original_name})

    @pytest.mark.asyncio
    async def test_update_collection_point_operating_hours(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing operating hours (AC3)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_hours = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    detail = await bff_api.admin_get_collection_point(cp_id)
                    original_hours = detail["operating_hours"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Update operating hours
        new_hours = {
            "weekdays": "05:30-09:30",
            "weekends": "06:00-08:00",
        }
        result = await bff_api.admin_update_collection_point(cp_id, {"operating_hours": new_hours})

        # Verify update
        assert result["operating_hours"]["weekdays"] == "05:30-09:30"
        assert result["operating_hours"]["weekends"] == "06:00-08:00"

        # Restore original
        await bff_api.admin_update_collection_point(cp_id, {"operating_hours": original_hours})

    @pytest.mark.asyncio
    async def test_update_collection_point_capacity(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test editing capacity settings (AC3)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_capacity = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    detail = await bff_api.admin_get_collection_point(cp_id)
                    original_capacity = detail["capacity"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Update capacity
        new_capacity = {
            "max_daily_kg": 1000,
            "storage_type": "refrigerated",
            "has_weighing_scale": True,
            "has_qc_device": True,
        }
        result = await bff_api.admin_update_collection_point(cp_id, {"capacity": new_capacity})

        # Verify update
        assert result["capacity"]["max_daily_kg"] == 1000
        assert result["capacity"]["storage_type"] == "refrigerated"

        # Restore original
        await bff_api.admin_update_collection_point(cp_id, {"capacity": original_capacity})


@pytest.mark.e2e
class TestCollectionPointStatusManagement:
    """E2E tests for Collection Point Status Management (AC4)."""

    @pytest.mark.asyncio
    async def test_change_status_to_inactive(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test changing status to inactive with confirmation (AC4)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_status = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                # Find an active collection point
                for cp in cp_result["data"]:
                    if cp["status"] == "active":
                        cp_id = cp["id"]
                        original_status = "active"
                        break
                if cp_id:
                    break

        if not cp_id:
            pytest.skip("No active collection points in seed data")

        # Change status to inactive
        result = await bff_api.admin_update_collection_point(cp_id, {"status": "inactive"})

        # Verify status changed
        assert result["status"] == "inactive"

        # Restore original status
        await bff_api.admin_update_collection_point(cp_id, {"status": original_status})

    @pytest.mark.asyncio
    async def test_change_status_to_seasonal(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test changing status to seasonal (AC4)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_status = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp = cp_result["data"][0]
                    cp_id = cp["id"]
                    original_status = cp["status"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Change status to seasonal
        result = await bff_api.admin_update_collection_point(cp_id, {"status": "seasonal"})

        # Verify status changed
        assert result["status"] == "seasonal"

        # Restore original status
        await bff_api.admin_update_collection_point(cp_id, {"status": original_status})


@pytest.mark.e2e
class TestCollectionPointUIUpdates:
    """E2E tests for Optimistic UI Updates (AC6)."""

    @pytest.mark.asyncio
    async def test_successful_update_returns_updated_data(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that successful update returns the updated entity for UI update (AC6)."""
        factories_result = await bff_api.admin_list_factories()
        cp_id = None
        original_name = None

        for factory in factories_result["data"]:
            if factory.get("collection_point_count", 0) > 0:
                cp_result = await bff_api.admin_list_collection_points(factory_id=factory["id"])
                if cp_result["data"]:
                    cp_id = cp_result["data"][0]["id"]
                    detail = await bff_api.admin_get_collection_point(cp_id)
                    original_name = detail["name"]
                    break

        if not cp_id:
            pytest.skip("No collection points in seed data")

        # Update and verify the response contains full entity (not just ID)
        new_name = f"{original_name} (Optimistic)"
        result = await bff_api.admin_update_collection_point(cp_id, {"name": new_name})

        # Response should contain full entity for optimistic UI update
        assert "id" in result
        assert "name" in result
        assert "status" in result
        assert "operating_hours" in result
        assert "capacity" in result
        assert "farmer_count" in result

        # Verify the update was applied
        assert result["name"] == new_name

        # Restore
        await bff_api.admin_update_collection_point(cp_id, {"name": original_name})


@pytest.mark.e2e
class TestCollectionPointErrorHandling:
    """E2E tests for Error Handling (AC7)."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_collection_point_returns_404(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 when collection point doesn't exist (AC7)."""
        # Use valid format ID that doesn't exist in seed data
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/collection-points/nonexistent-region-cp-999",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_collection_point_returns_404(
        self,
        bff_api: BFFClient,
    ):
        """Test 404 when updating non-existent collection point (AC7)."""
        # Use valid format ID that doesn't exist in seed data
        response = await bff_api.admin_request_raw(
            "PUT",
            "/api/admin/collection-points/nonexistent-region-cp-999",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_collection_points_missing_factory_id_returns_422(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 when listing without factory_id parameter (AC7)."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/collection-points",
            # Missing required factory_id
        )
        # Should return 422 for validation error
        assert response.status_code == 422
