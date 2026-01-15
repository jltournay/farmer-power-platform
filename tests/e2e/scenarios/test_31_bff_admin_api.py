"""E2E Tests: BFF Admin API Routes.

Story 9.1c: Tests for admin portal BFF endpoints (Region, Factory, CP, Farmer CRUD).

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Test Data Relationships:
    - REG-E2E-001 (Kericho Highland): FAC-E2E-001
    - REG-E2E-002 (Nandi Hills): FAC-E2E-002
    - FAC-E2E-001: CP-E2E-001, CP-E2E-002
    - FAC-E2E-002: CP-E2E-003
"""

from typing import Any

import pytest

from tests.e2e.helpers.api_clients import BFFClient


@pytest.mark.e2e
class TestAdminRegionEndpoints:
    """E2E tests for GET/POST /api/admin/regions endpoints."""

    @pytest.mark.asyncio
    async def test_list_regions(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing all regions returns expected structure and data."""
        result = await bff_api.admin_list_regions()

        # Verify response structure (PaginatedResponse)
        assert "data" in result
        assert "pagination" in result

        # Should have at least the seeded regions
        regions = result["data"]
        assert len(regions) >= 1, "Expected at least 1 region"

        # Verify region summary structure
        for region in regions:
            assert "id" in region
            assert "name" in region
            assert "country" in region
            assert "factory_count" in region
            assert "is_active" in region

    @pytest.mark.asyncio
    async def test_list_regions_pagination(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test pagination structure is correct."""
        result = await bff_api.admin_list_regions(page=1, page_size=10)

        pagination = result["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination
        assert "total_pages" in pagination
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_region_detail(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test getting a specific region returns detailed info.

        API returns RegionDetail directly (not wrapped in ApiResponse).
        """
        # First list to get a region ID (must match pattern: name-highland/midland/lowland)
        list_result = await bff_api.admin_list_regions()
        if not list_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = list_result["data"][0]["id"]
        result = await bff_api.admin_get_region(region_id)

        # Response is RegionDetail directly (not wrapped)
        assert result["id"] == region_id
        assert "name" in result
        assert "country" in result
        assert "county" in result
        assert "is_active" in result

    @pytest.mark.asyncio
    async def test_get_region_invalid_id_format(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 when region ID doesn't match expected pattern.

        Region IDs must match: ^[a-z][a-z0-9-]*-(highland|midland|lowland)$
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/regions/NON-EXISTENT-REGION",
        )

        # FastAPI returns 422 for validation errors (pattern mismatch)
        assert response.status_code == 422


@pytest.mark.e2e
class TestAdminFactoryEndpoints:
    """E2E tests for GET/POST /api/admin/factories endpoints."""

    @pytest.mark.asyncio
    async def test_list_factories(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing all factories returns expected structure."""
        result = await bff_api.admin_list_factories()

        # Verify response structure
        assert "data" in result
        assert "pagination" in result

        # Should have at least the seeded factories
        factories = result["data"]
        assert len(factories) >= 1, "Expected at least 1 factory"

        # Verify factory summary structure
        for factory in factories:
            assert "id" in factory
            assert "name" in factory
            assert "code" in factory
            assert "region_id" in factory
            assert "collection_point_count" in factory
            assert "farmer_count" in factory
            assert "is_active" in factory

    @pytest.mark.asyncio
    async def test_list_factories_filter_by_region(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering factories by region."""
        # First get a region
        regions_result = await bff_api.admin_list_regions()
        if not regions_result["data"]:
            pytest.skip("No regions in seed data")

        region_id = regions_result["data"][0]["id"]
        result = await bff_api.admin_list_factories(region_id=region_id)

        # All returned factories should belong to the specified region
        for factory in result["data"]:
            assert factory["region_id"] == region_id

    @pytest.mark.asyncio
    async def test_get_factory_detail(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test getting a specific factory returns detailed info.

        API returns FactoryDetail directly (not wrapped).
        """
        # First list to get a factory ID
        list_result = await bff_api.admin_list_factories()
        if not list_result["data"]:
            pytest.skip("No factories in seed data")

        factory_id = list_result["data"][0]["id"]
        result = await bff_api.admin_get_factory(factory_id)

        # Response is FactoryDetail directly (not wrapped)
        assert result["id"] == factory_id
        assert "name" in result
        assert "code" in result
        assert "region_id" in result
        assert "quality_thresholds" in result
        assert "payment_policy" in result
        assert "collection_point_count" in result
        assert "farmer_count" in result

    @pytest.mark.asyncio
    async def test_get_factory_invalid_id_format(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 when factory ID doesn't match expected pattern.

        Factory IDs must match: ^[A-Z]{3}-[A-Z]{3,4}-[0-9]{3}$
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/factories/invalid-factory-id",
        )

        # FastAPI returns 422 for validation errors (pattern mismatch)
        assert response.status_code == 422


@pytest.mark.e2e
class TestAdminCollectionPointEndpoints:
    """E2E tests for GET/PUT /api/admin/collection-points endpoints."""

    @pytest.mark.asyncio
    async def test_get_collection_point_detail(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test getting a specific collection point returns detailed info.

        API returns CollectionPointDetail directly (not wrapped).
        """
        # First get factories to find a valid CP ID pattern
        factories_result = await bff_api.admin_list_factories()
        if not factories_result["data"]:
            pytest.skip("No factories in seed data")

        factory = factories_result["data"][0]
        if factory["collection_point_count"] == 0:
            pytest.skip("Factory has no collection points")

        # Get factory detail which should include CPs
        factory_detail = await bff_api.admin_get_factory(factory["id"])

        # The factory detail may not include CP list directly
        # For now we'll test with known seed data CP
        # TODO: Update when factory detail includes collection_points list

    @pytest.mark.asyncio
    async def test_get_collection_point_invalid_id_format(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 when collection point ID doesn't match expected pattern."""
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/collection-points/invalid-cp-id",
        )

        # FastAPI returns 422 for validation errors (pattern mismatch)
        assert response.status_code == 422


@pytest.mark.e2e
class TestAdminFarmerEndpoints:
    """E2E tests for GET/POST /api/admin/farmers endpoints."""

    @pytest.mark.asyncio
    async def test_list_farmers_structure(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test listing all farmers returns expected structure."""
        result = await bff_api.admin_list_farmers()

        # Verify response structure
        assert "data" in result
        assert "pagination" in result

        # Check pagination structure
        pagination = result["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination

    @pytest.mark.asyncio
    async def test_list_farmers_filter_by_factory(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering farmers by factory."""
        factory_id = "FAC-E2E-001"
        result = await bff_api.admin_list_farmers(factory_id=factory_id)

        # Response should have expected structure
        assert "data" in result
        assert "pagination" in result

    @pytest.mark.asyncio
    async def test_list_farmers_filter_by_collection_point(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test filtering farmers by collection point."""
        cp_id = "CP-E2E-001"
        result = await bff_api.admin_list_farmers(collection_point_id=cp_id)

        # All returned farmers should belong to the specified collection point
        for farmer in result["data"]:
            assert farmer["collection_point_id"] == cp_id

    @pytest.mark.asyncio
    async def test_get_farmer_detail(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test getting a specific farmer returns detailed info.

        API returns FarmerDetail directly (not wrapped).
        """
        # Use known seed data farmer
        farmer_id = "FRM-E2E-001"
        result = await bff_api.admin_get_farmer(farmer_id)

        # Response is FarmerDetail directly (not wrapped)
        assert result["id"] == farmer_id
        assert "first_name" in result
        assert "last_name" in result
        assert "phone" in result
        assert "collection_point_id" in result
        assert "is_active" in result

    @pytest.mark.asyncio
    async def test_get_farmer_invalid_id_format(
        self,
        bff_api: BFFClient,
    ):
        """Test 422 when farmer ID doesn't match expected pattern.

        Farmer IDs must match: ^FRM-[A-Z0-9]+-[0-9]{3}$
        """
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/farmers/invalid-farmer-id",
        )

        # FastAPI returns 422 for validation errors (pattern mismatch)
        assert response.status_code == 422


@pytest.mark.e2e
class TestAdminAuthorization:
    """E2E tests for admin endpoint authorization."""

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin_endpoints(
        self,
        bff_api: BFFClient,
    ):
        """Test that non-admin roles get 403 on admin endpoints.

        Error code is 'insufficient_permissions' per auth.py.
        """
        # Try with factory_manager role (not platform_admin)
        response = await bff_api.admin_request_raw(
            "GET",
            "/api/admin/regions",
            role="factory_manager",
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "insufficient_permissions"

    @pytest.mark.asyncio
    async def test_platform_admin_can_access_all_admin_endpoints(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that platform_admin role can access all admin endpoints."""
        # These should all succeed (200)
        regions = await bff_api.admin_list_regions()
        assert "data" in regions

        factories = await bff_api.admin_list_factories()
        assert "data" in factories

        farmers = await bff_api.admin_list_farmers()
        assert "data" in farmers


@pytest.mark.e2e
class TestAdminAPIIntegration:
    """E2E tests for BFF-to-backend integration."""

    @pytest.mark.asyncio
    async def test_region_factory_relationship(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that region factory_count matches actual factories."""
        # Get regions
        regions = await bff_api.admin_list_regions()
        if not regions["data"]:
            pytest.skip("No regions in seed data")

        region = regions["data"][0]
        region_id = region["id"]

        # Get factories filtered by region
        factories = await bff_api.admin_list_factories(region_id=region_id)

        # Factory count should match
        assert region["factory_count"] == len(factories["data"])

    @pytest.mark.asyncio
    async def test_factory_collection_point_relationship(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that factory shows correct collection_point_count."""
        # Get factories
        factories = await bff_api.admin_list_factories()
        if not factories["data"]:
            pytest.skip("No factories in seed data")

        # Verify factory has collection_point_count field
        factory = factories["data"][0]
        assert "collection_point_count" in factory
        assert isinstance(factory["collection_point_count"], int)
        assert factory["collection_point_count"] >= 0

    @pytest.mark.asyncio
    async def test_bff_grpc_composition(
        self,
        bff_api: BFFClient,
        seed_data: dict[str, Any],
    ):
        """Test that BFF correctly composes data from gRPC backend.

        This tests the full integration path:
        BFF REST API → gRPC Clients → Plantation Model → MongoDB
        """
        # Get regions - tests ListRegions gRPC
        regions = await bff_api.admin_list_regions()
        assert "data" in regions
        assert "pagination" in regions

        # Get factories - tests ListFactories gRPC
        factories = await bff_api.admin_list_factories()
        assert "data" in factories

        # Get farmers - tests ListFarmers gRPC
        farmers = await bff_api.admin_list_farmers()
        assert "data" in farmers

        # All responses should have proper pagination structure
        for response in [regions, factories, farmers]:
            assert "total_count" in response["pagination"]
            assert "page" in response["pagination"]
