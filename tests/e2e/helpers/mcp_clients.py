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
        farm_location: dict[str, float],
        contact: dict[str, str],
        farm_size_hectares: float,
        national_id: str,
        grower_number: str = "",
    ) -> dict[str, Any]:
        """Create a farmer via gRPC.

        Story 9.5a: collection_point_id removed from CreateFarmerRequest.
        Use assign_farmer_to_cp() separately to assign farmer to a collection point.

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

    async def assign_farmer_to_cp(
        self,
        collection_point_id: str,
        farmer_id: str,
    ) -> dict[str, Any]:
        """Assign a farmer to a collection point (Story 9.5a).

        Args:
            collection_point_id: Collection point ID to assign farmer to.
            farmer_id: Farmer ID to assign.

        Returns:
            Updated CollectionPoint with farmer_ids.
        """
        request = plantation_pb2.AssignFarmerRequest(
            collection_point_id=collection_point_id,
            farmer_id=farmer_id,
        )

        try:
            response = await self.stub.AssignFarmerToCollectionPoint(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlantationServiceError(
                operation="AssignFarmerToCollectionPoint",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def unassign_farmer_from_cp(
        self,
        collection_point_id: str,
        farmer_id: str,
    ) -> dict[str, Any]:
        """Unassign a farmer from a collection point (Story 9.5a).

        Args:
            collection_point_id: Collection point ID to unassign farmer from.
            farmer_id: Farmer ID to unassign.

        Returns:
            Updated CollectionPoint with farmer_ids.
        """
        request = plantation_pb2.UnassignFarmerRequest(
            collection_point_id=collection_point_id,
            farmer_id=farmer_id,
        )

        try:
            response = await self.stub.UnassignFarmerFromCollectionPoint(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlantationServiceError(
                operation="UnassignFarmerFromCollectionPoint",
                code=e.code(),
                details=e.details() or str(e),
            ) from e


class CollectionServiceError(Exception):
    """Exception raised when Collection gRPC service returns an error."""

    def __init__(self, operation: str, code: grpc.StatusCode, details: str):
        self.operation = operation
        self.code = code
        self.details = details
        super().__init__(f"{operation} failed: [{code.name}] {details}")


class CollectionServiceClient:
    """gRPC client for Collection Model Service (Story 0.5.1a).

    This client connects directly to the Collection Model gRPC service
    for document queries via BFF.
    """

    def __init__(self, host: str = "localhost", port: int = 50054):
        self.address = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        # Note: Using Any for stub type because proto imports are deferred to __aenter__
        # to avoid import failures when protos are not yet generated
        self._stub: Any | None = None  # CollectionServiceStub at runtime

    async def __aenter__(self) -> "CollectionServiceClient":
        # Import here to avoid import errors when proto not generated
        from fp_proto.collection.v1 import collection_pb2_grpc

        self._channel = grpc.aio.insecure_channel(self.address)
        self._stub = collection_pb2_grpc.CollectionServiceStub(self._channel)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._channel:
            await self._channel.close()

    @property
    def stub(self) -> Any:
        if self._stub is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._stub

    async def get_document(
        self,
        document_id: str,
        collection_name: str,
    ) -> dict[str, Any]:
        """Get document by ID via gRPC."""
        from fp_proto.collection.v1 import collection_pb2

        request = collection_pb2.GetDocumentRequest(
            document_id=document_id,
            collection_name=collection_name,
        )
        try:
            response = await self.stub.GetDocument(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise CollectionServiceError(
                operation="GetDocument",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def list_documents(
        self,
        collection_name: str,
        farmer_id: str | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List documents with pagination via gRPC."""
        from fp_proto.collection.v1 import collection_pb2

        request = collection_pb2.ListDocumentsRequest(
            collection_name=collection_name,
            farmer_id=farmer_id or "",
            page_size=page_size,
            page_token=page_token or "",
        )
        try:
            response = await self.stub.ListDocuments(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise CollectionServiceError(
                operation="ListDocuments",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_documents_by_farmer(
        self,
        farmer_id: str,
        collection_name: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get all documents for a farmer via gRPC."""
        from fp_proto.collection.v1 import collection_pb2

        request = collection_pb2.GetDocumentsByFarmerRequest(
            farmer_id=farmer_id,
            collection_name=collection_name,
            limit=limit,
        )
        try:
            response = await self.stub.GetDocumentsByFarmer(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise CollectionServiceError(
                operation="GetDocumentsByFarmer",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def search_documents(
        self,
        collection_name: str,
        source_id: str | None = None,
        linkage_filters: dict[str, str] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Search documents with filters via gRPC."""
        from fp_proto.collection.v1 import collection_pb2

        request = collection_pb2.SearchDocumentsRequest(
            collection_name=collection_name,
            source_id=source_id or "",
            linkage_filters=linkage_filters or {},
            page_size=page_size,
            page_token=page_token or "",
        )
        try:
            response = await self.stub.SearchDocuments(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise CollectionServiceError(
                operation="SearchDocuments",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def check_connectivity(self) -> bool:
        """Check if gRPC service is reachable."""
        from fp_proto.collection.v1 import collection_pb2

        try:
            # Try to list documents with no filter - should return empty or results
            request = collection_pb2.ListDocumentsRequest(
                collection_name="test_connectivity",
                page_size=1,
            )
            await self.stub.ListDocuments(request)
            return True
        except grpc.RpcError:
            # Any response (even error) means the service is reachable
            return True
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# Platform Cost Service gRPC Client (Story 13.8)
# ═══════════════════════════════════════════════════════════════════════════════


class PlatformCostServiceError(Exception):
    """Exception raised when Platform Cost gRPC service returns an error."""

    def __init__(self, operation: str, code: grpc.StatusCode, details: str):
        self.operation = operation
        self.code = code
        self.details = details
        super().__init__(f"{operation} failed: [{code.name}] {details}")


class PlatformCostServiceClient:
    """gRPC client for Platform Cost Service (Story 13.8).

    This client connects directly to the Platform Cost gRPC service
    (UnifiedCostService) for cost queries and budget management.
    """

    def __init__(self, host: str = "localhost", port: int = 50055):
        self.address = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: Any | None = None

    async def __aenter__(self) -> "PlatformCostServiceClient":
        from fp_proto.platform_cost.v1 import platform_cost_pb2_grpc

        self._channel = grpc.aio.insecure_channel(self.address)
        self._stub = platform_cost_pb2_grpc.UnifiedCostServiceStub(self._channel)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._channel:
            await self._channel.close()

    @property
    def stub(self) -> Any:
        if self._stub is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._stub

    async def get_cost_summary(
        self,
        start_date: str,
        end_date: str,
        factory_id: str | None = None,
    ) -> dict[str, Any]:
        """Get cost summary for a date range via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.CostSummaryRequest(
            start_date=start_date,
            end_date=end_date,
        )
        if factory_id:
            request.factory_id = factory_id

        try:
            response = await self.stub.GetCostSummary(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetCostSummary",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_daily_cost_trend(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get daily cost trend for visualization via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.DailyCostTrendRequest(days=days)
        if start_date:
            request.start_date = start_date
        if end_date:
            request.end_date = end_date

        try:
            response = await self.stub.GetDailyCostTrend(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetDailyCostTrend",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_current_day_cost(self) -> dict[str, Any]:
        """Get real-time today's running cost total via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.CurrentDayCostRequest()
        try:
            response = await self.stub.GetCurrentDayCost(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetCurrentDayCost",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_llm_cost_by_agent_type(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get LLM cost breakdown by agent type via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.LlmCostByAgentTypeRequest()
        if start_date:
            request.start_date = start_date
        if end_date:
            request.end_date = end_date

        try:
            response = await self.stub.GetLlmCostByAgentType(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetLlmCostByAgentType",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_llm_cost_by_model(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get LLM cost breakdown by model via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.LlmCostByModelRequest()
        if start_date:
            request.start_date = start_date
        if end_date:
            request.end_date = end_date

        try:
            response = await self.stub.GetLlmCostByModel(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetLlmCostByModel",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_document_cost_summary(
        self,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """Get document processing cost summary via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.DocumentCostSummaryRequest(
            start_date=start_date,
            end_date=end_date,
        )
        try:
            response = await self.stub.GetDocumentCostSummary(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetDocumentCostSummary",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_embedding_cost_by_domain(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get embedding cost breakdown by domain via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.EmbeddingCostByDomainRequest()
        if start_date:
            request.start_date = start_date
        if end_date:
            request.end_date = end_date

        try:
            response = await self.stub.GetEmbeddingCostByDomain(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetEmbeddingCostByDomain",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def get_budget_status(self) -> dict[str, Any]:
        """Get current budget thresholds and utilization via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.BudgetStatusRequest()
        try:
            response = await self.stub.GetBudgetStatus(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="GetBudgetStatus",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def configure_budget_threshold(
        self,
        daily_threshold_usd: str | None = None,
        monthly_threshold_usd: str | None = None,
    ) -> dict[str, Any]:
        """Configure budget thresholds (persisted to MongoDB) via gRPC."""
        from fp_proto.platform_cost.v1 import platform_cost_pb2

        request = platform_cost_pb2.ConfigureBudgetThresholdRequest()
        if daily_threshold_usd is not None:
            request.daily_threshold_usd = daily_threshold_usd
        if monthly_threshold_usd is not None:
            request.monthly_threshold_usd = monthly_threshold_usd

        try:
            response = await self.stub.ConfigureBudgetThreshold(request)
            return MessageToDict(response, preserving_proto_field_name=True)
        except grpc.RpcError as e:
            raise PlatformCostServiceError(
                operation="ConfigureBudgetThreshold",
                code=e.code(),
                details=e.details() or str(e),
            ) from e

    async def check_connectivity(self) -> bool:
        """Check if gRPC service is reachable."""
        try:
            await self.get_current_day_cost()
            return True
        except grpc.RpcError:
            # Any response (even error) means the service is reachable
            return True
        except Exception:
            return False
