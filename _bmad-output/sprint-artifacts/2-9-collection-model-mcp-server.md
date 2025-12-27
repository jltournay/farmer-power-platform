# Story 2.9: Collection Model MCP Server

**Status:** ready-for-dev
**Epic:** 2 - Quality Data Ingestion
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->
**Created:** 2025-12-27

---

## Story

As an **AI agent**,
I want to query collected documents via generic MCP tools,
So that I can access any source's data using consistent, config-driven queries.

---

## Context

This story implements the **Collection Model MCP Server** - a stateless gRPC service that exposes the unified `documents` collection to AI agents via MCP tools.

**Design Principle:** All tools work with the **generic `documents` collection**. No source-specific tools. New sources require only configuration - the same tools work for QC data, weather, market prices, or any future source.

**Already Implemented (reuse from prior stories):**
- `DocumentRepository` - Generic document storage (`services/collection-model/src/collection_model/infrastructure/document_repository.py`)
- `SourceConfigService` - Source configuration loading (`services/collection-model/src/collection_model/services/source_config_service.py`)
- Proto definitions for MCP (`libs/fp-proto/fp_proto/mcp/v1/mcp_tool.proto`)
- MCP gRPC service pattern from plantation-mcp (`mcp-servers/plantation-mcp/`)

---

## Acceptance Criteria

### AC1: get_documents - Query with Filters

**Given** the Collection MCP Server is deployed
**When** an AI agent calls `get_documents(source_id="qc-analyzer-result", farmer_id="WM-4521", date_range={start, end}, limit=50)`
**Then** matching documents are returned from the generic `documents` collection
**And** each document includes: document_id, source_id, farmer_id, linkage, attributes, files, ingested_at
**And** results are sorted by ingested_at descending

### AC2: get_documents - Attribute Filtering

**Given** quality documents exist with varying primary_percentage
**When** an AI agent calls `get_documents(source_id="qc-analyzer-result", attributes={"bag_summary.primary_percentage": {"$lt": 70}})`
**Then** only documents matching the attribute filter are returned
**And** this enables queries like "poor quality events" without hardcoded tools

### AC3: get_documents - Linkage Filtering

**Given** documents exist with linkage fields (batch_id, plantation_id, factory_id)
**When** an AI agent calls `get_documents(linkage={"batch_id": "batch-2025-12-26-001"})`
**Then** all documents linked to that batch are returned across any source_id

### AC4: get_document_by_id - Single Document with Files

**Given** a document_id exists
**When** an AI agent calls `get_document_by_id(document_id="qc-analyzer-exceptions/batch-001/leaf_001", include_files=true)`
**Then** the full document is returned with all attributes and payload
**And** files[] array includes blob_uri with fresh SAS tokens (1 hour validity)
**And** file roles are preserved (image, metadata, primary, thumbnail)

### AC5: get_farmer_documents - Cross-Source Farmer Query

**Given** a farmer has documents from multiple sources
**When** an AI agent calls `get_farmer_documents(farmer_id="WM-4521", source_ids=["qc-analyzer-result", "qc-analyzer-exceptions"], date_range={last_30_days})`
**Then** all matching documents across specified sources are returned
**And** this replaces the need for source-specific farmer tools

### AC6: search_documents - Full-Text Search

**Given** documents have searchable content in attributes
**When** an AI agent calls `search_documents(query="coarse leaf", source_ids=["qc-analyzer-exceptions"], limit=20)`
**Then** documents matching the search query are returned
**And** results include relevance scoring

### AC7: list_sources - Source Registry

**Given** source configurations are deployed
**When** an AI agent calls `list_sources(enabled_only=true)`
**Then** all enabled source configurations are returned
**And** each includes: source_id, display_name, ingestion.mode, description

### AC8: Weather and Market Data via Generic Tools

**Given** weather-api and market-prices sources are configured
**When** an AI agent calls `get_documents(source_id="weather-api", linkage={"region_id": "nyeri"}, date_range={last_7_days})`
**Then** weather documents for that region are returned
**And** the same pattern works for `get_documents(source_id="market-prices", ...)`
**And** no source-specific tools are needed

### AC9: Error Handling

**Given** an invalid source_id is provided
**When** an AI agent calls `get_documents(source_id="nonexistent")`
**Then** an empty result set is returned (not an error)
**And** the response includes metadata indicating 0 matches

**Given** an invalid document_id is provided
**When** an AI agent calls `get_document_by_id(document_id="nonexistent")`
**Then** a NOT_FOUND error is returned with appropriate error code

---

## Tasks / Subtasks

### Task 1: Create Collection MCP Server Scaffold (AC: all)

- [ ] Create `mcp-servers/collection-mcp/` directory structure
  - [ ] `src/collection_mcp/__init__.py`
  - [ ] `src/collection_mcp/main.py` - gRPC server entrypoint
  - [ ] `src/collection_mcp/config.py` - Service configuration
  - [ ] `pyproject.toml` with dependencies (fp-proto, fp-common, motor, azure-storage-blob)
  - [ ] `Dockerfile` for container build
- [ ] Follow plantation-mcp structure: `api/`, `tools/`, `infrastructure/`

### Task 2: Create Tool Definitions Registry (AC: 1, 2, 3, 4, 5, 6, 7)

- [ ] Create `mcp-servers/collection-mcp/src/collection_mcp/tools/definitions.py`
  - [ ] `get_documents` tool definition with full input schema:
    - `source_id: string | null` - Filter by source
    - `farmer_id: string | null` - Filter by farmer
    - `linkage: object | null` - Filter by linkage fields
    - `attributes: object | null` - MongoDB-style attribute filters (supports $lt, $gt, $eq)
    - `date_range: {start: string, end: string} | null` - ISO date range
    - `limit: integer = 50` - Max results (default 50, max 1000)
  - [ ] `get_document_by_id` tool definition:
    - `document_id: string` (required)
    - `include_files: boolean = false` - Include file URIs with SAS tokens
  - [ ] `get_farmer_documents` tool definition:
    - `farmer_id: string` (required)
    - `source_ids: string[] | null` - Filter by sources
    - `date_range: {start: string, end: string} | null`
  - [ ] `search_documents` tool definition:
    - `query: string` (required) - Full-text search query
    - `source_ids: string[] | null` - Filter by sources
    - `farmer_id: string | null` - Filter by farmer
    - `limit: integer = 20` - Max results
  - [ ] `list_sources` tool definition:
    - `enabled_only: boolean = true` - Only show enabled sources
  - [ ] `TOOL_REGISTRY: dict[str, ToolDefinition]`
  - [ ] `list_tools(category)` helper function

### Task 3: Create Document Client Infrastructure (AC: 1, 2, 3, 4, 5, 6)

- [ ] Create `mcp-servers/collection-mcp/src/collection_mcp/infrastructure/document_client.py`
  - [ ] `DocumentClient` class with async Motor (MongoDB) operations
  - [ ] `__init__(mongodb_uri, database_name)` - Initialize Motor async client
  - [ ] `get_documents(filters) -> list[dict]` - Query with filters
    - Build MongoDB query from source_id, farmer_id, linkage, attributes, date_range
    - Support dot notation for nested attribute filtering (e.g., `bag_summary.primary_percentage`)
    - Support MongoDB operators ($lt, $gt, $eq, $in) for attribute values
  - [ ] `get_document_by_id(document_id) -> dict | None` - Single document lookup
  - [ ] `get_farmer_documents(farmer_id, source_ids, date_range) -> list[dict]` - Cross-source query
  - [ ] `search_documents(query, source_ids, farmer_id, limit) -> list[dict]` - Text search
    - Use MongoDB text index if available, fallback to regex
  - [ ] Error handling: `DocumentNotFoundError`, `DocumentClientError`

### Task 4: Create Blob URL Generator (AC: 4)

- [ ] Create `mcp-servers/collection-mcp/src/collection_mcp/infrastructure/blob_url_generator.py`
  - [ ] `BlobUrlGenerator` class
  - [ ] `__init__(connection_string)` - Initialize Azure Blob Storage client
  - [ ] `generate_sas_url(blob_uri, validity_hours=1) -> str` - Generate SAS token URL
    - Parse blob_uri to extract container and blob name
    - Generate user delegation SAS with 1 hour validity
    - Return full URL with SAS token
  - [ ] `enrich_files_with_sas(files: list[dict]) -> list[dict]` - Add SAS URLs to files array

### Task 5: Create Source Config Client (AC: 7)

- [ ] Create `mcp-servers/collection-mcp/src/collection_mcp/infrastructure/source_config_client.py`
  - [ ] `SourceConfigClient` class
  - [ ] `__init__(dapr_app_id)` - DAPR Service Invocation to collection-model
  - [ ] `list_sources(enabled_only) -> list[dict]` - Get source configurations
    - Call collection-model service via DAPR
    - Return source_id, display_name, ingestion.mode, description
  - [ ] Alternative: direct MongoDB read from `source_configs` collection (simpler, read-only)

### Task 6: Create MCP Tool Service (AC: all)

- [ ] Create `mcp-servers/collection-mcp/src/collection_mcp/api/mcp_service.py`
  - [ ] `McpToolServiceServicer(mcp_tool_pb2_grpc.McpToolServiceServicer)`
  - [ ] `__init__(document_client, blob_url_generator, source_config_client)`
  - [ ] `ListTools(request, context)` - Return tool definitions
  - [ ] `CallTool(request, context)` - Route to handlers
  - [ ] Tool handlers:
    - [ ] `_handle_get_documents(arguments)` - Build query, call DocumentClient
    - [ ] `_handle_get_document_by_id(arguments)` - Lookup, optionally enrich files with SAS
    - [ ] `_handle_get_farmer_documents(arguments)` - Cross-source farmer query
    - [ ] `_handle_search_documents(arguments)` - Full-text search
    - [ ] `_handle_list_sources(arguments)` - Return source configs
  - [ ] Follow plantation-mcp patterns for error handling, logging, tracing

### Task 7: Create gRPC Server Main (AC: all)

- [ ] Modify/create `mcp-servers/collection-mcp/src/collection_mcp/main.py`
  - [ ] Initialize Motor async client for MongoDB
  - [ ] Initialize BlobUrlGenerator with Azure connection string
  - [ ] Initialize SourceConfigClient
  - [ ] Initialize DocumentClient
  - [ ] Create McpToolServiceServicer with dependencies
  - [ ] Start gRPC server with reflection enabled
  - [ ] Graceful shutdown handling

### Task 8: Update CI Configuration

- [ ] Update `.github/workflows/ci.yaml`
  - [ ] Add `mcp-servers/collection-mcp/src` to PYTHONPATH
  - [ ] Include collection-mcp in test discovery

### Task 9: Create Unit Tests (AC: all)

- [ ] Create `mcp-servers/collection-mcp/tests/` directory
  - [ ] `conftest.py` - Test fixtures (mock MongoDB, mock Blob client)
  - [ ] `test_document_client.py` - DocumentClient query building tests
  - [ ] `test_blob_url_generator.py` - SAS URL generation tests
  - [ ] `test_mcp_service.py` - Tool handler tests
  - [ ] `test_tool_definitions.py` - Schema validation tests
- [ ] Test scenarios:
  - [ ] Query by source_id only
  - [ ] Query by farmer_id only
  - [ ] Query with attribute filters ($lt, $gt)
  - [ ] Query with linkage filters
  - [ ] Query with date_range
  - [ ] Combined filters
  - [ ] Document not found returns NOT_FOUND error
  - [ ] Empty result set returns success with 0 items
  - [ ] SAS URL generation with correct expiry
  - [ ] list_sources returns configured sources

### Task 10: Create Kubernetes Deployment

- [ ] Create `deploy/kubernetes/base/mcp-servers/collection-mcp/`
  - [ ] `deployment.yaml` - Stateless deployment, HPA min 2, max 10
  - [ ] `service.yaml` - gRPC service on port 50051
  - [ ] `kustomization.yaml` - Include in base kustomize

---

## Dev Notes

### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COLLECTION MCP SERVER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  AI Agent (via DAPR Service Invocation)                                  │
│       │                                                                  │
│       ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    MCP gRPC Service                                 │ │
│  │                                                                     │ │
│  │  ListTools() ─────▶ TOOL_REGISTRY                                  │ │
│  │                                                                     │ │
│  │  CallTool(tool_name, args) ────┬──▶ _handle_get_documents()        │ │
│  │                                ├──▶ _handle_get_document_by_id()   │ │
│  │                                ├──▶ _handle_get_farmer_documents() │ │
│  │                                ├──▶ _handle_search_documents()     │ │
│  │                                └──▶ _handle_list_sources()         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                          │                                               │
│                          ▼                                               │
│         ┌────────────────────────────────────────────┐                  │
│         │           INFRASTRUCTURE                    │                  │
│         ├────────────────────────────────────────────┤                  │
│         │ DocumentClient    │ MongoDB (documents)    │                  │
│         │ BlobUrlGenerator  │ Azure Blob (SAS gen)   │                  │
│         │ SourceConfigClient│ MongoDB (source_configs)│                  │
│         └────────────────────────────────────────────┘                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### MongoDB Query Building

The `get_documents` tool supports flexible MongoDB-style filtering:

```python
# Example: Build query from tool arguments
def _build_query(self, args: dict) -> dict:
    query = {}

    if args.get("source_id"):
        query["source_id"] = args["source_id"]

    if args.get("farmer_id"):
        query["farmer_id"] = args["farmer_id"]

    if args.get("linkage"):
        for key, value in args["linkage"].items():
            query[f"linkage.{key}"] = value

    if args.get("attributes"):
        for key, value in args["attributes"].items():
            if isinstance(value, dict):
                # MongoDB operators: {"$lt": 70}
                query[f"attributes.{key}"] = value
            else:
                # Direct equality
                query[f"attributes.{key}"] = value

    if args.get("date_range"):
        query["ingested_at"] = {
            "$gte": args["date_range"]["start"],
            "$lte": args["date_range"]["end"]
        }

    return query
```

### SAS URL Generation Pattern

```python
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

async def generate_sas_url(self, blob_uri: str, validity_hours: int = 1) -> str:
    # Parse: https://storage.blob.core.windows.net/container/path/to/blob
    # Or: wasbs://container@storage.blob.core.windows.net/path

    sas_token = generate_blob_sas(
        account_name=self._account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=self._account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=validity_hours),
    )
    return f"https://{self._account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"
```

### Existing Code to Reuse

| Component | Source | Usage |
|-----------|--------|-------|
| gRPC service pattern | `mcp-servers/plantation-mcp/src/plantation_mcp/api/mcp_service.py` | Copy structure |
| Tool definitions pattern | `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py` | Copy pattern |
| Proto definitions | `libs/fp-proto/fp_proto/mcp/v1/mcp_tool.proto` | Import directly |
| Motor async pattern | Already in project dependencies | Use for async MongoDB |

### MCP Server Rules (from project-context.md)

- MCP servers are **STATELESS** - no in-memory caching
- Each domain model exposes **ONE** MCP server
- Tools **return data, NOT make decisions**
- Use Pydantic models for tool input/output schemas
- Tool names: `get_*`, `search_*`, `list_*` (verbs for read operations)

### Project Structure Notes

New MCP server follows existing patterns:
```
mcp-servers/collection-mcp/
├── src/collection_mcp/
│   ├── __init__.py
│   ├── main.py              # gRPC server entrypoint
│   ├── config.py            # Service configuration
│   ├── api/
│   │   └── mcp_service.py   # McpToolServiceServicer
│   ├── tools/
│   │   └── definitions.py   # TOOL_REGISTRY
│   └── infrastructure/
│       ├── document_client.py    # MongoDB async client
│       ├── blob_url_generator.py # Azure SAS generation
│       └── source_config_client.py # Source config access
├── tests/
│   ├── conftest.py
│   ├── test_document_client.py
│   ├── test_blob_url_generator.py
│   └── test_mcp_service.py
├── Dockerfile
└── pyproject.toml
```

### Previous Story Learnings (from 2-7)

1. **Async patterns:** Use `async/await` consistently. Motor provides async MongoDB.
2. **Error handling:** Return appropriate MCP error codes (NOT_FOUND, INVALID_ARGUMENTS, etc.)
3. **Logging:** Use `structlog` with context (tool_name, caller_agent_id, etc.)
4. **Tracing:** Use OpenTelemetry spans for each tool call
5. **Testing:** Mock external dependencies (MongoDB, Azure Blob) in unit tests
6. **CI:** Update PYTHONPATH in `.github/workflows/ci.yaml` for new service

### Testing Strategy

| Test | Type | Location |
|------|------|----------|
| DocumentClient query building | Unit | `tests/test_document_client.py` |
| BlobUrlGenerator SAS gen | Unit | `tests/test_blob_url_generator.py` |
| MCP service tool handlers | Unit | `tests/test_mcp_service.py` |
| Tool schema validation | Unit | `tests/test_tool_definitions.py` |
| End-to-end MCP calls | Integration | `tests/integration/test_collection_mcp.py` |

---

### References

- [Source: `_bmad-output/architecture/collection-model-architecture.md` - MCP Server Tools section]
- [Source: `_bmad-output/epics.md` - Story 2.9 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` - MCP Server Rules]
- [Source: `mcp-servers/plantation-mcp/` - Existing MCP server pattern]
- [Source: `libs/fp-proto/fp_proto/mcp/v1/mcp_tool.proto` - Proto definitions]

---

## Definition of Done

- [ ] Collection MCP Server scaffold created with correct structure
- [ ] Tool definitions for all 5 tools with full schemas
- [ ] DocumentClient queries documents with filters (source, farmer, linkage, attributes, date_range)
- [ ] BlobUrlGenerator creates SAS URLs with 1 hour validity
- [ ] MCP service handles all tool calls with proper error codes
- [ ] list_sources returns configured sources
- [ ] Unit tests for all components
- [ ] CI configuration updated for collection-mcp
- [ ] Kubernetes deployment manifests created
- [ ] CI passes (ruff check, ruff format, tests)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

_Created: 2025-12-27_
