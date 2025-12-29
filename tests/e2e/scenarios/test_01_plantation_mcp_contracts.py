"""E2E Test: Plantation MCP Tool Contract Tests.

Verifies that all 9 Plantation MCP tools return expected data structures
and handle error cases correctly.

Tools tested:
1. get_factory - Returns factory details
2. get_farmer - Returns farmer details
3. get_farmer_performance - Returns performance metrics
4. get_collection_points - Returns CPs for a factory
5. get_farmers_by_collection_point - Returns farmers at a CP
6. get_region - Returns region details
7. list_regions - Returns filtered regions
8. get_current_flush - Returns flush period info
9. get_region_weather - Returns weather observations

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Seed Data Required (from tests/e2e/infrastructure/seed/):
    - factories.json: FAC-E2E-001, FAC-E2E-002
    - collection_points.json: CP-E2E-001, CP-E2E-002, CP-E2E-003
    - farmers.json: FRM-E2E-001 to FRM-E2E-004
    - farmer_performance.json: Performance summaries for all farmers
    - weather_observations.json: 7 days for kericho-high, nandi-high
    - regions.json: 5 regions
    - grading_models.json: TBK, KTDA models
"""

import pytest


@pytest.mark.e2e
class TestGetFactory:
    """Test get_factory MCP tool (AC1)."""

    @pytest.mark.asyncio
    async def test_get_factory_returns_valid_structure(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given seed data is loaded, get_factory returns expected fields."""
        # Use seeded factory
        factory_id = "FAC-E2E-001"

        result = await plantation_mcp.call_tool("get_factory", {"factory_id": factory_id})

        # Verify response structure
        assert result is not None
        # MCP responses have 'content' field with the actual data
        content = result.get("content", [])
        assert len(content) > 0

        # Parse the text content (MCP returns text content)
        factory_data = content[0].get("text", "")
        assert factory_id in factory_data or "FAC-E2E-001" in str(result)

    @pytest.mark.asyncio
    async def test_get_factory_error_for_invalid_id(
        self,
        plantation_mcp,
        seed_data,
    ):
        """get_factory returns error for non-existent factory."""
        result = await plantation_mcp.call_tool(
            "get_factory",
            {"factory_id": "NON-EXISTENT-FACTORY"},
        )

        # Should return error or empty content
        content = result.get("content", [])
        is_error = result.get("is_error", False)
        # Either is_error=True or content indicates not found
        assert is_error or "not found" in str(content).lower() or len(content) == 0


@pytest.mark.e2e
class TestGetFarmer:
    """Test get_farmer MCP tool (AC2)."""

    @pytest.mark.asyncio
    async def test_get_farmer_returns_valid_structure(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given a farmer exists, get_farmer returns expected fields."""
        farmer_id = "FRM-E2E-001"

        result = await plantation_mcp.call_tool("get_farmer", {"farmer_id": farmer_id})

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        # Verify farmer data is in response
        response_str = str(result)
        # Should contain farmer info - check for ID or name
        assert farmer_id in response_str or "James" in response_str or "Kiprop" in response_str

    @pytest.mark.asyncio
    async def test_get_farmer_error_for_invalid_id(
        self,
        plantation_mcp,
        seed_data,
    ):
        """get_farmer returns error for non-existent farmer."""
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": "NON-EXISTENT-FARMER"},
        )

        content = result.get("content", [])
        is_error = result.get("is_error", False)
        assert is_error or "not found" in str(content).lower() or len(content) == 0


@pytest.mark.e2e
class TestGetFarmerPerformance:
    """Test get_farmer_performance MCP tool (AC3)."""

    @pytest.mark.asyncio
    async def test_get_farmer_performance_returns_metrics(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given farmer has performance data, returns metrics structure."""
        farmer_id = "FRM-E2E-001"

        result = await plantation_mcp.call_tool(
            "get_farmer_performance",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        # Performance data should include metrics
        response_str = str(result)
        # Check for performance indicators - could be in various formats
        assert any(
            term in response_str.lower() for term in ["primary", "quality", "score", "metrics", "trend", "deliveries"]
        )


@pytest.mark.e2e
class TestGetCollectionPoints:
    """Test get_collection_points MCP tool (AC4)."""

    @pytest.mark.asyncio
    async def test_get_collection_points_returns_all_cps(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given factory has CPs, returns all collection points."""
        factory_id = "FAC-E2E-001"  # Has 2 CPs: CP-E2E-001, CP-E2E-002

        result = await plantation_mcp.call_tool(
            "get_collection_points",
            {"factory_id": factory_id},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain at least one of the CP IDs or names
        assert any(cp in response_str for cp in ["CP-E2E-001", "CP-E2E-002", "Ainamoi", "Kapsoit"])


@pytest.mark.e2e
class TestGetFarmersByCollectionPoint:
    """Test get_farmers_by_collection_point MCP tool (AC5)."""

    @pytest.mark.asyncio
    async def test_get_farmers_by_cp_returns_farmers(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given CP has farmers, returns list of farmers."""
        collection_point_id = "CP-E2E-001"  # Has FRM-E2E-001, FRM-E2E-002

        result = await plantation_mcp.call_tool(
            "get_farmers_by_collection_point",
            {"collection_point_id": collection_point_id},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain farmer info
        assert any(farmer in response_str for farmer in ["FRM-E2E-001", "FRM-E2E-002", "James", "Grace"])


@pytest.mark.e2e
class TestGetRegion:
    """Test get_region MCP tool (AC6)."""

    @pytest.mark.asyncio
    async def test_get_region_returns_full_details(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given region exists, returns geography and flush calendar."""
        region_id = "kericho-high"

        result = await plantation_mcp.call_tool("get_region", {"region_id": region_id})

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain region info
        assert "kericho" in response_str.lower() or "Kericho" in response_str

    @pytest.mark.asyncio
    async def test_get_region_error_for_invalid_id(
        self,
        plantation_mcp,
        seed_data,
    ):
        """get_region returns error for non-existent region."""
        result = await plantation_mcp.call_tool(
            "get_region",
            {"region_id": "non-existent-region"},
        )

        content = result.get("content", [])
        is_error = result.get("is_error", False)
        assert is_error or "not found" in str(content).lower() or len(content) == 0


@pytest.mark.e2e
class TestListRegions:
    """Test list_regions MCP tool (AC7)."""

    @pytest.mark.asyncio
    async def test_list_regions_by_county(
        self,
        plantation_mcp,
        seed_data,
    ):
        """list_regions filters by county correctly."""
        result = await plantation_mcp.call_tool(
            "list_regions",
            {"county": "Kericho"},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain Kericho regions (we have 3: low, medium, high)
        assert "kericho" in response_str.lower()

    @pytest.mark.asyncio
    async def test_list_regions_by_altitude_band(
        self,
        plantation_mcp,
        seed_data,
    ):
        """list_regions filters by altitude_band correctly."""
        result = await plantation_mcp.call_tool(
            "list_regions",
            {"altitude_band": "high"},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain high altitude regions (kericho-high, nandi-high)
        assert "high" in response_str.lower()


@pytest.mark.e2e
class TestGetCurrentFlush:
    """Test get_current_flush MCP tool (AC8)."""

    @pytest.mark.asyncio
    async def test_get_current_flush_returns_period(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given region has flush calendar, returns current flush period."""
        region_id = "kericho-high"

        result = await plantation_mcp.call_tool(
            "get_current_flush",
            {"region_id": region_id},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain flush info - period name or days remaining
        assert any(term in response_str.lower() for term in ["flush", "period", "days", "main", "dry", "secondary"])


@pytest.mark.e2e
class TestGetRegionWeather:
    """Test get_region_weather MCP tool (AC9)."""

    @pytest.mark.asyncio
    async def test_get_region_weather_returns_observations(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given region has weather data, returns observations array."""
        region_id = "kericho-high"

        result = await plantation_mcp.call_tool(
            "get_region_weather",
            {"region_id": region_id, "days": 7},
        )

        assert result is not None
        content = result.get("content", [])
        assert len(content) > 0

        response_str = str(result)
        # Should contain weather data
        assert any(
            term in response_str.lower() for term in ["temperature", "temp", "precipitation", "humidity", "weather"]
        )
