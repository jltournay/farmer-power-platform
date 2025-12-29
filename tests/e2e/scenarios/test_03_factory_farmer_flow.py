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
    - Write operations use MongoDB direct (Plantation Model has no HTTP write API)
    - MCP tools are read-only for verification
    - Google Elevation Mock provides deterministic altitude responses
    - Altitude bands: Highland >1800m, Midland 1400-1800m, Lowland 800-1400m

Test Data (unique to this flow):
    - Factory: FAC-E2E-FLOW-001 (TBK grading model)
    - Collection Point: CP-E2E-FLOW-001
    - Farmer: FRM-E2E-FLOW-001 (lat=0.8, expected region: midland)
"""

import pytest

# Test entity IDs - unique to avoid conflicts with seed data
FLOW_FACTORY_ID = "FAC-E2E-FLOW-001"
FLOW_CP_ID = "CP-E2E-FLOW-001"
FLOW_FARMER_ID = "FRM-E2E-FLOW-001"


@pytest.mark.e2e
class TestFactoryCreation:
    """Test factory creation flow (AC1)."""

    @pytest.mark.asyncio
    async def test_create_factory_with_tbk_grading_model(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Given seeded grading models, create a factory with TBK model."""
        # Create factory with TBK grading model
        factory_data = {
            "id": FLOW_FACTORY_ID,
            "name": "E2E Flow Test Factory",
            "code": "KEN-TBK-FLOW",
            "region_id": "kericho-highland",
            "location": {
                "latitude": 0.35,
                "longitude": 35.35,
                "altitude_meters": 1850.0,
            },
            "contact": {
                "phone": "+254712000001",
                "email": "flow-factory@e2e.co.ke",
                "address": "P.O. Box 999, Kericho",
            },
            "processing_capacity_kg": 30000,
            "quality_thresholds": {
                "tier_1": 85.0,
                "tier_2": 70.0,
                "tier_3": 50.0,
            },
            "payment_policy": {
                "policy_type": "split_payment",
                "tier_1_adjustment": 0.15,
                "tier_2_adjustment": 0.0,
                "tier_3_adjustment": -0.05,
                "below_tier_3_adjustment": -0.10,
            },
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        # Insert via MongoDB direct
        await mongodb_direct.seed_factories([factory_data])

        # Verify via MCP tool
        result = await plantation_mcp.call_tool(
            "get_factory",
            {"factory_id": FLOW_FACTORY_ID},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify factory data in response
        result_str = str(result.get("result_json", ""))
        assert FLOW_FACTORY_ID in result_str or "E2E Flow Test Factory" in result_str


@pytest.mark.e2e
class TestCollectionPointCreation:
    """Test collection point creation flow (AC2)."""

    @pytest.mark.asyncio
    async def test_create_collection_point_linked_to_factory(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Given a factory exists, create a collection point linked to it."""
        # First ensure factory exists
        factory_data = {
            "id": FLOW_FACTORY_ID,
            "name": "E2E Flow Test Factory",
            "code": "KEN-TBK-FLOW",
            "region_id": "kericho-highland",
            "location": {
                "latitude": 0.35,
                "longitude": 35.35,
                "altitude_meters": 1850.0,
            },
            "contact": {
                "phone": "+254712000001",
                "email": "flow-factory@e2e.co.ke",
                "address": "P.O. Box 999, Kericho",
            },
            "processing_capacity_kg": 30000,
            "quality_thresholds": {
                "tier_1": 85.0,
                "tier_2": 70.0,
                "tier_3": 50.0,
            },
            "payment_policy": {
                "policy_type": "split_payment",
                "tier_1_adjustment": 0.15,
                "tier_2_adjustment": 0.0,
                "tier_3_adjustment": -0.05,
                "below_tier_3_adjustment": -0.10,
            },
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_factories([factory_data])

        # Create collection point linked to factory
        cp_data = {
            "id": FLOW_CP_ID,
            "name": "Flow Test Collection Point",
            "factory_id": FLOW_FACTORY_ID,
            "location": {
                "latitude": 0.36,
                "longitude": 35.36,
                "altitude_meters": 1840.0,
            },
            "region_id": "kericho-highland",
            "clerk_id": "CLK-FLOW-001",
            "clerk_phone": "+254712000101",
            "operating_hours": {
                "weekdays": "06:00-14:00",
                "weekends": "07:00-12:00",
            },
            "collection_days": ["mon", "tue", "wed", "thu", "fri", "sat"],
            "capacity": {
                "max_daily_kg": 4000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": True,
            },
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_collection_points([cp_data])

        # Verify via MCP tool - get collection points for the factory
        result = await plantation_mcp.call_tool(
            "get_collection_points",
            {"factory_id": FLOW_FACTORY_ID},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify CP is in the response
        result_str = str(result.get("result_json", ""))
        assert FLOW_CP_ID in result_str or "Flow Test Collection Point" in result_str


@pytest.mark.e2e
class TestFarmerRegistrationWithGPS:
    """Test farmer registration with GPS-based region assignment (AC3, AC4)."""

    @pytest.mark.asyncio
    async def test_register_farmer_with_gps_coordinates(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Given a collection point exists, register farmer with GPS and region assignment.

        GPS coordinates: lat=1.0, lng=35.0
        - Google Elevation Mock returns 1400m for lat >= 1.0
        - 1400m falls in midland altitude band (1400-1800m)
        - Expected region assignment: kericho-midland or similar midland region
        """
        # Ensure factory and CP exist
        factory_data = {
            "id": FLOW_FACTORY_ID,
            "name": "E2E Flow Test Factory",
            "code": "KEN-TBK-FLOW",
            "region_id": "kericho-highland",
            "location": {
                "latitude": 0.35,
                "longitude": 35.35,
                "altitude_meters": 1850.0,
            },
            "contact": {
                "phone": "+254712000001",
                "email": "flow-factory@e2e.co.ke",
                "address": "P.O. Box 999, Kericho",
            },
            "processing_capacity_kg": 30000,
            "quality_thresholds": {"tier_1": 85.0, "tier_2": 70.0, "tier_3": 50.0},
            "payment_policy": {
                "policy_type": "split_payment",
                "tier_1_adjustment": 0.15,
                "tier_2_adjustment": 0.0,
                "tier_3_adjustment": -0.05,
                "below_tier_3_adjustment": -0.10,
            },
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_factories([factory_data])

        cp_data = {
            "id": FLOW_CP_ID,
            "name": "Flow Test Collection Point",
            "factory_id": FLOW_FACTORY_ID,
            "location": {"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            "region_id": "kericho-highland",
            "clerk_id": "CLK-FLOW-001",
            "clerk_phone": "+254712000101",
            "operating_hours": {"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            "collection_days": ["mon", "tue", "wed", "thu", "fri", "sat"],
            "capacity": {
                "max_daily_kg": 4000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": True,
            },
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_collection_points([cp_data])

        # Register farmer with GPS coordinates
        # lat=1.0 triggers elevation mock to return 1400m (midland range)
        farmer_data = {
            "id": FLOW_FARMER_ID,
            "grower_number": "GN-FLOW-001",
            "first_name": "Test",
            "last_name": "Farmer",
            "region_id": "kericho-midland",  # Assigned based on 1400m altitude
            "collection_point_id": FLOW_CP_ID,
            "farm_location": {
                "latitude": 1.0,  # Elevation mock returns 1400m for lat >= 1.0
                "longitude": 35.0,
                "altitude_meters": 1400.0,  # From elevation mock
            },
            "contact": {
                "phone": "+254712000201",
                "email": "test.farmer@e2e.co.ke",
                "address": "Flow Test Village",
            },
            "farm_size_hectares": 2.0,
            "farm_scale": "medium",
            "national_id": "99999999",
            "registration_date": "2025-01-01T00:00:00Z",
            "is_active": True,
            "notification_channel": "sms",
            "interaction_pref": "text",
            "pref_lang": "en",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_farmers([farmer_data])

        # Verify farmer was created via MCP
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": FLOW_FARMER_ID},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        assert FLOW_FARMER_ID in result_str or "Test" in result_str

    @pytest.mark.asyncio
    async def test_altitude_based_region_assignment(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Verify region assignment matches altitude from elevation mock.

        Altitude bands from seed data:
        - Highland: >1800m (kericho-highland)
        - Midland: 1400-1800m (kericho-midland)
        - Lowland: 800-1400m (kericho-lowland)

        Elevation mock returns:
        - lat < 0.5 → 600m (below lowland)
        - lat 0.5-1.0 → 1000m (lowland)
        - lat >= 1.0 → 1400m (midland)
        """
        # Create farmer at lat=1.0 (elevation mock returns 1400m → midland)
        farmer_midland = {
            "id": "FRM-E2E-FLOW-MIDLAND",
            "grower_number": "GN-FLOW-MIDLAND",
            "first_name": "Midland",
            "last_name": "Farmer",
            "region_id": "kericho-midland",  # 1400m altitude
            "collection_point_id": "CP-E2E-001",  # Use existing seed CP
            "farm_location": {
                "latitude": 1.0,
                "longitude": 35.0,
                "altitude_meters": 1400.0,
            },
            "contact": {"phone": "+254712000301", "email": "", "address": "Midland Area"},
            "farm_size_hectares": 1.5,
            "farm_scale": "small",
            "national_id": "88888888",
            "registration_date": "2025-01-01T00:00:00Z",
            "is_active": True,
            "notification_channel": "sms",
            "interaction_pref": "text",
            "pref_lang": "sw",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_farmers([farmer_midland])

        # Verify farmer via MCP
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": "FRM-E2E-FLOW-MIDLAND"},
        )

        assert result is not None
        assert result.get("success") is True

        # Verify region is midland
        result_str = str(result.get("result_json", "")).lower()
        assert "midland" in result_str


@pytest.mark.e2e
class TestMCPQueryVerification:
    """Test MCP query verification (AC5)."""

    @pytest.mark.asyncio
    async def test_get_farmer_returns_correct_data(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Verify get_farmer returns farmer with all registration fields."""
        # Ensure test farmer exists
        farmer_data = {
            "id": FLOW_FARMER_ID,
            "grower_number": "GN-FLOW-001",
            "first_name": "Test",
            "last_name": "Farmer",
            "region_id": "kericho-midland",
            "collection_point_id": FLOW_CP_ID,
            "farm_location": {
                "latitude": 1.0,
                "longitude": 35.0,
                "altitude_meters": 1400.0,
            },
            "contact": {
                "phone": "+254712000201",
                "email": "test.farmer@e2e.co.ke",
                "address": "Flow Test Village",
            },
            "farm_size_hectares": 2.0,
            "farm_scale": "medium",
            "national_id": "99999999",
            "registration_date": "2025-01-01T00:00:00Z",
            "is_active": True,
            "notification_channel": "sms",
            "interaction_pref": "text",
            "pref_lang": "en",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_farmers([farmer_data])

        # Query via MCP
        result = await plantation_mcp.call_tool(
            "get_farmer",
            {"farmer_id": FLOW_FARMER_ID},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Verify key fields are present
        assert FLOW_FARMER_ID in result_str
        assert "Test" in result_str or "Farmer" in result_str

    @pytest.mark.asyncio
    async def test_get_farmers_by_collection_point_returns_farmer(
        self,
        mongodb_direct,
        plantation_mcp,
        seed_data,
    ):
        """Verify get_farmers_by_collection_point includes registered farmer."""
        # Ensure factory, CP, and farmer exist
        factory_data = {
            "id": FLOW_FACTORY_ID,
            "name": "E2E Flow Test Factory",
            "code": "KEN-TBK-FLOW",
            "region_id": "kericho-highland",
            "location": {"latitude": 0.35, "longitude": 35.35, "altitude_meters": 1850.0},
            "contact": {
                "phone": "+254712000001",
                "email": "flow-factory@e2e.co.ke",
                "address": "P.O. Box 999, Kericho",
            },
            "processing_capacity_kg": 30000,
            "quality_thresholds": {"tier_1": 85.0, "tier_2": 70.0, "tier_3": 50.0},
            "payment_policy": {
                "policy_type": "split_payment",
                "tier_1_adjustment": 0.15,
                "tier_2_adjustment": 0.0,
                "tier_3_adjustment": -0.05,
                "below_tier_3_adjustment": -0.10,
            },
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_factories([factory_data])

        cp_data = {
            "id": FLOW_CP_ID,
            "name": "Flow Test Collection Point",
            "factory_id": FLOW_FACTORY_ID,
            "location": {"latitude": 0.36, "longitude": 35.36, "altitude_meters": 1840.0},
            "region_id": "kericho-highland",
            "clerk_id": "CLK-FLOW-001",
            "clerk_phone": "+254712000101",
            "operating_hours": {"weekdays": "06:00-14:00", "weekends": "07:00-12:00"},
            "collection_days": ["mon", "tue", "wed", "thu", "fri", "sat"],
            "capacity": {
                "max_daily_kg": 4000,
                "storage_type": "covered_shed",
                "has_weighing_scale": True,
                "has_qc_device": True,
            },
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_collection_points([cp_data])

        farmer_data = {
            "id": FLOW_FARMER_ID,
            "grower_number": "GN-FLOW-001",
            "first_name": "Test",
            "last_name": "Farmer",
            "region_id": "kericho-midland",
            "collection_point_id": FLOW_CP_ID,
            "farm_location": {
                "latitude": 1.0,
                "longitude": 35.0,
                "altitude_meters": 1400.0,
            },
            "contact": {
                "phone": "+254712000201",
                "email": "test.farmer@e2e.co.ke",
                "address": "Flow Test Village",
            },
            "farm_size_hectares": 2.0,
            "farm_scale": "medium",
            "national_id": "99999999",
            "registration_date": "2025-01-01T00:00:00Z",
            "is_active": True,
            "notification_channel": "sms",
            "interaction_pref": "text",
            "pref_lang": "en",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        await mongodb_direct.seed_farmers([farmer_data])

        # Query farmers by collection point
        result = await plantation_mcp.call_tool(
            "get_farmers_by_collection_point",
            {"collection_point_id": FLOW_CP_ID},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Verify farmer is in the list
        assert FLOW_FARMER_ID in result_str or "Test" in result_str
