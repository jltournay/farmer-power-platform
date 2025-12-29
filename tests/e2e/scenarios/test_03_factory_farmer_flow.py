"""E2E Test: Factory-Farmer Registration Flow.

Tests the complete registration flow: Factory → Collection Point → Farmer,
validating that GPS-based region assignment works correctly via the
Google Elevation mock.

Acceptance Criteria:
1. AC1: Factory Creation - Create factory with TBK grading model
2. AC2: Collection Point Creation - Create CP linked to factory
3. AC3: Farmer Registration with GPS - Create farmer with GPS coordinates
4. AC4: Altitude-Based Region Assignment - Region assigned based on elevation
5. AC5: MCP Query Verification - Verify via get_farmer, get_farmers_by_collection_point

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Architecture Notes:
    - Write operations use Plantation gRPC API (CreateFactory, CreateFarmer, etc.)
    - Read/verification via MCP tools (plantation_mcp fixture)
    - Google Elevation Mock provides deterministic altitude responses
    - Altitude bands: Highland >1800m, Midland 1400-1800m, Lowland 800-1400m

Test Data (dynamically created per test):
    - Factory codes: KEN-TBK-FLOW-* (unique per test)
    - Collection Points: Created dynamically, linked to test factories
    - Farmers: Created with GPS coordinates for elevation mock testing

Google Elevation Mock Behavior:
    - lat < 0.5 → 600m (lowland)
    - 0.5 <= lat < 1.0 → 1000m (lowland: 800-1400m)
    - lat >= 1.0 → 1400m (midland: 1400-1800m)
"""

import pytest


@pytest.mark.e2e
class TestFactoryCreation:
    """Test factory creation flow (AC1)."""

    @pytest.mark.asyncio
    async def test_create_factory_with_tbk_grading_model(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Given seeded grading models, create a factory with TBK model via gRPC.

        AC1: Factory is created in a region that uses TBK grading model.
        The TBK grading model is pre-seeded and associated with regions.
        Factory inherits grading model configuration via region_id.
        """
        # Create factory via Plantation gRPC API
        # Note: TBK grading model is seeded and associated with kericho regions
        factory = await plantation_service.create_factory(
            name="E2E Flow Test Factory",
            code="KEN-TBK-FLOW",
            region_id="kericho-highland",
            location={
                "latitude": 0.35,
                "longitude": 35.35,
                "altitude_meters": 1850.0,
            },
            contact={
                "phone": "+254712000001",
                "email": "flow-factory@e2e.co.ke",
                "address": "P.O. Box 999, Kericho",
            },
            processing_capacity_kg=30000,
            quality_thresholds={
                "tier_1": 85.0,
                "tier_2": 70.0,
                "tier_3": 50.0,
            },
            payment_policy={
                "policy_type": "split_payment",
                "tier_1_adjustment": 0.15,
                "tier_2_adjustment": 0.0,
                "tier_3_adjustment": -0.05,
                "below_tier_3_adjustment": -0.10,
            },
        )

        # Verify factory was created
        assert factory is not None
        factory_id = factory.get("id")
        assert factory_id is not None

        # Verify via MCP tool
        result = await plantation_mcp.call_tool(
            "get_factory",
            {"factory_id": factory_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify factory data in response
        result_str = str(result.get("result_json", ""))
        assert factory_id in result_str or "E2E Flow Test Factory" in result_str


@pytest.mark.e2e
class TestCollectionPointCreation:
    """Test collection point creation flow (AC2)."""

    @pytest.mark.asyncio
    async def test_create_collection_point_linked_to_factory(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Given a factory exists, create a collection point linked to it."""
        # First create factory
        factory = await plantation_service.create_factory(
            name="E2E Flow CP Test Factory",
            code="KEN-TBK-FLOW-CP",
            region_id="kericho-highland",
            location={"latitude": 0.35, "longitude": 35.35, "altitude_meters": 1850.0},
            contact={
                "phone": "+254712000002",
                "email": "flow-cp-factory@e2e.co.ke",
                "address": "P.O. Box 998, Kericho",
            },
            processing_capacity_kg=25000,
        )
        factory_id = factory.get("id")

        # Create collection point linked to factory
        cp = await plantation_service.create_collection_point(
            name="Flow Test Collection Point",
            factory_id=factory_id,
            location={"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            region_id="kericho-highland",
            clerk_id="CLK-FLOW-001",
            clerk_phone="+254712000101",
            operating_hours={"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            collection_days=["mon", "tue", "wed", "thu", "fri", "sat"],
            capacity={
                "max_daily_kg": 4000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": True,
            },
            status="active",
        )

        # Verify CP was created
        assert cp is not None
        cp_id = cp.get("id")
        assert cp_id is not None

        # Verify via MCP tool - get collection points for the factory
        result = await plantation_mcp.call_tool(
            "get_collection_points",
            {"factory_id": factory_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify CP is in the response
        result_str = str(result.get("result_json", ""))
        assert cp_id in result_str or "Flow Test Collection Point" in result_str


@pytest.mark.e2e
class TestFarmerRegistrationWithGPS:
    """Test farmer registration with GPS-based region assignment (AC3, AC4)."""

    @pytest.mark.asyncio
    async def test_register_farmer_with_gps_coordinates(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Given a collection point exists, register farmer with GPS.

        GPS coordinates: lat=1.0, lng=35.0
        - Google Elevation Mock returns 1400m for lat >= 1.0
        - 1400m falls in midland altitude band (1400-1800m)
        - Expected region assignment: midland
        """
        # Create factory
        factory = await plantation_service.create_factory(
            name="E2E Flow Farmer Test Factory",
            code="KEN-TBK-FLOW-FRM",
            region_id="kericho-highland",
            location={"latitude": 0.35, "longitude": 35.35, "altitude_meters": 1850.0},
            contact={
                "phone": "+254712000003",
                "email": "flow-farmer-factory@e2e.co.ke",
                "address": "P.O. Box 997, Kericho",
            },
            processing_capacity_kg=20000,
        )
        factory_id = factory.get("id")

        # Create collection point
        cp = await plantation_service.create_collection_point(
            name="Flow Farmer Test CP",
            factory_id=factory_id,
            location={"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            region_id="kericho-highland",
            clerk_id="CLK-FLOW-002",
            clerk_phone="+254712000102",
            operating_hours={"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            collection_days=["mon", "wed", "fri"],
            capacity={
                "max_daily_kg": 3000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": False,
            },
        )
        cp_id = cp.get("id")

        # Register farmer with GPS coordinates
        # lat=1.0 triggers elevation mock to return 1400m (midland range)
        farmer = await plantation_service.create_farmer(
            first_name="Test",
            last_name="Farmer",
            collection_point_id=cp_id,
            farm_location={
                "latitude": 1.0,  # Elevation mock returns 1400m for lat >= 1.0
                "longitude": 35.0,
                "altitude_meters": 0.0,  # Will be set by elevation lookup
            },
            contact={
                "phone": "+254712000201",
                "email": "test.farmer@e2e.co.ke",
                "address": "Flow Test Village",
            },
            farm_size_hectares=2.0,
            national_id="99999999",
            grower_number="GN-FLOW-001",
        )

        # Verify farmer was created
        assert farmer is not None
        farmer_id = farmer.get("id")
        assert farmer_id is not None

        # Verify farmer via MCP
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        assert farmer_id in result_str or "Test" in result_str

    @pytest.mark.asyncio
    async def test_altitude_based_region_assignment(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Verify region assignment based on altitude from elevation mock (AC4).

        Elevation mock returns:
        - lat < 0.5 → 600m (lowland)
        - 0.5 <= lat < 1.0 → 1000m (lowland: 800-1400m)
        - lat >= 1.0 → 1400m (midland: 1400-1800m)

        This test creates a farmer at lat=1.0 and verifies the region
        is assigned to a midland region based on the 1400m altitude.
        """
        # First create factory and collection point for this test
        factory = await plantation_service.create_factory(
            name="E2E Altitude Test Factory",
            code="KEN-TBK-FLOW-ALT",
            region_id="kericho-midland",  # Use midland region
            location={"latitude": 1.0, "longitude": 35.0, "altitude_meters": 1400.0},
            contact={
                "phone": "+254712000005",
                "email": "altitude-test@e2e.co.ke",
                "address": "P.O. Box 995, Kericho",
            },
            processing_capacity_kg=10000,
        )
        factory_id = factory.get("id")

        cp = await plantation_service.create_collection_point(
            name="Altitude Test CP",
            factory_id=factory_id,
            location={"latitude": 1.0, "longitude": 35.0, "altitude_meters": 1400.0},
            region_id="kericho-midland",
            clerk_id="CLK-FLOW-ALT",
            clerk_phone="+254712000105",
            operating_hours={"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            collection_days=["mon", "wed", "fri"],
            capacity={
                "max_daily_kg": 2000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": False,
            },
        )
        cp_id = cp.get("id")

        # Create farmer at lat=1.0 (elevation mock returns 1400m → midland)
        farmer = await plantation_service.create_farmer(
            first_name="Altitude",
            last_name="Test",
            collection_point_id=cp_id,
            farm_location={
                "latitude": 1.0,  # Elevation mock returns 1400m
                "longitude": 35.0,
                "altitude_meters": 0.0,  # Will be set by elevation lookup
            },
            contact={"phone": "+254712000301", "email": "", "address": "Midland Area"},
            farm_size_hectares=1.5,
            national_id="88888888",
            grower_number="GN-FLOW-ALT",
        )

        farmer_id = farmer.get("id")
        assert farmer_id is not None

        # Verify farmer via MCP - check region assignment
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"

        # AC4: Verify the region altitude band is "midland" (1400-1800m range)
        result_str = str(result.get("result_json", "")).lower()
        assert "midland" in result_str, (
            f"Expected farmer to be assigned to a midland region "
            f"(1400m altitude from mock), but got: {result.get('result_json')}"
        )


@pytest.mark.e2e
class TestMCPQueryVerification:
    """Test MCP query verification (AC5)."""

    @pytest.mark.asyncio
    async def test_get_farmer_returns_correct_data(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Verify get_farmer returns farmer with all registration fields."""
        # Create factory and CP for this test (avoid seed data dependency)
        factory = await plantation_service.create_factory(
            name="E2E Query Farmer Factory",
            code="KEN-TBK-FLOW-QF",
            region_id="kericho-highland",
            location={"latitude": 0.35, "longitude": 35.35, "altitude_meters": 1850.0},
            contact={
                "phone": "+254712000006",
                "email": "query-farmer@e2e.co.ke",
                "address": "P.O. Box 994, Kericho",
            },
            processing_capacity_kg=12000,
        )
        factory_id = factory.get("id")

        cp = await plantation_service.create_collection_point(
            name="Query Farmer Test CP",
            factory_id=factory_id,
            location={"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            region_id="kericho-highland",
            clerk_id="CLK-FLOW-QF",
            clerk_phone="+254712000106",
            operating_hours={"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            collection_days=["mon", "wed", "fri"],
            capacity={
                "max_daily_kg": 2000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": False,
            },
        )
        cp_id = cp.get("id")

        # Create a farmer for this test
        farmer = await plantation_service.create_farmer(
            first_name="Query",
            last_name="Test",
            collection_point_id=cp_id,
            farm_location={"latitude": 0.9, "longitude": 35.0, "altitude_meters": 0.0},
            contact={
                "phone": "+254712000401",
                "email": "query.test@e2e.co.ke",
                "address": "Query Test Village",
            },
            farm_size_hectares=2.5,
            national_id="77777777",
            grower_number="GN-FLOW-QUERY",
        )

        farmer_id = farmer.get("id")

        # Query via MCP
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Verify key fields are present
        assert farmer_id in result_str
        assert "Query" in result_str or "Test" in result_str

    @pytest.mark.asyncio
    async def test_get_farmers_by_collection_point_returns_farmer(
        self,
        plantation_service,
        plantation_mcp,
        seed_data,
    ):
        """Verify get_farmers_by_collection_point includes registered farmer."""
        # Create factory and CP
        factory = await plantation_service.create_factory(
            name="E2E Flow Query CP Factory",
            code="KEN-TBK-FLOW-QCP",
            region_id="kericho-highland",
            location={"latitude": 0.35, "longitude": 35.35, "altitude_meters": 1850.0},
            contact={
                "phone": "+254712000004",
                "email": "flow-query-cp@e2e.co.ke",
                "address": "P.O. Box 996, Kericho",
            },
            processing_capacity_kg=15000,
        )
        factory_id = factory.get("id")

        cp = await plantation_service.create_collection_point(
            name="Query CP Test",
            factory_id=factory_id,
            location={"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            region_id="kericho-highland",
            clerk_id="CLK-FLOW-003",
            clerk_phone="+254712000103",
            operating_hours={"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            collection_days=["mon", "wed", "fri", "sat"],
            capacity={
                "max_daily_kg": 2500,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": True,
            },
        )
        cp_id = cp.get("id")

        # Create farmer linked to this CP
        farmer = await plantation_service.create_farmer(
            first_name="CPQuery",
            last_name="Farmer",
            collection_point_id=cp_id,
            farm_location={"latitude": 0.9, "longitude": 35.0, "altitude_meters": 0.0},
            contact={
                "phone": "+254712000501",
                "email": "cpquery.farmer@e2e.co.ke",
                "address": "CP Query Village",
            },
            farm_size_hectares=1.8,
            national_id="66666666",
            grower_number="GN-FLOW-CPQ",
        )
        farmer_id = farmer.get("id")

        # Query farmers by collection point
        result = await plantation_mcp.call_tool(
            "get_farmers_by_collection_point",
            {"collection_point_id": cp_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Verify farmer is in the list
        assert farmer_id in result_str or "CPQuery" in result_str
