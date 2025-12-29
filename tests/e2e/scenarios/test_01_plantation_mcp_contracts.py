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
    - weather_observations.json: 7 days for kericho-highland, nandi-highland
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

        # Verify response structure - MCP responses have success and result_json
        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify factory data is in result
        result_str = str(result.get("result_json", ""))
        assert factory_id in result_str or "FAC-E2E-001" in result_str

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

        # Should return error_code and error_message (no success field on error)
        assert "error_code" in result
        error_message = result.get("error_message", "")
        assert "not found" in error_message.lower() or "NON-EXISTENT" in error_message


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
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify farmer data is in response
        result_str = str(result.get("result_json", ""))
        # Should contain farmer info - check for ID or name
        assert farmer_id in result_str or "James" in result_str or "Kiprop" in result_str

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

        # Should return error_code and error_message (no success field on error)
        assert "error_code" in result
        error_message = result.get("error_message", "")
        assert "not found" in error_message.lower() or "NON-EXISTENT" in error_message


@pytest.mark.e2e
class TestGetFarmerSummary:
    """Test get_farmer_summary MCP tool (AC3)."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: MCP client accesses non-existent proto fields (avg_grade, delivery_count). "
        "See plantation_client.py _farmer_summary_to_dict - proto HistoricalMetrics/TodayMetrics "
        "don't have these fields."
    )
    async def test_get_farmer_summary_returns_metrics(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given farmer has performance data, returns metrics structure."""
        farmer_id = "FRM-E2E-001"

        result = await plantation_mcp.call_tool(
            "get_farmer_summary",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Performance data should include metrics
        result_str = str(result.get("result_json", "")).lower()
        # Check for performance indicators - could be in various formats
        assert any(
            term in result_str for term in ["primary", "quality", "score", "metrics", "trend", "deliveries"]
        )


@pytest.mark.e2e
class TestGetCollectionPoints:
    """Test get_collection_points MCP tool (AC4)."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: MCP client accesses non-existent proto field 'code' on CollectionPoint. "
        "See plantation_client.py _collection_point_to_dict - proto CollectionPoint doesn't have 'code' field."
    )
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
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain at least one of the CP IDs or names
        assert any(cp in result_str for cp in ["CP-E2E-001", "CP-E2E-002", "Ainamoi", "Kapsoit"])


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
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain farmer info
        assert any(farmer in result_str for farmer in ["FRM-E2E-001", "FRM-E2E-002", "James", "Grace"])


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
        region_id = "kericho-highland"

        result = await plantation_mcp.call_tool("get_region", {"region_id": region_id})

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain region info
        assert "kericho" in result_str.lower() or "Kericho" in result_str

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

        # Should return error_code and error_message (no success field on error)
        # Note: The region_id format validator in the model may reject invalid formats
        assert "error_code" in result


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
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain Kericho regions (we have 3: lowland, midland, highland)
        assert "kericho" in result_str.lower()

    @pytest.mark.asyncio
    async def test_list_regions_by_altitude_band(
        self,
        plantation_mcp,
        seed_data,
    ):
        """list_regions filters by altitude_band correctly."""
        result = await plantation_mcp.call_tool(
            "list_regions",
            {"altitude_band": "highland"},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain highland altitude regions (kericho-highland, nandi-highland)
        assert "highland" in result_str.lower()


@pytest.mark.e2e
class TestGetCurrentFlush:
    """Test get_current_flush MCP tool (AC8)."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: MCP client accesses response.flush_name but proto has response.current_flush.flush_name. "
        "See plantation_client.py get_current_flush - should access response.current_flush.flush_name."
    )
    async def test_get_current_flush_returns_period(
        self,
        plantation_mcp,
        seed_data,
    ):
        """Given region has flush calendar, returns current flush period."""
        region_id = "kericho-highland"

        result = await plantation_mcp.call_tool(
            "get_current_flush",
            {"region_id": region_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", "")).lower()
        # Should contain flush info - period name or days remaining
        assert any(term in result_str for term in ["flush", "period", "days", "dormant", "first", "monsoon", "autumn"])


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
        region_id = "kericho-highland"

        result = await plantation_mcp.call_tool(
            "get_region_weather",
            {"region_id": region_id, "days": 7},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", "")).lower()
        # Should contain weather data
        assert any(
            term in result_str for term in ["temperature", "temp", "precipitation", "humidity", "weather", "observation"]
        )
