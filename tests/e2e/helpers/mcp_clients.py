"""gRPC MCP clients for E2E testing."""

from typing import Any

import grpc

# Import generated protobuf stubs
# Note: These imports assume fp-proto is in the PYTHONPATH
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
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
        import json

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
        import json

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
