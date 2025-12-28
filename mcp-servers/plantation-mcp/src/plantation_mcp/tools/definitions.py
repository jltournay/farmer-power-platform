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
    "get_factory": ToolDefinition(
        name="get_factory",
        description=(
            "Get factory details by ID. Returns name, code, region, location, "
            "processing capacity, and quality thresholds (tier_1, tier_2, tier_3)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "factory_id": {
                    "type": "string",
                    "description": "Factory ID (e.g., KEN-FAC-001)",
                },
            },
            "required": ["factory_id"],
        },
        category="query",
    ),
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
                },
            },
            "required": ["farmer_id"],
        },
        category="query",
    ),
    "get_farmer_summary": ToolDefinition(
        name="get_farmer_summary",
        description=(
            "Get farmer performance summary including quality history, trends, yield metrics, and last delivery date."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "Farmer ID (e.g., WM-0001)",
                },
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
                },
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
                },
            },
            "required": ["collection_point_id"],
        },
        category="query",
    ),
    # Region tools (Story 1.8)
    "get_region": ToolDefinition(
        name="get_region",
        description=(
            "Get region details by ID. Returns name, county, country, geography "
            "(center GPS, radius, altitude band), flush calendar, agronomic factors, "
            "and weather configuration."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "region_id": {
                    "type": "string",
                    "description": "Region ID in format {county}-{altitude_band} (e.g., nyeri-highland)",
                },
            },
            "required": ["region_id"],
        },
        category="query",
    ),
    "list_regions": ToolDefinition(
        name="list_regions",
        description=(
            "List regions with optional filtering by county or altitude band. "
            "Returns active regions by default."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "county": {
                    "type": "string",
                    "description": "Filter by county name (e.g., Nyeri, Kericho)",
                },
                "altitude_band": {
                    "type": "string",
                    "enum": ["highland", "midland", "lowland"],
                    "description": "Filter by altitude band",
                },
            },
            "required": [],
        },
        category="query",
    ),
    "get_current_flush": ToolDefinition(
        name="get_current_flush",
        description=(
            "Get the current flush period for a region based on today's date. "
            "Returns flush name (first_flush, monsoon_flush, autumn_flush, dormant), "
            "start/end dates, characteristics, and days remaining."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "region_id": {
                    "type": "string",
                    "description": "Region ID (e.g., nyeri-highland)",
                },
            },
            "required": ["region_id"],
        },
        category="query",
    ),
    "get_region_weather": ToolDefinition(
        name="get_region_weather",
        description=(
            "Get recent weather observations for a region. Returns temperature "
            "(min/max), precipitation, and humidity data."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "region_id": {
                    "type": "string",
                    "description": "Region ID (e.g., nyeri-highland)",
                },
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "default": 7,
                    "description": "Number of days of history (default: 7, max: 30)",
                },
            },
            "required": ["region_id"],
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
