"""MCP Tool definitions and registry for Collection Model."""

from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    category: str


# Tool registry - all available tools for Collection Model MCP Server
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_documents": ToolDefinition(
        name="get_documents",
        description=(
            "Query documents from the collection model with flexible filters. "
            "Supports filtering by source_id, farmer_id, linkage fields, attribute values "
            "(with MongoDB operators like $lt, $gt), and date ranges. "
            "Returns documents sorted by ingested_at descending."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": (
                        "Filter by source ID (e.g., 'qc-analyzer-result', 'weather-api', 'market-prices'). "
                        "Optional - omit to query across all sources."
                    ),
                },
                "farmer_id": {
                    "type": "string",
                    "description": "Filter by farmer ID (e.g., 'WM-4521'). Optional.",
                },
                "linkage": {
                    "type": "object",
                    "description": (
                        "Filter by linkage fields. Keys are linkage field names "
                        "(e.g., 'batch_id', 'collection_point_id', 'factory_id', 'region_id'), "
                        "values are the expected values."
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "attributes": {
                    "type": "object",
                    "description": (
                        "Filter by document attributes using dot notation for nested fields. "
                        "Values can be direct equality matches or MongoDB-style operators. "
                        "Examples: {'bag_summary.primary_percentage': {'$lt': 70}}, "
                        "{'grade': 'A'}, {'temperature': {'$gt': 25, '$lt': 35}}"
                    ),
                    "additionalProperties": True,
                },
                "date_range": {
                    "type": "object",
                    "description": "Filter by ingestion date range.",
                    "properties": {
                        "start": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Start of date range (ISO 8601 format)",
                        },
                        "end": {
                            "type": "string",
                            "format": "date-time",
                            "description": "End of date range (ISO 8601 format)",
                        },
                    },
                    "required": ["start", "end"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default 50, max 1000.",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": [],
        },
        category="query",
    ),
    "get_document_by_id": ToolDefinition(
        name="get_document_by_id",
        description=(
            "Get a single document by its document_id. Returns the full document including "
            "all attributes, payload, and optionally file URIs with fresh SAS tokens for blob access."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": (
                        "The document ID (e.g., 'qc-analyzer-exceptions/batch-001/leaf_001'). "
                        "This is the unique identifier for the document in the collection."
                    ),
                },
                "include_files": {
                    "type": "boolean",
                    "description": (
                        "If true, include file URIs with fresh SAS tokens (1 hour validity) "
                        "for direct blob access. Default false."
                    ),
                    "default": False,
                },
            },
            "required": ["document_id"],
        },
        category="query",
    ),
    "get_farmer_documents": ToolDefinition(
        name="get_farmer_documents",
        description=(
            "Get all documents for a specific farmer, optionally filtered by source types and date range. "
            "This is a convenience tool for cross-source farmer queries."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "The farmer ID (e.g., 'WM-4521').",
                },
                "source_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of source IDs to filter by (e.g., ['qc-analyzer-result', 'qc-analyzer-exceptions']). "
                        "Optional - omit to query across all sources."
                    ),
                },
                "date_range": {
                    "type": "object",
                    "description": "Filter by ingestion date range.",
                    "properties": {
                        "start": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Start of date range (ISO 8601 format)",
                        },
                        "end": {
                            "type": "string",
                            "format": "date-time",
                            "description": "End of date range (ISO 8601 format)",
                        },
                    },
                    "required": ["start", "end"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default 100, max 1000.",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": ["farmer_id"],
        },
        category="query",
    ),
    "search_documents": ToolDefinition(
        name="search_documents",
        description=(
            "Full-text search across document content and attributes. "
            "Returns documents matching the search query with relevance scoring."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query (e.g., 'coarse leaf', 'moisture damage'). "
                        "Searches across searchable document fields."
                    ),
                },
                "source_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": ("List of source IDs to search within. Optional - omit to search all sources."),
                },
                "farmer_id": {
                    "type": "string",
                    "description": "Filter search results by farmer ID. Optional.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default 20, max 100.",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["query"],
        },
        category="search",
    ),
    "list_sources": ToolDefinition(
        name="list_sources",
        description=(
            "List all configured data sources in the collection model. "
            "Returns source metadata including source_id, display name, ingestion mode, and description."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "enabled_only": {
                    "type": "boolean",
                    "description": "If true, only return enabled sources. Default true.",
                    "default": True,
                },
            },
            "required": [],
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
