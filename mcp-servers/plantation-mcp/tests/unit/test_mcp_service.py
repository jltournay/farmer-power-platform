"""Unit tests for MCP Tool Service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_proto.mcp.v1 import mcp_tool_pb2

from plantation_mcp.api.mcp_service import McpToolServiceServicer
from plantation_mcp.infrastructure.plantation_client import (
    NotFoundError,
    PlantationClient,
    ServiceUnavailableError,
)


@pytest.fixture
def mock_plantation_client() -> MagicMock:
    """Create a mock PlantationClient."""
    return MagicMock(spec=PlantationClient)


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock gRPC context."""
    return MagicMock()


@pytest.fixture
def servicer(mock_plantation_client: MagicMock) -> McpToolServiceServicer:
    """Create the MCP service servicer with mocked client."""
    return McpToolServiceServicer(plantation_client=mock_plantation_client)


@pytest.fixture
def sample_farmer() -> dict:
    """Sample farmer data."""
    return {
        "farmer_id": "WM-0001",
        "first_name": "John",
        "last_name": "Mwangi",
        "phone": "+254712345678",
        "farm_size_hectares": 1.5,
        "farm_scale": "FARM_SCALE_MEDIUM",
        "region_id": "nyeri-highland",
        "collection_point_id": "nyeri-highland-cp-001",
        "notification_channel": "NOTIFICATION_CHANNEL_SMS",
        "interaction_pref": "INTERACTION_PREFERENCE_TEXT",
        "pref_lang": "PREFERRED_LANGUAGE_SW",
        "is_active": True,
    }


@pytest.fixture
def sample_farmer_summary() -> dict:
    """Sample farmer summary data."""
    return {
        "farmer_id": "WM-0001",
        "first_name": "John",
        "last_name": "Mwangi",
        "phone": "+254712345678",
        "collection_point_id": "nyeri-highland-cp-001",
        "farm_size_hectares": 1.5,
        "farm_scale": "FARM_SCALE_MEDIUM",
        "grading_model_id": "tbk_kenya_tea_v1",
        "grading_model_version": "1.0.0",
        "trend_direction": "TREND_DIRECTION_STABLE",
        "notification_channel": "NOTIFICATION_CHANNEL_SMS",
        "interaction_pref": "INTERACTION_PREFERENCE_TEXT",
        "pref_lang": "PREFERRED_LANGUAGE_SW",
        "historical": {
            "avg_grade": "B+",
            "total_kg": 180.0,
            "delivery_count": 12,
            "improvement_trend": "TREND_DIRECTION_IMPROVING",
        },
    }


class TestListTools:
    """Tests for ListTools RPC."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """AC #1, #2, #3, #4: ListTools returns all 4 tools with schemas."""
        request = mcp_tool_pb2.ListToolsRequest()

        response = await servicer.ListTools(request, mock_context)

        assert len(response.tools) == 4

        tool_names = {tool.name for tool in response.tools}
        assert tool_names == {
            "get_farmer",
            "get_farmer_summary",
            "get_collection_points",
            "get_farmers_by_collection_point",
        }

        # Verify each tool has schema
        for tool in response.tools:
            assert tool.name
            assert tool.description
            assert tool.input_schema_json
            assert tool.category == "query"

            # Verify schema is valid JSON
            schema = json.loads(tool.input_schema_json)
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    @pytest.mark.asyncio
    async def test_list_tools_with_category_filter(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """ListTools with category filter returns matching tools."""
        request = mcp_tool_pb2.ListToolsRequest(category="query")

        response = await servicer.ListTools(request, mock_context)

        assert len(response.tools) == 4
        for tool in response.tools:
            assert tool.category == "query"

    @pytest.mark.asyncio
    async def test_list_tools_with_nonexistent_category(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """ListTools with non-existent category returns empty list."""
        request = mcp_tool_pb2.ListToolsRequest(category="nonexistent")

        response = await servicer.ListTools(request, mock_context)

        assert len(response.tools) == 0


class TestGetFarmerTool:
    """Tests for get_farmer tool."""

    @pytest.mark.asyncio
    async def test_get_farmer_success(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
        sample_farmer: dict,
    ) -> None:
        """AC #1: get_farmer returns farmer details with preferences."""
        mock_plantation_client.get_farmer = AsyncMock(return_value=sample_farmer)

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer",
            arguments_json=json.dumps({"farmer_id": "WM-0001"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["farmer_id"] == "WM-0001"
        assert result["first_name"] == "John"
        assert result["notification_channel"] == "NOTIFICATION_CHANNEL_SMS"
        assert result["pref_lang"] == "PREFERRED_LANGUAGE_SW"

        mock_plantation_client.get_farmer.assert_called_once_with("WM-0001")

    @pytest.mark.asyncio
    async def test_get_farmer_not_found(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """get_farmer with non-existent farmer returns error."""
        mock_plantation_client.get_farmer = AsyncMock(
            side_effect=NotFoundError("Farmer not found: WM-9999")
        )

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer",
            arguments_json=json.dumps({"farmer_id": "WM-9999"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is False
        assert response.error_code == mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS
        assert "not found" in response.error_message.lower()


class TestGetFarmerSummaryTool:
    """Tests for get_farmer_summary tool."""

    @pytest.mark.asyncio
    async def test_get_farmer_summary_success(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
        sample_farmer_summary: dict,
    ) -> None:
        """AC #2: get_farmer_summary returns performance metrics."""
        mock_plantation_client.get_farmer_summary = AsyncMock(
            return_value=sample_farmer_summary
        )

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer_summary",
            arguments_json=json.dumps({"farmer_id": "WM-0001"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["farmer_id"] == "WM-0001"
        assert result["trend_direction"] == "TREND_DIRECTION_STABLE"
        assert "historical" in result
        assert result["historical"]["avg_grade"] == "B+"


class TestGetCollectionPointsTool:
    """Tests for get_collection_points tool."""

    @pytest.mark.asyncio
    async def test_get_collection_points_success(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """AC #3: get_collection_points returns factory collection points."""
        sample_cps = [
            {
                "collection_point_id": "nyeri-cp-001",
                "name": "Nyeri Central CP",
                "code": "NCP001",
                "factory_id": "nyeri-factory-001",
                "region_id": "nyeri-highland",
                "location": {"latitude": -0.4, "longitude": 36.9},
                "is_active": True,
            },
            {
                "collection_point_id": "nyeri-cp-002",
                "name": "Nyeri West CP",
                "code": "NCP002",
                "factory_id": "nyeri-factory-001",
                "region_id": "nyeri-highland",
                "location": {"latitude": -0.42, "longitude": 36.88},
                "is_active": True,
            },
        ]
        mock_plantation_client.get_collection_points = AsyncMock(return_value=sample_cps)

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_collection_points",
            arguments_json=json.dumps({"factory_id": "nyeri-factory-001"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert "collection_points" in result
        assert len(result["collection_points"]) == 2


class TestGetFarmersByCollectionPointTool:
    """Tests for get_farmers_by_collection_point tool."""

    @pytest.mark.asyncio
    async def test_get_farmers_by_collection_point_success(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
        sample_farmer: dict,
    ) -> None:
        """AC #4: get_farmers_by_collection_point returns farmers."""
        mock_plantation_client.get_farmers_by_collection_point = AsyncMock(
            return_value=[sample_farmer]
        )

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmers_by_collection_point",
            arguments_json=json.dumps({"collection_point_id": "nyeri-highland-cp-001"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert "farmers" in result
        assert len(result["farmers"]) == 1
        assert result["farmers"][0]["farmer_id"] == "WM-0001"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_invalid_arguments_missing_required(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """AC #6: Invalid arguments return INVALID_ARGUMENTS error."""
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer",
            arguments_json=json.dumps({}),  # Missing required farmer_id
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is False
        assert response.error_code == mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS
        assert "farmer_id" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_arguments(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Invalid JSON arguments return INVALID_ARGUMENTS error."""
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer",
            arguments_json="not valid json",
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is False
        assert response.error_code == mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS
        assert "invalid json" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_service_unavailable(
        self,
        servicer: McpToolServiceServicer,
        mock_plantation_client: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """AC #7: Service unavailable returns SERVICE_UNAVAILABLE error."""
        mock_plantation_client.get_farmer = AsyncMock(
            side_effect=ServiceUnavailableError("Plantation service unavailable")
        )

        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="get_farmer",
            arguments_json=json.dumps({"farmer_id": "WM-0001"}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is False
        assert response.error_code == mcp_tool_pb2.ERROR_CODE_SERVICE_UNAVAILABLE
        assert "unavailable" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_tool_not_found(
        self,
        servicer: McpToolServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """Unknown tool returns TOOL_NOT_FOUND error."""
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name="unknown_tool",
            arguments_json=json.dumps({}),
        )

        response = await servicer.CallTool(request, mock_context)

        assert response.success is False
        assert response.error_code == mcp_tool_pb2.ERROR_CODE_TOOL_NOT_FOUND
        assert "unknown_tool" in response.error_message
