"""MCP Tool definitions and registry."""

from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    category: str


# Tool registry - all available tools
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_farmer": ToolDefinition(
        name="get_farmer",
        description=(
            "Get farmer details by ID. Returns name, phone, farm size, region, "
            "collection point, and communication preferences."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "Farmer ID (e.g., WM-0001)",
                }
            },
            "required": ["farmer_id"],
        },
        category="query",
    ),
    "get_farmer_summary": ToolDefinition(
        name="get_farmer_summary",
        description=(
            "Get farmer performance summary including quality history, trends, "
            "yield metrics, and last delivery date."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "Farmer ID (e.g., WM-0001)",
                }
            },
            "required": ["farmer_id"],
        },
        category="query",
    ),
    "get_collection_points": ToolDefinition(
        name="get_collection_points",
        description="Get all collection points for a factory with their details.",
        input_schema={
            "type": "object",
            "properties": {
                "factory_id": {
                    "type": "string",
                    "description": "Factory ID",
                }
            },
            "required": ["factory_id"],
        },
        category="query",
    ),
    "get_farmers_by_collection_point": ToolDefinition(
        name="get_farmers_by_collection_point",
        description="Get all farmers registered at a collection point.",
        input_schema={
            "type": "object",
            "properties": {
                "collection_point_id": {
                    "type": "string",
                    "description": "Collection point ID",
                }
            },
            "required": ["collection_point_id"],
        },
        category="query",
    ),
}


def get_tool(name: str) -> ToolDefinition | None:
    """Get a tool definition by name."""
    return TOOL_REGISTRY.get(name)


def list_tools(category: str | None = None) -> list[ToolDefinition]:
    """List all tools, optionally filtered by category."""
    tools = list(TOOL_REGISTRY.values())
    if category:
        tools = [t for t in tools if t.category == category]
    return tools
