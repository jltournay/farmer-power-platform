# ADR-019: Admin Configuration Visibility (Read-Only gRPC APIs)

**Status:** Accepted
**Date:** 2026-01-20
**Deciders:** Winston (Architect), John (PM), Sally (UX), Amelia (Dev), Jeanlouistournay
**Related Stories:** Story 9.11a, 9.11b, 9.11c, 9.12a, 9.12b, 9.12c (to be created)

## Context

The platform has three configuration CLIs that manage critical system configurations:

| CLI | Manages | MongoDB Collection | Write Operations |
|-----|---------|-------------------|------------------|
| `source-config` | Data source ingestion configs | `source_configs` | Create, Update, Deploy |
| `agent-config` | AI agent configurations | `agent_configs` | Create, Update, Deploy |
| `prompt-config` | LLM prompt templates | `prompts` | Create, Update, Deploy |

**Current State:**
- CLIs talk directly to MongoDB for all operations
- No gRPC endpoints exist for these configurations
- Admin users cannot view configurations without CLI access or direct MongoDB queries

**Problem:**
Platform administrators and CP managers need visibility into:
1. **Source Configurations** - What data sources are enabled? What ingestion settings are active?
2. **AI Agents** - Which agents are deployed? What are their configurations?
3. **Prompts** - What prompts are linked to which agents? What versions are active?

This visibility supports:
- **Auditability** - Verify what's configured without database diving
- **Debugging** - When something behaves unexpectedly, check actual config
- **Trust** - View-only access means no accidental changes, but full visibility

**Key Insight:** Prompts have a foreign key relationship to Agents (`prompt.agent_id` → `agent.agent_id`). These should be viewed together, not as separate screens.

---

## Decision 1: Add Read-Only gRPC Services

### Problem

The Admin UI needs to display configuration data, but no gRPC endpoints exist. Two options:

| Option | Pros | Cons |
|--------|------|------|
| **A: BFF queries MongoDB directly** | Fast to implement | Breaks service boundaries, duplicates access patterns |
| **B: Add gRPC endpoints to services** | Clean architecture, reusable | More work upfront |

### Decision

**Add read-only gRPC services to Collection Model and AI Model services.**

This maintains the established architecture:
```
┌─────────────────┐     ┌─────────────────┐
│  Admin UI (FE)  │     │  Admin UI (FE)  │
└────────┬────────┘     └────────┬────────┘
         │ REST                  │ REST
         ▼                       ▼
┌─────────────────────────────────────────┐
│            Admin BFF                     │
│  - SourceConfigClient (gRPC)            │
│  - AgentConfigClient (gRPC)             │
│  - REST endpoints for frontend          │
└────────┬────────────────────┬───────────┘
         │ gRPC                │ gRPC
         ▼                     ▼
┌─────────────────┐     ┌─────────────────┐
│ Collection Model│     │    AI Model     │
│ SourceConfigSvc │     │ AgentConfigSvc  │
└─────────────────┘     └─────────────────┘
```

### Why Read-Only?

| Operation | Tool | Rationale |
|-----------|------|-----------|
| **Create/Update/Delete** | CLI tools | Complex validation, version management, deployment workflows |
| **Read/List** | gRPC + Admin UI | Simple queries, no business logic needed |

CLIs remain the authoritative write path. The Admin UI is purely for visibility.

---

## Decision 2: SourceConfigService in Collection Model

### gRPC Service Definition

Add to `proto/collection/v1/collection.proto`:

```protobuf
// ============================================================================
// Source Config Service - Read-only admin visibility (ADR-019)
// Write operations handled by source-config CLI
// ============================================================================

service SourceConfigService {
  // List all source configurations with optional filters
  rpc ListSourceConfigs(ListSourceConfigsRequest) returns (ListSourceConfigsResponse);

  // Get a single source configuration by ID
  rpc GetSourceConfig(GetSourceConfigRequest) returns (SourceConfigResponse);
}

message ListSourceConfigsRequest {
  int32 page_size = 1;         // Max 100, default 20
  string page_token = 2;       // Pagination cursor
  bool enabled_only = 3;       // Filter to enabled configs only
  string ingestion_mode = 4;   // Filter: "blob_trigger" or "scheduled_pull"
}

message ListSourceConfigsResponse {
  repeated SourceConfigSummary configs = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}

message GetSourceConfigRequest {
  string source_id = 1;
}

message SourceConfigSummary {
  string source_id = 1;
  string display_name = 2;
  string description = 3;
  bool enabled = 4;
  string ingestion_mode = 5;      // "blob_trigger" or "scheduled_pull"
  string ai_agent_id = 6;         // Linked AI agent (nullable)
  google.protobuf.Timestamp updated_at = 7;
}

message SourceConfigResponse {
  string source_id = 1;
  string display_name = 2;
  string description = 3;
  bool enabled = 4;

  // Full config as JSON for detail view
  // Using JSON string to avoid duplicating complex nested proto definitions
  string config_json = 5;

  google.protobuf.Timestamp created_at = 6;
  google.protobuf.Timestamp updated_at = 7;
}
```

### Implementation Notes

- **List returns summaries** - Key fields for table display
- **Get returns full config as JSON** - Avoids duplicating complex Pydantic models in proto
- **No write methods** - CLIs handle mutations

---

## Decision 3: AgentConfigService in AI Model (with Prompts)

### gRPC Service Definition

Add to `proto/ai_model/v1/ai_model.proto`:

```protobuf
// ============================================================================
// Agent Config Service - Read-only admin visibility (ADR-019)
// Write operations handled by agent-config and prompt-config CLIs
// ============================================================================

service AgentConfigService {
  // List all agent configurations with optional filters
  rpc ListAgentConfigs(ListAgentConfigsRequest) returns (ListAgentConfigsResponse);

  // Get a single agent configuration with its linked prompts
  rpc GetAgentConfig(GetAgentConfigRequest) returns (AgentConfigResponse);

  // List prompts for a specific agent
  rpc ListPromptsByAgent(ListPromptsByAgentRequest) returns (ListPromptsResponse);
}

message ListAgentConfigsRequest {
  int32 page_size = 1;         // Max 100, default 20
  string page_token = 2;       // Pagination cursor
  string agent_type = 3;       // Filter: "extractor", "explorer", "generator", etc.
  string status = 4;           // Filter: "draft", "staged", "active", "archived"
}

message ListAgentConfigsResponse {
  repeated AgentConfigSummary agents = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}

message GetAgentConfigRequest {
  string agent_id = 1;
  string version = 2;          // Optional: specific version (empty = active)
}

message AgentConfigSummary {
  string agent_id = 1;
  string version = 2;
  string agent_type = 3;       // "extractor", "explorer", "generator", "conversational", "tiered-vision"
  string status = 4;           // "draft", "staged", "active", "archived"
  string description = 5;
  string model = 6;            // LLM model identifier
  int32 prompt_count = 7;      // Number of linked prompts
  google.protobuf.Timestamp updated_at = 8;
}

message AgentConfigResponse {
  string agent_id = 1;
  string version = 2;
  string agent_type = 3;
  string status = 4;
  string description = 5;

  // Full config as JSON for detail view
  string config_json = 6;

  // Linked prompts (denormalized for single call)
  repeated PromptSummary prompts = 7;

  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp updated_at = 9;
}

// Prompt messages
message ListPromptsByAgentRequest {
  string agent_id = 1;
  string status = 2;           // Filter: "draft", "staged", "active", "archived"
}

message ListPromptsResponse {
  repeated PromptSummary prompts = 1;
  int32 total_count = 2;
}

message PromptSummary {
  string id = 1;               // Format: {prompt_id}:{version}
  string prompt_id = 2;
  string agent_id = 3;
  string version = 4;
  string status = 5;           // "draft", "staged", "active", "archived"
  string author = 6;
  google.protobuf.Timestamp updated_at = 7;
}

message PromptResponse {
  string id = 1;
  string prompt_id = 2;
  string agent_id = 3;
  string version = 4;
  string status = 5;

  // Full prompt content
  string system_prompt = 6;
  string template = 7;
  string output_schema_json = 8;   // JSON schema as string
  string few_shot_examples_json = 9;

  // Metadata
  string author = 10;
  string changelog = 11;
  string git_commit = 12;

  // A/B test config
  bool ab_test_enabled = 13;
  float ab_test_traffic_percentage = 14;

  google.protobuf.Timestamp created_at = 15;
  google.protobuf.Timestamp updated_at = 16;
}
```

### Design Decisions

1. **Agent + Prompts together** - `GetAgentConfig` returns linked prompts in one call
2. **Prompt linked via agent_id** - Natural relationship already exists in data model
3. **Version history accessible** - Can query specific versions or list all versions
4. **Full content as JSON** - Complex nested structures returned as JSON strings

---

## Decision 4: BFF Layer Architecture

### BFF gRPC Clients

Following ADR-012 patterns:

```python
# services/bff/src/bff/infrastructure/clients/source_config_client.py
class SourceConfigClient(BaseGrpcClient):
    async def list_source_configs(
        self,
        page_size: int = 20,
        page_token: str | None = None,
        enabled_only: bool = False,
        ingestion_mode: str | None = None,
    ) -> PaginatedResponse[SourceConfigSummary]:
        ...

    async def get_source_config(self, source_id: str) -> SourceConfigDetail:
        ...


# services/bff/src/bff/infrastructure/clients/agent_config_client.py
class AgentConfigClient(BaseGrpcClient):
    async def list_agent_configs(
        self,
        page_size: int = 20,
        page_token: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[AgentConfigSummary]:
        ...

    async def get_agent_config(
        self,
        agent_id: str,
        version: str | None = None,
    ) -> AgentConfigDetail:
        """Returns agent config with linked prompts."""
        ...
```

### BFF REST API Endpoints

```python
# Admin Configuration Routes
# services/bff/src/bff/api/routes/admin_config_routes.py

@router.get("/admin/source-configs")
async def list_source_configs(
    page_size: int = Query(20, le=100),
    page_token: str | None = None,
    enabled_only: bool = False,
    ingestion_mode: str | None = None,
) -> SourceConfigListResponse:
    """List all source configurations."""
    ...

@router.get("/admin/source-configs/{source_id}")
async def get_source_config(source_id: str) -> SourceConfigDetailResponse:
    """Get source configuration details."""
    ...

@router.get("/admin/ai-agents")
async def list_ai_agents(
    page_size: int = Query(20, le=100),
    page_token: str | None = None,
    agent_type: str | None = None,
    status: str | None = None,
) -> AgentConfigListResponse:
    """List all AI agent configurations."""
    ...

@router.get("/admin/ai-agents/{agent_id}")
async def get_ai_agent(
    agent_id: str,
    version: str | None = None,
) -> AgentConfigDetailResponse:
    """Get AI agent details with linked prompts."""
    ...
```

---

## Decision 5: Admin UI Screen Design

### Screen 1: Source Configuration Viewer

**Route:** `/admin/source-configs`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔗 SOURCE CONFIGURATIONS                                    [Filter ▼]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  source_id          │ display_name       │ mode          │ enabled │ agent  │
│  ───────────────────┼────────────────────┼───────────────┼─────────┼─────── │
│  qc-analyzer-result │ QC Analyzer Result │ blob_trigger  │ ✅      │ qc-ext │
│  qc-analyzer-except │ QC Exceptions      │ blob_trigger  │ ✅      │ exc-ex │
│  weather-forecast   │ Weather Forecast   │ scheduled_pull│ ✅      │ -      │
│  market-prices      │ Market Prices      │ scheduled_pull│ ❌      │ -      │
│                                                                              │
│  Showing 4 of 4                                       [← Previous] [Next →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Detail Panel (slide-out on row click):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔗 SOURCE CONFIGURATION DETAIL                                    [✕ Close]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ SUMMARY ──────────────────────────────────────────────────────────────┐ │
│  │  Source ID:     qc-analyzer-result                                     │ │
│  │  Display Name:  QC Analyzer Result                                     │ │
│  │  Description:   Tea leaf quality analysis results from QC Analyzer     │ │
│  │  Status:        ✅ Enabled                                             │ │
│  │  Updated:       2026-01-15 14:32 UTC                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ INGESTION ────────────────────────────────────────────────────────────┐ │
│  │  Mode:              blob_trigger                                       │ │
│  │  Landing Container: qc-analyzer-landing                                │ │
│  │  File Pattern:      *.json                                             │ │
│  │  File Format:       json                                               │ │
│  │  Trigger:           event_grid                                         │ │
│  │  Processor Type:    json-extraction                                    │ │
│  │                                                                        │ │
│  │  Path Pattern:                                                         │ │
│  │    Pattern:         {region}/{factory}/{date}/{filename}               │ │
│  │    Extract Fields:  region, factory, date                              │ │
│  │                                                                        │ │
│  │  Processed File Config:                                                │ │
│  │    Action:          archive                                            │ │
│  │    Archive TTL:     90 days                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ VALIDATION ───────────────────────────────────────────────────────────┐ │
│  │  Schema Name:    data/qc-bag-result.json                               │ │
│  │  Schema Version: latest                                                │ │
│  │  Strict Mode:    ✅ Yes                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ TRANSFORMATION ───────────────────────────────────────────────────────┐ │
│  │  AI Agent ID:    qc-event-extractor                          [View →]  │ │
│  │  Link Field:     farmer_id                                             │ │
│  │  Extract Fields: farmer_id, grade, weight_kg, leaf_type, attributes    │ │
│  │                                                                        │ │
│  │  Field Mappings:                                                       │ │
│  │    bag_weight     → weight_kg                                          │ │
│  │    quality_grade  → grade                                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ STORAGE ──────────────────────────────────────────────────────────────┐ │
│  │  Raw Container:     raw-documents                                      │ │
│  │  Index Collection:  qc_results                                         │ │
│  │  TTL Days:          365                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ EVENTS ───────────────────────────────────────────────────────────────┐ │
│  │  On Success:                                                           │ │
│  │    Topic:         collection.quality_result.received                   │ │
│  │    Payload:       farmer_id, grade, weight_kg, collection_point_id     │ │
│  │                                                                        │ │
│  │  On Failure:                                                           │ │
│  │    Topic:         collection.ingestion.failed                          │ │
│  │    Payload:       source_id, error_message, document_id                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ RAW JSON ─────────────────────────────────────────────────────────────┐ │
│  │  [▼ Expand to view full configuration JSON]                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ⚠️ Read-only view. Use `source-config` CLI to modify.                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Wireframe: Scheduled Pull Source Config (alternative mode)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔗 SOURCE CONFIGURATION DETAIL                                    [✕ Close]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ SUMMARY ──────────────────────────────────────────────────────────────┐ │
│  │  Source ID:     weather-forecast                                       │ │
│  │  Display Name:  Weather Forecast                                       │ │
│  │  Description:   Daily weather data from Open-Meteo API                 │ │
│  │  Status:        ✅ Enabled                                             │ │
│  │  Updated:       2026-01-10 09:15 UTC                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ INGESTION (Scheduled Pull) ───────────────────────────────────────────┐ │
│  │  Mode:              scheduled_pull                                     │ │
│  │  Provider:          open-meteo                                         │ │
│  │  Schedule:          0 6 * * * (daily at 6:00 AM)                       │ │
│  │                                                                        │ │
│  │  Request Config:                                                       │ │
│  │    Base URL:        https://api.open-meteo.com/v1/forecast             │ │
│  │    Auth Type:       none                                               │ │
│  │    Timeout:         30s                                                │ │
│  │                                                                        │ │
│  │  Iteration Config:                                                     │ │
│  │    Foreach:         region                                             │ │
│  │    Source MCP:      plantation                                         │ │
│  │    Source Tool:     list_regions                                       │ │
│  │    Concurrency:     5                                                  │ │
│  │                                                                        │ │
│  │  Retry Config:                                                         │ │
│  │    Max Attempts:    3                                                  │ │
│  │    Backoff:         exponential                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ TRANSFORMATION ───────────────────────────────────────────────────────┐ │
│  │  AI Agent ID:    -                                                     │ │
│  │  Link Field:     region_id                                             │ │
│  │  Extract Fields: temperature_high, temperature_low, rainfall_mm, ...   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ... (Storage, Events, Raw JSON sections same as above)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Structured sections matching SourceConfig Pydantic model
- Conditional display based on ingestion mode (blob_trigger vs scheduled_pull)
- Link to AI Agent detail view when agent is configured
- Collapsible raw JSON for power users
- Clear read-only indicator with CLI reference

#### Implementation Notes for Story 9.11c (UI)

> **Added 2026-01-25** after Party Mode analysis of 9.11a implementation compatibility.

**1. JSON Parsing Responsibility**

The gRPC `GetSourceConfig` returns `config_json` as a **JSON string** (not structured proto fields). This is intentional to avoid duplicating the complex nested Pydantic model in proto definitions.

The **frontend must parse** `config_json` to render structured sections:

```typescript
// React component pattern
const configData = JSON.parse(sourceConfigDetail.config_json);
// Now access: configData.ingestion, configData.validation, etc.
```

**2. TypeScript Interfaces**

Create TypeScript interfaces that mirror the `SourceConfig` Pydantic model structure from `libs/fp-common/fp_common/models/source_config.py`:

```typescript
// frontend/src/types/source-config.ts
interface SourceConfig {
  source_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  ingestion: IngestionConfig;
  validation: ValidationConfig | null;
  transformation: TransformationConfig;
  storage: StorageConfig;
  events: EventsConfig | null;
}

interface IngestionConfig {
  mode: 'blob_trigger' | 'scheduled_pull';
  // blob_trigger fields
  landing_container?: string;
  path_pattern?: PathPatternConfig;
  file_pattern?: string;
  file_format?: 'json' | 'zip';
  trigger_mechanism?: 'event_grid';
  processed_file_config?: ProcessedFileConfig;
  processor_type?: string;
  // scheduled_pull fields
  provider?: string;
  schedule?: string;
  request?: RequestConfig;
  iteration?: IterationConfig;
  retry?: RetryConfig;
}
// ... (complete interfaces for all nested types)
```

**3. Conditional Rendering by Ingestion Mode**

The wireframe shows different fields for `blob_trigger` vs `scheduled_pull` modes:

```tsx
// React pattern
{configData.ingestion.mode === 'blob_trigger' ? (
  <BlobTriggerSection ingestion={configData.ingestion} />
) : (
  <ScheduledPullSection ingestion={configData.ingestion} />
)}
```

**4. Timestamp Field Handling**

The `SourceConfig` Pydantic model does **not include timestamps** (`created_at`, `updated_at`). The proto fields exist for future compatibility, but currently return `null`.

**UI Options:**
- **Option A (Recommended):** Hide the "Updated" field until data model is enhanced
- **Option B:** Display "Not tracked" placeholder text
- **Option C:** Show field only when timestamp is non-null

```tsx
// Option A - Hide if null
{sourceConfigDetail.updated_at && (
  <DetailRow label="Updated" value={formatDate(sourceConfigDetail.updated_at)} />
)}
```

**5. Null Safety for Optional Fields**

Many config sections are optional. Use null coalescing:

```tsx
// Safe access pattern
const schemaName = configData.validation?.schema_name ?? 'Not configured';
const aiAgentId = configData.transformation?.ai_agent_id ?? '-';
```

**6. E2E Test Requirements for UI**

Story 9.11c E2E tests must verify:
- [ ] `blob_trigger` source config renders all INGESTION fields correctly
- [ ] `scheduled_pull` source config renders alternative INGESTION fields
- [ ] Optional sections (VALIDATION, EVENTS) render "Not configured" when null
- [ ] RAW JSON section displays valid, parseable JSON
- [ ] Timestamps hidden or show placeholder when null

### Screen 2: AI Agents List View

**Route:** `/admin/ai-agents`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI AGENTS                                                [Filter ▼]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  agent_id             │ type         │ version │ status  │ model   │prompts │
│  ─────────────────────┼──────────────┼─────────┼─────────┼─────────┼─────── │
│  disease-diagnosis    │ explorer     │ v1.0    │ 🟢 active│ gpt-4o  │   3    │
│  qc-event-extractor   │ extractor    │ v1.2    │ 🟢 active│ gpt-4o-m│   2    │
│  weekly-action-plan   │ generator    │ v1.0    │ 🟢 active│ gpt-4o  │   1    │
│  leaf-quality-analyzer│ tiered-vision│ v1.1    │ 🟢 active│ gpt-4o  │   2    │
│  farmer-chat          │ conversation │ v2.0    │ 🟡 staged│ gpt-4o  │   1    │
│                                                                              │
│  Showing 5 of 5                                       [← Previous] [Next →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction:** Click row → Navigate to Agent Detail View

### Screen 2b: AI Agent Detail View (Full Page)

**Route:** `/admin/ai-agents/{agent_id}`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [← Back to Agents]                                                          │
│                                                                              │
│  🤖 AI AGENT DETAIL: disease-diagnosis                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ SUMMARY ──────────────────────────────────────────────────────────────┐ │
│  │  Agent ID:       disease-diagnosis                                     │ │
│  │  Version:        v1.0                                                  │ │
│  │  Type:           explorer                                              │ │
│  │  Status:         🟢 active                                             │ │
│  │  Description:    Diagnoses tea plant diseases from quality events      │ │
│  │                  and environmental data using RAG knowledge base       │ │
│  │  Updated:        2026-01-12 10:45 UTC                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ LLM CONFIGURATION ────────────────────────────────────────────────────┐ │
│  │  Model:              openai/gpt-4o                                     │ │
│  │  Temperature:        0.3                                               │ │
│  │  Max Tokens:         2048                                              │ │
│  │  Top P:              0.95                                              │ │
│  │  Response Format:    json_object                                       │ │
│  │                                                                        │ │
│  │  Retry Config:                                                         │ │
│  │    Max Retries:      3                                                 │ │
│  │    Backoff:          exponential                                       │ │
│  │    Timeout:          60s                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ RAG CONFIGURATION ────────────────────────────────────────────────────┐ │
│  │  RAG Enabled:        ✅ Yes                                            │ │
│  │  Domains:            plant_diseases, tea_cultivation, weather_patterns │ │
│  │  Top K:              5                                                 │ │
│  │  Score Threshold:    0.75                                              │ │
│  │  Namespace:          knowledge-v12                                     │ │
│  │  Include Metadata:   ✅ Yes                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ INPUT CONTRACT ───────────────────────────────────────────────────────┐ │
│  │  Required Fields:                                                      │ │
│  │    • farmer_id        (string)   - Farmer identifier                   │ │
│  │    • quality_events   (array)    - Recent quality event data           │ │
│  │    • weather_data     (object)   - Weather context for correlation     │ │
│  │                                                                        │ │
│  │  Optional Fields:                                                      │ │
│  │    • historical_data  (object)   - Past performance metrics            │ │
│  │    • region_context   (object)   - Regional agronomic context          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ OUTPUT CONTRACT ──────────────────────────────────────────────────────┐ │
│  │  Output Schema:      DiagnosisResult                                   │ │
│  │  Fields:                                                               │ │
│  │    • diagnosis_id     (string)   - Unique diagnosis identifier         │ │
│  │    • disease_name     (string)   - Identified disease or issue         │ │
│  │    • confidence       (float)    - Confidence score 0-1                │ │
│  │    • severity         (enum)     - low, medium, high, critical         │ │
│  │    • contributing_factors (array)- Factors that led to diagnosis       │ │
│  │    • recommendations  (array)    - Suggested actions                   │ │
│  │    • knowledge_refs   (array)    - RAG sources used                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ LINKED PROMPTS (3) ───────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  prompt_id              │ version │ status    │ author    │ updated    │ │
│  │  ───────────────────────┼─────────┼───────────┼───────────┼─────────── │ │
│  │  disease-diagnosis-main │ v2.1.0  │ 🟢 active │ jlt       │ 2026-01-15 │ │
│  │  disease-diagnosis-main │ v2.0.0  │ 📦 archived│ jlt       │ 2026-01-02 │ │
│  │  disease-diagnosis-main │ v1.0.0  │ 📦 archived│ agronomist│ 2025-12-20 │ │
│  │                                                                        │ │
│  │  [Click row to expand prompt detail below]                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ PROMPT DETAIL: disease-diagnosis-main v2.1.0 ─────────────────────────┐ │
│  │                                                                        │ │
│  │  Status:     🟢 active                                                 │ │
│  │  Author:     jlt                                                       │ │
│  │  Changelog:  Improved few-shot examples for blister blight detection   │ │
│  │  Git Commit: a1b2c3d                                                   │ │
│  │                                                                        │ │
│  │  ┌─ System Prompt ───────────────────────────────────────────────────┐ │ │
│  │  │ You are an expert tea plant pathologist and agronomist with deep  │ │ │
│  │  │ knowledge of East African tea cultivation. Your role is to        │ │ │
│  │  │ diagnose plant health issues based on quality metrics, weather    │ │ │
│  │  │ patterns, and historical data.                                    │ │ │
│  │  │                                                                   │ │ │
│  │  │ Guidelines:                                                       │ │ │
│  │  │ - Always consider weather lag effects (7-14 days)                 │ │ │
│  │  │ - Cross-reference with regional disease prevalence                │ │ │
│  │  │ - Provide actionable recommendations suitable for smallholders    │ │ │
│  │  │ ...                                                               │ │ │
│  │  │                                            [▼ Show full prompt]   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Template ────────────────────────────────────────────────────────┐ │ │
│  │  │ Analyze the following quality data for farmer {{farmer_id}}:      │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Quality Events (last 30 days)                                  │ │ │
│  │  │ {{quality_events}}                                                │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Weather Context                                                │ │ │
│  │  │ {{weather_data}}                                                  │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Knowledge Context                                              │ │ │
│  │  │ {{rag_context}}                                                   │ │ │
│  │  │                                            [▼ Show full template] │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Output Schema ───────────────────────────────────────────────────┐ │ │
│  │  │ {                                                                 │ │ │
│  │  │   "type": "object",                                               │ │ │
│  │  │   "properties": {                                                 │ │ │
│  │  │     "diagnosis_id": { "type": "string" },                         │ │ │
│  │  │     "disease_name": { "type": "string" },                         │ │ │
│  │  │     "confidence": { "type": "number", "minimum": 0, "maximum": 1 }│ │ │
│  │  │     ...                                                           │ │ │
│  │  │   }                                                               │ │ │
│  │  │ }                                          [▼ Show full schema]   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Few-Shot Examples (2) ───────────────────────────────────────────┐ │ │
│  │  │ Example 1: Blister Blight Detection                               │ │ │
│  │  │ Example 2: Weather-Related Quality Drop                           │ │ │
│  │  │                                            [▼ Show examples]      │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ A/B Test Config ─────────────────────────────────────────────────┐ │ │
│  │  │ A/B Testing:      ❌ Disabled                                     │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ RAW JSON ─────────────────────────────────────────────────────────────┐ │
│  │  [▼ Expand to view full agent configuration JSON]                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ⚠️ Read-only view. Use `agent-config` and `prompt-config` CLIs to modify.  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Full-page detail view (Option B) - click agent in list → navigate to detail page
- All agent config sections: Summary, LLM Config, RAG Config, Input/Output Contracts
- Linked prompts table with version history
- Expandable prompt detail panel (click row to view)
- Prompt content sections: System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test
- Collapsible sections for long content (system prompt, template, schema)
- Raw JSON expandable for power users
- Clear read-only indicator with CLI references
- Back navigation to agent list

---

## Decision 6: Story Breakdown

### Layer-by-Layer Implementation

| Story | Title | Layer | Points | Dependency |
|-------|-------|-------|--------|------------|
| **9.11a** | SourceConfigService gRPC in Collection Model | Backend | 3 | - |
| **9.12a** | AgentConfigService gRPC in AI Model | Backend | 5 | - |
| **9.11b** | Source Config gRPC Client + REST API in BFF | BFF | 3 | 9.11a |
| **9.12b** | Agent Config gRPC Client + REST API in BFF | BFF | 3 | 9.12a |
| **9.11c** | Source Configuration Viewer UI | Frontend | 3 | 9.11b |
| **9.12c** | AI Agent & Prompt Viewer UI | Frontend | 5 | 9.12b |

**Total: 22 story points**

### Parallel Execution

```
Week 1: 9.11a + 9.12a (parallel - backend)
Week 2: 9.11b + 9.12b (parallel - BFF, after respective backend)
Week 3: 9.11c + 9.12c (parallel - UI, after respective BFF)
```

---

## Consequences

### Positive

- **Clean separation** - CLIs own writes, gRPC/UI owns reads
- **Follows established patterns** - ADR-012 BFF architecture
- **Single-call efficiency** - Agent + prompts returned together
- **Audit visibility** - Admins can verify configs without database access
- **No new dependencies** - Uses existing MongoDB collections

### Negative

- **More proto definitions** - New messages in two proto files
- **Maintenance** - Must keep gRPC responses in sync with CLI models
- **6 stories** - More granular than a single "add config viewer" story

### Risks Mitigated

- **Accidental mutation** - Read-only APIs prevent UI-based config changes
- **Schema drift** - Using JSON strings for complex configs avoids proto duplication
- **Over-engineering** - Simple list/get operations, no complex business logic

---

## References

- ADR-012: BFF Service Composition and API Design Patterns
- ADR-011: gRPC + FastAPI + DAPR Architecture
- `scripts/source-config/` - Source config CLI
- `scripts/agent-config/` - Agent config CLI
- `scripts/prompt-config/` - Prompt config CLI
- `libs/fp-common/fp_common/models/source_config.py` - SourceConfig model
- `services/ai-model/src/ai_model/domain/agent_config.py` - AgentConfig models
- `scripts/prompt-config/src/fp_prompt_config/models.py` - Prompt models
