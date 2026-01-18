"""E2E Test: Farmer-CollectionPoint Assignment (Story 9.5a).

Tests the N:M relationship between Farmers and Collection Points.

Story 9.5a: Farmers are no longer linked to CPs via collection_point_id on Farmer.
Instead, CPs have a farmer_ids array, and farmers can be assigned to multiple CPs.

Acceptance Criteria tested:
1. AC1: Assign farmer to CP (farmer appears in CP.farmer_ids)
2. AC2: Unassign farmer from CP (farmer removed from CP.farmer_ids)
3. AC3: Idempotent assign (no duplicate entries)
4. AC4: Idempotent unassign (no error if farmer not in CP)
5. AC5: Multi-CP assignment (farmer can be in multiple CPs)
6. AC6: Error handling (404 for invalid IDs)

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Seed Data Required (from tests/e2e/infrastructure/seed/):
    - collection_points.json: kericho-highland-cp-100, kericho-highland-cp-101, nandi-highland-cp-100
    - farmers.json: FRM-E2E-001 to FRM-E2E-004
"""

import pytest


@pytest.mark.e2e
class TestAssignFarmerToCP:
    """Test assigning farmers to collection points (AC1)."""

    @pytest.mark.asyncio
    async def test_assign_farmer_to_cp_success(
        self,
        plantation_service,
        seed_data,
    ):
        """Given a farmer and CP exist, assign farmer to CP.

        AC1: Farmer appears in CP.farmer_ids after assignment.
        """
        # Use seeded farmer that may not be assigned to this CP yet
        farmer_id = "FRM-E2E-003"  # Assigned to kericho-highland-cp-101
        cp_id = "nandi-highland-cp-100"  # Different CP

        # Assign farmer to CP
        result = await plantation_service.assign_farmer_to_cp(cp_id, farmer_id)

        # Verify farmer is in CP's farmer_ids
        assert result is not None
        assert result.get("id") == cp_id
        assert farmer_id in result.get("farmer_ids", [])

    @pytest.mark.asyncio
    async def test_assign_farmer_to_cp_idempotent(
        self,
        plantation_service,
        seed_data,
    ):
        """Assigning same farmer twice should be idempotent (AC3).

        Uses MongoDB $addToSet for idempotency - no duplicate entries.
        """
        farmer_id = "FRM-E2E-001"
        cp_id = "kericho-highland-cp-100"  # Farmer already assigned in seed data

        # Assign twice
        result1 = await plantation_service.assign_farmer_to_cp(cp_id, farmer_id)
        result2 = await plantation_service.assign_farmer_to_cp(cp_id, farmer_id)

        # Both should succeed
        assert result1 is not None
        assert result2 is not None

        # Farmer should appear only once
        farmer_ids = result2.get("farmer_ids", [])
        count = farmer_ids.count(farmer_id)
        assert count == 1, f"Expected farmer to appear once, but appeared {count} times"


@pytest.mark.e2e
class TestUnassignFarmerFromCP:
    """Test unassigning farmers from collection points (AC2)."""

    @pytest.mark.asyncio
    async def test_unassign_farmer_from_cp_success(
        self,
        plantation_service,
        seed_data,
    ):
        """Given farmer is assigned to CP, unassign removes them.

        AC2: Farmer no longer in CP.farmer_ids after unassignment.
        """
        # First ensure farmer is assigned
        farmer_id = "FRM-E2E-002"
        cp_id = "kericho-highland-cp-100"

        # Assign first to ensure farmer is there
        await plantation_service.assign_farmer_to_cp(cp_id, farmer_id)

        # Unassign
        result = await plantation_service.unassign_farmer_from_cp(cp_id, farmer_id)

        # Verify farmer is not in CP's farmer_ids
        assert result is not None
        assert result.get("id") == cp_id
        assert farmer_id not in result.get("farmer_ids", [])

    @pytest.mark.asyncio
    async def test_unassign_farmer_idempotent(
        self,
        plantation_service,
        seed_data,
    ):
        """Unassigning farmer not in CP should be idempotent (AC4).

        Uses MongoDB $pull for idempotency - no error if farmer not present.
        """
        farmer_id = "FRM-E2E-004"  # Assigned to nandi-highland-cp-100
        cp_id = "kericho-highland-cp-100"  # Different CP

        # Unassign twice (farmer may not be in this CP)
        result1 = await plantation_service.unassign_farmer_from_cp(cp_id, farmer_id)
        result2 = await plantation_service.unassign_farmer_from_cp(cp_id, farmer_id)

        # Both should succeed without error
        assert result1 is not None
        assert result2 is not None


@pytest.mark.e2e
class TestMultiCPAssignment:
    """Test farmers assigned to multiple CPs (AC5)."""

    @pytest.mark.asyncio
    async def test_farmer_in_multiple_cps(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Farmer can be assigned to multiple collection points.

        AC5: N:M relationship - farmer appears in multiple CP.farmer_ids.
        """
        farmer_id = "FRM-E2E-001"
        cp1_id = "kericho-highland-cp-100"
        cp2_id = "kericho-highland-cp-101"

        # Assign farmer to both CPs
        result1 = await plantation_service.assign_farmer_to_cp(cp1_id, farmer_id)
        result2 = await plantation_service.assign_farmer_to_cp(cp2_id, farmer_id)

        # Verify farmer is in both CPs
        assert farmer_id in result1.get("farmer_ids", [])
        assert farmer_id in result2.get("farmer_ids", [])

        # Verify via get_farmers_by_collection_point
        mcp_result1 = await plantation_mcp.call_tool(
            "get_farmers_by_collection_point",
            {"collection_point_id": cp1_id},
        )
        mcp_result2 = await plantation_mcp.call_tool(
            "get_farmers_by_collection_point",
            {"collection_point_id": cp2_id},
        )

        # Farmer should appear in both CP queries
        assert mcp_result1.get("success") is True
        assert mcp_result2.get("success") is True
        result1_str = str(mcp_result1.get("result_json", ""))
        result2_str = str(mcp_result2.get("result_json", ""))
        assert farmer_id in result1_str
        assert farmer_id in result2_str


@pytest.mark.e2e
class TestAssignmentErrorHandling:
    """Test error handling for invalid assignments (AC6)."""

    @pytest.mark.asyncio
    async def test_assign_invalid_farmer_returns_error(
        self,
        plantation_service,
        seed_data,
    ):
        """Assigning non-existent farmer returns 404 error."""
        cp_id = "kericho-highland-cp-100"
        invalid_farmer_id = "NON-EXISTENT-FARMER"

        with pytest.raises(Exception) as exc_info:
            await plantation_service.assign_farmer_to_cp(cp_id, invalid_farmer_id)

        # Should be NOT_FOUND error
        error_str = str(exc_info.value).lower()
        assert "not found" in error_str or "not_found" in error_str

    @pytest.mark.asyncio
    async def test_assign_invalid_cp_returns_error(
        self,
        plantation_service,
        seed_data,
    ):
        """Assigning to non-existent CP returns 404 error."""
        farmer_id = "FRM-E2E-001"
        invalid_cp_id = "NON-EXISTENT-CP"

        with pytest.raises(Exception) as exc_info:
            await plantation_service.assign_farmer_to_cp(invalid_cp_id, farmer_id)

        # Should be NOT_FOUND error
        error_str = str(exc_info.value).lower()
        assert "not found" in error_str or "not_found" in error_str

    @pytest.mark.asyncio
    async def test_unassign_invalid_farmer_returns_error(
        self,
        plantation_service,
        seed_data,
    ):
        """Unassigning non-existent farmer returns 404 error."""
        cp_id = "kericho-highland-cp-100"
        invalid_farmer_id = "NON-EXISTENT-FARMER"

        with pytest.raises(Exception) as exc_info:
            await plantation_service.unassign_farmer_from_cp(cp_id, invalid_farmer_id)

        # Should be NOT_FOUND error
        error_str = str(exc_info.value).lower()
        assert "not found" in error_str or "not_found" in error_str

    @pytest.mark.asyncio
    async def test_unassign_invalid_cp_returns_error(
        self,
        plantation_service,
        seed_data,
    ):
        """Unassigning from non-existent CP returns 404 error."""
        farmer_id = "FRM-E2E-001"
        invalid_cp_id = "NON-EXISTENT-CP"

        with pytest.raises(Exception) as exc_info:
            await plantation_service.unassign_farmer_from_cp(invalid_cp_id, farmer_id)

        # Should be NOT_FOUND error
        error_str = str(exc_info.value).lower()
        assert "not found" in error_str or "not_found" in error_str
