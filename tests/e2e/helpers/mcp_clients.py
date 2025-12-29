"""gRPC clients for E2E testing.

Includes:
- PlantationMCPClient: MCP tool client for read operations
- PlantationServiceClient: Plantation Model gRPC client for write operations
- CollectionMCPClient: MCP tool client for Collection Model
"""

import json
from typing import Any

import grpc

# Import generated protobuf stubs
# Note: These imports assume fp-proto is in the PYTHONPATH
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from google.protobuf.json_format import MessageToDict


class PlantationMCPClient:
    """gRPC client for Plantation MCP Server."""

    def __init__(self, host: str = "localhost", port: int = 50052):
        self.address = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: mcp_tool_pb2_grpc.McpToolServiceStub | None = None

    async def __aenter__(self) -> "PlantationMCPClient":
        self._channel = grpc.aio.insecure_channel(self.address)
        self._stub = mcp_tool_pb2_grpc.McpToolServiceStub(self._channel)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._channel:
            await self._channel.close()

    @property
    def stub(self) -> mcp_tool_pb2_grpc.McpToolServiceStub:
        if self._stub is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._stub

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call an MCP tool by name."""
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name=tool_name,
            arguments_json=json.dumps(arguments),
        )
        response = await self.stub.CallTool(request)
        return MessageToDict(response, preserving_proto_field_name=True)

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools."""
        request = mcp_tool_pb2.ListToolsRequest()
        response = await self.stub.ListTools(request)
        return [MessageToDict(tool, preserving_proto_field_name=True) for tool in response.tools]

    # Convenience methods for common tools
    async def get_farmer(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer by ID via MCP tool."""
        return await self.call_tool("get_farmer", {"farmer_id": farmer_id})

    async def get_factory(self, factory_id: str) -> dict[str, Any]:
        """Get factory by ID via MCP tool."""
        return await self.call_tool("get_factory", {"factory_id": factory_id})

    async def search_farmers(
        self,
        factory_id: str | None = None,
        region: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search farmers via MCP tool."""
        args: dict[str, Any] = {"limit": limit}
        if factory_id:
            args["factory_id"] = factory_id
        if region:
            args["region"] = region
        return await self.call_tool("search_farmers", args)

    async def get_farmer_performance(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer performance summary via MCP tool."""
        return await self.call_tool("get_farmer_performance", {"farmer_id": farmer_id})


class CollectionMCPClient:
    """gRPC client for Collection MCP Server."""

    def __init__(self, host: str = "localhost", port: int = 50053):
        self.address = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: mcp_tool_pb2_grpc.McpToolServiceStub | None = None

    async def __aenter__(self) -> "CollectionMCPClient":
        self._channel = grpc.aio.insecure_channel(self.address)
        self._stub = mcp_tool_pb2_grpc.McpToolServiceStub(self._channel)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._channel:
            await self._channel.close()

    @property
    def stub(self) -> mcp_tool_pb2_grpc.McpToolServiceStub:
        if self._stub is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._stub

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call an MCP tool by name."""
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name=tool_name,
            arguments_json=json.dumps(arguments),
        )
        response = await self.stub.CallTool(request)
        return MessageToDict(response, preserving_proto_field_name=True)

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools."""
        request = mcp_tool_pb2.ListToolsRequest()
        response = await self.stub.ListTools(request)
        return [MessageToDict(tool, preserving_proto_field_name=True) for tool in response.tools]

    # Convenience methods for common tools
    async def get_document(self, document_id: str) -> dict[str, Any]:
        """Get document by ID via MCP tool."""
        return await self.call_tool("get_document", {"document_id": document_id})

    async def search_documents(
        self,
        farmer_id: str | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search documents via MCP tool."""
        args: dict[str, Any] = {"limit": limit}
        if farmer_id:
            args["farmer_id"] = farmer_id
        if source:
            args["source"] = source
        return await self.call_tool("search_documents", args)

    async def get_blob_sas_url(
        self,
        container_name: str,
        blob_name: str,
    ) -> dict[str, Any]:
        """Get SAS URL for blob access via MCP tool."""
        return await self.call_tool(
            "get_blob_sas_url",
            {"container_name": container_name, "blob_name": blob_name},
        )


class PlantationServiceError(Exception):
    """Exception raised when Plantation gRPC service returns an error."""

    def __init__(self, operation: str, code: grpc.StatusCode, details: str):
        self.operation = operation
        self.code = code
        self.details = details
        super().__init__(f"{operation} failed: [{code.name}] {details}")


class PlantationServiceClient:
    """gRPC client for Plantation Model Service (write operations).

    This client connects directly to the Plantation Model gRPC service
    for write operations (CreateFactory, CreateCollectionPoint, CreateFarmer).
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        self.address = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: plantation_pb2_grpc.PlantationServiceStub | None = None

    async def __aenter__(self) -> "PlantationServiceClient":
        self._channel = grpc.aio.insecure_channel(self.address)
        self._stub = plantation_pb2_grpc.PlantationServiceStub(self._channel)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._channel:
            await self._channel.close()

    @property
    def stub(self) -> plantation_pb2_grpc.PlantationServiceStub:
        if self._stub is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._stub

    async def create_factory(
        self,
        name: str,
        code: str,
        region_id: str,
        location: dict[str, float],
        contact: dict[str, str],
        processing_capacity_kg: int,
        quality_thresholds: dict[str, float] | None = None,
        payment_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a factory via gRPC."""
        # Build location message
        geo_location = plantation_pb2.GeoLocation(
            latitude=location.get("latitude", 0.0),
            longitude=location.get("longitude", 0.0),
            altitude_meters=location.get("altitude_meters", 0.0),
        )

        # Build contact message
        contact_info = plantation_pb2.ContactInfo(
            phone=contact.get("phone", ""),
            email=contact.get("email", ""),
            address=contact.get("address", ""),
        )

        # Build quality thresholds
        thresholds = None
        if quality_thresholds:
            thresholds = plantation_pb2.QualityThresholds(
                tier_1=quality_thresholds.get("tier_1", 85.0),
                tier_2=quality_thresholds.get("tier_2", 70.0),
                tier_3=quality_thresholds.get("tier_3", 50.0),
            )

        # Build payment policy
        policy = None
        if payment_policy:
            policy_type = plantation_pb2.PAYMENT_POLICY_TYPE_FEEDBACK_ONLY
            policy_type_str = payment_policy.get("policy_type", "feedback_only")
            if policy_type_str == "split_payment":
                policy_type = plantation_pb2.PAYMENT_POLICY_TYPE_SPLIT_PAYMENT
            elif policy_type_str == "weekly_bonus":
                policy_type = plantation_pb2.PAYMENT_POLICY_TYPE_WEEKLY_BONUS

            policy = plantation_pb2.PaymentPolicy(
                policy_type=policy_type,
                tier_1_adjustment=payment_policy.get("tier_1_adjustment", 0.0),
                tier_2_adjustment=payment_policy.get("tier_2_adjustment", 0.0),
                tier_3_adjustment=payment_policy.get("tier_3_adjustment", 0.0),
                below_tier_3_adjustment=payment_policy.get("below_tier_3_adjustment", 0.0),
            )

        request = plantation_pb2.CreateFactoryRequest(
            name=name,
            code=code,
            region_id=region_id,
            location=geo_location,
            contact=contact_info,
            processing_capacity_kg=processing_capacity_kg,
        )
        if thresholds:
            request.quality_thresholds.CopyFrom(thresholds)
        if policy:
            request.payment_policy.CopyFrom(policy)

        try:
            response = await self.stub.CreateFactory(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlantationServiceError(
                operation="CreateFactory",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def create_collection_point(
        self,
        name: str,
        factory_id: str,
        location: dict[str, float],
        region_id: str,
        clerk_id: str,
        clerk_phone: str,
        operating_hours: dict[str, str],
        collection_days: list[str],
        capacity: dict[str, Any],
        status: str = "active",
    ) -> dict[str, Any]:
        """Create a collection point via gRPC."""
        geo_location = plantation_pb2.GeoLocation(
            latitude=location.get("latitude", 0.0),
            longitude=location.get("longitude", 0.0),
            altitude_meters=location.get("altitude_meters", 0.0),
        )

        hours = plantation_pb2.OperatingHours(
            weekdays=operating_hours.get("weekdays", ""),
            weekends=operating_hours.get("weekends", ""),
        )

        cp_capacity = plantation_pb2.CollectionPointCapacity(
            max_daily_kg=capacity.get("max_daily_kg", 0),
            storage_type=capacity.get("storage_type", ""),
            has_weighing_scale=capacity.get("has_weighing_scale", False),
            has_qc_device=capacity.get("has_qc_device", False),
        )

        request = plantation_pb2.CreateCollectionPointRequest(
            name=name,
            factory_id=factory_id,
            location=geo_location,
            region_id=region_id,
            clerk_id=clerk_id,
            clerk_phone=clerk_phone,
            operating_hours=hours,
            collection_days=collection_days,
            capacity=cp_capacity,
            status=status,
        )

        try:
            response = await self.stub.CreateCollectionPoint(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlantationServiceError(
                operation="CreateCollectionPoint",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def create_farmer(
        self,
        first_name: str,
        last_name: str,
        collection_point_id: str,
        farm_location: dict[str, float],
        contact: dict[str, str],
        farm_size_hectares: float,
        national_id: str,
        grower_number: str = "",
    ) -> dict[str, Any]:
        """Create a farmer via gRPC.

        Note: region_id is auto-assigned based on GPS + altitude from elevation API.
        """
        geo_location = plantation_pb2.GeoLocation(
            latitude=farm_location.get("latitude", 0.0),
            longitude=farm_location.get("longitude", 0.0),
            altitude_meters=farm_location.get("altitude_meters", 0.0),
        )

        contact_info = plantation_pb2.ContactInfo(
            phone=contact.get("phone", ""),
            email=contact.get("email", ""),
            address=contact.get("address", ""),
        )

        request = plantation_pb2.CreateFarmerRequest(
            first_name=first_name,
            last_name=last_name,
            collection_point_id=collection_point_id,
            farm_location=geo_location,
            contact=contact_info,
            farm_size_hectares=farm_size_hectares,
            national_id=national_id,
            grower_number=grower_number,
        )

        try:
            response = await self.stub.CreateFarmer(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlantationServiceError(
                operation="CreateFarmer",
                code=e.code(),
                details=e.details() or str(e),
            ) from e
