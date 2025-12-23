---
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-23'
sections_completed: ['technology_stack', 'python_rules', 'framework_rules', 'architecture_rules', 'testing_rules', 'ui_ux_rules', 'critical_rules']
status: 'complete'
rule_count: 176
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

| Technology | Version | Critical Notes |
|------------|---------|----------------|
| Python | 3.12 | Use 3.12 features (type hints, match statements) |
| Pydantic | 2.0 | V2 syntax required - NOT compatible with V1 |
| FastAPI | Latest | Async endpoints required for all I/O operations |
| LangChain | Latest | Use for simple linear chains ONLY |
| LangGraph | Latest | Use for stateful/conditional workflows |
| DAPR | Latest | ALL inter-service communication via DAPR sidecar |
| MongoDB | Managed | Atlas or CosmosDB - NOT self-hosted |
| Pinecone | Latest | Namespace-per-version for knowledge versioning |
| OpenRouter | N/A | Single LLM gateway - NO direct provider calls |

### Version Constraints

- **Pydantic 2.0**: V1 models will NOT work - use `model_dump()` not `dict()`
- **Python 3.12**: Required for type hint features used throughout
- **DAPR**: All events, state, secrets MUST go through DAPR components
- **OpenTelemetry**: Supported via DAPR - no manual instrumentation needed

---

## Python-Specific Rules

### Async/Await Requirements

- ALL I/O operations MUST be async (database, HTTP, MCP calls)
- Use `async def` for FastAPI endpoints
- Use `asyncio.gather()` for parallel operations, NOT sequential awaits
- Use `asyncio.wait()` with timeout for parallel analyzers

### Type Hints

- ALL function signatures MUST have type hints
- Use `TypedDict` for LangGraph state definitions
- Use Pydantic models for API request/response schemas
- Use `Optional[T]` not `T | None` for compatibility

### Pydantic 2.0 Patterns

- Use `model_dump()` NOT `dict()` (V1 syntax)
- Use `model_validate()` NOT `parse_obj()`
- Use `Field(description=...)` for LLM output schemas
- Define `model_config` as class attribute, NOT `Config` inner class

### Error Handling

- Use custom exception classes per error category (TransientError, DataError)
- Use `tenacity` for retry logic with exponential backoff
- Catch specific exceptions, NOT bare `except:`
- Log errors with structlog including trace_id and agent_id

### Import Conventions

- Absolute imports only (no relative imports)
- Group: stdlib, third-party, local
- One class/function per import line for clarity

---

## Framework-Specific Rules

### LangChain vs LangGraph Decision

| Use Case | Framework | Example |
|----------|-----------|---------|
| Simple extraction | LangChain | QC event extraction, triage classification |
| Stateful workflow | LangGraph | Quality analysis saga, action plan generation |
| Parallel branches | LangGraph | Multi-analyzer fan-out/join |
| Conditional routing | LangGraph | Triage → analyzer selection |

### LangGraph Patterns

- ALWAYS use `StateGraph` with `TypedDict` state
- ALWAYS enable MongoDB checkpointing for crash recovery
- Use `fan_out` node type for parallel analyzers
- Use `conditional` edges for triage routing
- Set `timeout_ms` on parallel branches (default: 30000)
- Handle branch failures with `on_branch_error: proceed_without`

### DAPR Communication Rules

- **Inter-model calls**: gRPC via DAPR Service Invocation
- **Events**: DAPR Pub/Sub (NOT direct HTTP)
- **Scheduling**: DAPR Jobs (NOT cron in code)
- **State**: DAPR State Store (NOT direct MongoDB for cross-model state)
- **Secrets**: DAPR Secret Store (NOT environment variables for sensitive data)

### DAPR Event Naming

- Format: `{source-model}.{entity}.{action}`
- Examples: `collection.quality_event.created`, `ai.diagnosis.complete`
- Use past tense for completed actions

### MCP Server Rules

- MCP servers are STATELESS - no in-memory caching
- Each domain model exposes ONE MCP server
- Tools return data, NOT make decisions
- Use Pydantic models for tool input/output schemas
- Tool names: `get_*`, `search_*`, `list_*` (verbs for read operations)

### FastAPI/BFF Rules

- BFF is the ONLY external-facing API
- Internal cluster: gRPC via DAPR
- External clients: REST + WebSocket via BFF
- Use dependency injection for DAPR client, MongoDB, etc.
- Background tasks for non-blocking operations

---

## Architecture & Domain Model Rules

### Domain Model Boundaries (8 Models)

| Model | Responsibility | Does NOT |
|-------|---------------|----------|
| Collection | Ingest, validate, store documents | Make business decisions |
| Plantation | Farmer/factory digital twin | Store raw documents |
| Knowledge | Diagnose situations | Prescribe solutions |
| Action Plan | Generate recommendations | Store diagnoses, deliver messages |
| Notification | Deliver messages (SMS, WhatsApp, Voice IVR) | Generate content, handle dialogue |
| Market Analysis | Buyer profiles, lot matching | Generate action plans |
| AI Model | Agent orchestration, LLM calls | Own business data |
| Conversational AI | Two-way dialogue (voice chatbot, text chat) | Execute AI logic, deliver final messages |

### Cross-Model Communication

- Models communicate via DAPR Pub/Sub events ONLY
- NO direct database access across models
- Use MCP servers for data retrieval between models
- Each model owns its MongoDB collections exclusively

### Data Ingestion Rules (Collection Model)

- **Trust provided IDs** - Do NOT verify farmer_id against Plantation Model on ingest
- **Store with warnings, don't reject** - Validation failures are stored with warnings, not rejected
- **Best-effort semantic checking** - Collection Model is intake, not police
- **Missing farmer ID** - Store document with warning, not rejection

### MongoDB Collection Ownership

- `collection_model`: `quality_events`, `weather_data`, `documents_index`
- `plantation_model`: `farmers`, `factories`, `regions`, `grading_models`
- `knowledge_model`: `diagnoses`, `triage_feedback`
- `action_plan_model`: `action_plans`, `farmer_dashboard_view`
- `ai_model`: `prompts`, `rag_documents`, `workflow_checkpoints`, `agent_configs`
- `conversational_ai_model`: `sessions`, `conversation_history`, `channel_configs`

### Region Definition (Plantation Model)

- Regions are defined by **county + altitude band** combination
- Altitude bands: low (<800m), medium (800-1200m), high (>1200m)
- Use Google Elevation API to determine farm altitude at registration
- Weather data is collected **per region**, NOT per farm (cost optimization)
- Flush calendar (harvest timing) varies by region based on seasonal patterns

### AI Model Agent Types

| Type | Framework | Purpose |
|------|-----------|---------|
| Extractor | LangChain | Data extraction, validation, classification |
| Explorer | LangGraph | Multi-step analysis with conditional routing |
| Generator | LangGraph | Content generation (action plans, reports) |
| Conversational | LangGraph | Multi-turn dialogue with context management |

### Triage-First Pattern

- ALWAYS use Triage Agent (Haiku) before expensive analyzers
- Triage classifies: disease, weather, technique, handling, soil
- If confidence >= 0.7: route to primary analyzer only
- If confidence < 0.7: run multiple analyzers in parallel

### Weather Correlation Pattern (Knowledge Model)

- Weather analyzer uses **3-7 day lookback** for lag correlation
- Coffee quality issues often manifest days after weather events
- Fetch weather history via Plantation Model MCP, NOT direct API
- Correlate: heavy rain → moisture issues, heat waves → stress symptoms

### Triage Feedback Loop (Knowledge Model)

- Store triage predictions with actual analyzer outcomes
- Collection: `triage_feedback` in knowledge_model database
- Periodic evaluation: compare triage confidence vs actual diagnosis match
- Use feedback to improve triage prompt and routing thresholds
- Target: triage accuracy > 85% for primary classification

### Grading Model Flexibility

- **NEVER hardcode grade labels** (A, B, C, D, Premium, Standard, Rejected, etc.)
- Grading models are fully configurable per factory/regulatory authority
- Types: binary (Accept/Reject), ternary (Premium/Standard/Reject), multi-level (A/B/C/D)
- Always include `grading_model_id` reference for label lookup

**Grade Calculation:**
- Grades are computed from **weighted attributes** defined in the Grading Model
- Attributes: moisture %, leaf count, defect count, bean size, color score, etc.
- Each attribute has a weight; final score = weighted sum normalized to 0.0-1.0
- Grade thresholds map score ranges to labels (e.g., 0.8+ = Premium, 0.5-0.8 = Standard)

| Pattern | Usage | Example |
|---------|-------|---------|
| Semantic category | Trigger conditions | `grade_category: "rejection"` (lowest tier) |
| Normalized threshold | Score-based triggers | `quality_score_below: 0.3` (0.0-1.0 scale) |
| Dynamic object map | Grade distributions | `{ [grading_model_label]: count }` |

- For UI display: lookup grade labels from factory's Grading Model at render time
- For triggers: use semantic categories or normalized thresholds, NOT label matching
- Grade distributions and statistics: store as dynamic objects keyed by Grading Model labels

### Externalized Configuration

- **Prompts**: Stored in MongoDB, NOT in source code
- **RAG Knowledge**: Stored in MongoDB + Pinecone
- **Agent Configs**: YAML files in Git, deployed to MongoDB
- Hot-reload: 5-minute cache TTL for prompts and knowledge

### Triggering Responsibility

- **Domain models own triggers** - NOT the AI Model
- Event triggers: domain model subscribes to event, invokes AI workflow
- Schedule triggers: domain model configures DAPR Jobs, invokes AI workflow
- AI Model is PASSIVE - only executes when invoked by domain models

---

## Testing Rules

### Test Organization

- Tests live in `tests/` directory mirroring `src/` structure
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Golden samples: `tests/golden/`

### Agent Testing Strategy

| Test Type | Purpose | Mocking |
|-----------|---------|---------|
| Unit | Individual node functions | Mock LLM, MCP, MongoDB |
| Golden Sample | End-to-end agent accuracy | Real LLM, mock external data |
| Integration | Cross-model workflows | Mock external APIs only |

### Golden Sample Testing (Critical)

- ALWAYS maintain golden samples for each agent
- Store in `tests/golden/{agent_name}/`
- Include: input payload, expected output, acceptable variance
- Run golden tests on every PR that touches agent code
- Use `farmer-cli test golden --agent {name}` to run

### LLM Mocking

- Use `unittest.mock` with recorded responses for unit tests
- Store LLM response fixtures in `tests/fixtures/llm_responses/`
- NEVER mock LLM in golden sample tests (defeats purpose)

### MCP Tool Mocking

- Mock MCP tool responses at the client level
- Use `pytest-asyncio` for async test functions
- Create reusable fixtures for common MCP responses

### Test Naming

- Test files: `test_{module_name}.py`
- Test functions: `test_{function_name}_{scenario}`
- Example: `test_triage_agent_routes_to_disease_analyzer`

---

## UI/UX Rules

### Design System Stack

| Technology | Purpose | Critical Notes |
|------------|---------|----------------|
| Tailwind CSS | Utility-first styling | Purge unused CSS for Kenya network conditions |
| shadcn/ui | Component library | Copy-paste components, Radix primitives with ARIA built-in |
| MUI v6 | DataGrid, Charts, Forms | Use with custom theme configuration |
| Inter | Typography | Clean, professional font family |

### Design Tokens (Mandatory)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-win` | #22C55E | Primary ≥85%, success states |
| `--color-watch` | #F59E0B | Primary 70-84%, warnings |
| `--color-action` | #EF4444 | Primary <70%, errors, alerts |
| `--color-primary` | #16A34A | Brand, Forest Green, agriculture theme |
| `--color-secondary` | #5C4033 | Earth Brown |
| `--spacing-unit` | 4px | Base spacing multiplier |
| `--radius-default` | 6px | Cards and containers |
| `--radius-badge` | 16px | Status badges |

### Status Badge Pattern (Critical)

| Status | Color | Icon | Background | Threshold |
|--------|-------|------|------------|-----------|
| WIN | Forest Green `#1B4332` | ✅ | `#D8F3DC` | ≥85% Primary |
| WATCH | Harvest Gold `#D4A03A` | ⚠️ | `#FFF8E7` | 70-84% Primary |
| ACTION | Warm Red `#C1292E` | 🔴 | `#FFE5E5` | <70% Primary |

**Rule**: ALWAYS use color + icon + text label for status (color independence for accessibility)

### Custom Components Required

| Component | Purpose | Notes |
|-----------|---------|-------|
| StatusBadge | Quality category display | WIN/WATCH/ACTION variants |
| TrendIndicator | Quality trajectory | ↑ up, ↓ down, → stable |
| FarmerCard | Single farmer overview | Avatar, Primary %, trend, quick actions |
| LeafTypeTag | Issue identification | Coaching tooltips on hover/focus |
| ActionStrip | Dashboard header counts | Clickable category filters |
| SMSPreview | Template editing | Phone mockup with character count |

### Responsive Breakpoints (MUI v6)

| Breakpoint | Width | Layout |
|------------|-------|--------|
| xs | 0-599px | Single column, bottom navigation, stacked cards |
| sm | 600-899px | Optional 2-column, side-by-side buttons |
| md | 900-1199px | 2-column master-detail, filter sidebar |
| lg | 1200-1535px | Full Command Center, 3-column dashboard |
| xl | 1536px+ | 4-column capability, side-by-side comparison |

**Rule**: Mobile-first CSS, desktop-optimized for Factory/Admin dashboards

### Touch & Accessibility Requirements

| Requirement | Standard | Notes |
|-------------|----------|-------|
| Touch targets | 48x48px minimum | Buttons, icons, list items |
| Focus ring | 3px Forest Green outline | All interactive elements |
| WCAG level | 2.1 AA | Target compliance |
| Contrast ratio | 4.5:1 minimum | Text on backgrounds |

### Accessibility Patterns

- **Focus management**: Return focus to trigger after modal close
- **Skip links**: "Skip to main content" on Tab
- **ARIA labels**: `role="status"` for badges, `aria-live="polite"` for updates
- **Keyboard**: Tab navigation, Escape closes modals, Arrow keys in menus
- **Reduced motion**: Respect `prefers-reduced-motion` media query

### Multi-Channel Consistency

| Channel | Format | Rules |
|---------|--------|-------|
| Dashboard | StatusBadge components | WIN/WATCH/ACTION with icons |
| SMS | Emoji + text (160 chars) | ✅ for WIN, ⚠️ for WATCH, 🔴 for ACTION |
| Voice IVR | Spoken audio | Numbered menus, 0.8s pauses between options |

**SMS Template Pattern**:
```
[Name], chai yako:
[Status Emoji] [Primary %] daraja la kwanza
Tatizo: [Leaf Type Issue]
[Action Tip]
```

### UI Anti-Patterns to Avoid

- **NO hardcoded colors** - Always use design tokens
- **NO status without icons** - Color alone is not accessible
- **NO touch targets < 48px** - Field officers use mobile in field conditions
- **NO hover-only interactions** - Must work with touch
- **NO blocking modals for confirmations** - Use toast/snackbar for success
- **NO infinite scroll without pagination fallback** - Kenya network conditions

### Form Patterns

| Pattern | Rule |
|---------|------|
| Required fields | Red asterisk (*) after label |
| Validation | Inline below field on blur, summary at top on submit |
| Error state | `#C1292E` border + ✕ icon + error text |
| Phone format | Auto-format to +254 XXX XXX XXX |

### Loading & Empty States

| Context | Pattern |
|---------|---------|
| Initial page load | Skeleton screens (match actual layout) |
| Data refresh | Spinner in header after 500ms |
| Button action | Inline spinner after 200ms |
| No results | Illustration + message + action button |
| No farmers need action | "No farmers need action today 🎉" (celebration) |

---

## Critical Don't-Miss Rules

### Anti-Patterns to Avoid

- **NO direct LLM provider calls** - Always use OpenRouter gateway
- **NO synchronous I/O** - All database, HTTP, MCP calls must be async
- **NO cross-model database access** - Use MCP servers for data retrieval
- **NO hardcoded prompts** - All prompts loaded from MongoDB
- **NO in-memory state in MCP servers** - They must be stateless
- **NO cron jobs in code** - Use DAPR Jobs for scheduling
- **NO environment variables for secrets** - Use DAPR Secret Store

### LLM Cost Optimization

- Use Haiku for triage/classification (fast, cheap: ~$0.001/call)
- Use Sonnet for analysis requiring reasoning
- Use Sonnet for vision tasks (image analysis)
- ALWAYS set `max_tokens` to prevent runaway costs
- Cache RAG context - don't re-fetch for same request

### Vision Processing

- Triage images with Haiku at 256x256 resolution first
- Only send full resolution to Sonnet if triage indicates need
- Store images in Azure Blob, pass URLs not base64 when possible

### Farmer Context

- Farmers are often basic users with limited English
- Action plans must be simple, clear, actionable
- Generate triple-format output: detailed (factory), SMS summary (farmer), voice script (farmer via IVR)
- Support SMS + Voice IVR delivery for farmer messages
- Voice IVR enables low-literacy farmers to hear detailed explanations in local languages

### SMS Cost Optimization (Notification Model)

- Target **1-2 SMS segments** per message (160 chars GSM-7, 70 chars Unicode)
- Use GSM-7 encoding when possible (avoid emojis, special characters)
- Action Generator must output `sms_summary` field (max 300 chars)
- Tiered strategy: critical alerts = immediate, routine = batched daily digest
- Two-way SMS: support keyword commands (STOP, HELP, STATUS)
- Include Voice IVR prompt in SMS: "Piga *384# kwa maelezo zaidi" (Call *384# for more details)

### Voice IVR Rules (Notification Model)

- **Purpose**: Provide detailed action plan explanations for low-literacy farmers via spoken audio
- **Providers**: Africa's Talking (primary), Twilio (fallback) for IVR; Google Cloud TTS / Amazon Polly for TTS
- **Languages supported**: Swahili (sw-KE), Kikuyu (ki-KE), Luo (luo-KE)

**Voice Script Generation:**
- Action Generator must output `voice_script` field alongside `sms_summary`
- Voice scripts use `VoiceScript` Pydantic model with: greeting, quality_summary, main_actions (max 3), closing
- Maximum voice script length: 2000 chars (~3 minutes of speech)
- Use simple language (6th-grade reading level equivalent)
- Action items start with verbs: "Anika..." (Dry...), "Usivune..." (Don't harvest...)

**IVR Call Flow:**
1. Farmer dials shortcode (*384#)
2. Caller ID lookup → farmer identification (fallback: enter farmer ID)
3. Language selection via DTMF (1=Swahili, 2=Kikuyu, 3=Luo)
4. TTS plays personalized action plan (2-3 minutes)
5. Options menu: replay (1), help (2), end (9)

**TTS Configuration:**
- Speaking rate: 0.9x (slightly slower for clarity)
- Pauses: 0.5s after greeting, 0.8s between action items
- Audio encoding: MP3, 8kHz sample rate (phone quality)
- Max call duration: 5 minutes (cost control)
- Max replays: 3 per call (abuse prevention)

**Voice IVR Anti-Patterns:**
- **NO hardcoded language strings** - All voice content via templates in MongoDB
- **NO synchronous TTS calls** - Pre-generate audio or stream asynchronously
- **NO storing raw audio** - Generate on-demand or cache with TTL

### Conversational AI Rules

- **Purpose**: Enable interactive two-way dialogue with farmers via voice chatbot and text chat
- **Channels**: Voice chatbot (phone), WhatsApp chat, SMS text
- **Architecture**: Open-Closed Principle - base handler + channel-specific adapters

**Channel Adapters:**
- `VoiceChatbotAdapter`: Real-time voice dialogue, STT/TTS integration
- `WhatsAppChatAdapter`: Async text messaging, media support
- `SMSChatAdapter`: Simple text exchange, 160-char limits

**Session Management:**
- Store sessions in `conversational_ai_model.sessions` collection
- Session timeout: 30 minutes of inactivity
- Persist conversation history for context across turns
- Use `session_id` to link multi-turn conversations

**Integration Pattern:**
- Conversational AI Model invokes AI Model for LLM processing
- Uses existing MCP servers for data retrieval (does NOT expose own MCP)
- Hands off final delivery to Notification Model

**Conversational AI Anti-Patterns:**
- **NO direct LLM calls** - Always invoke via AI Model
- **NO final message delivery** - Hand off to Notification Model
- **NO business data ownership** - Query via MCP servers

### Event Deduplication

- Same farmer may have multiple quality events in short period
- Use DAPR Jobs to aggregate before triggering expensive analysis
- Deduplicate by farmer_id + time window (e.g., 1 hour)

### Confidence Thresholds

- Triage routing: >= 0.7 = single analyzer, < 0.7 = parallel
- Diagnosis aggregation: primary = highest confidence, secondary >= 0.5
- A/B test traffic: typically 10-20% for variant

### Deployment

- Single Kubernetes namespace per environment (qa, preprod, prod)
- ConfigMaps for environment-specific settings
- Secrets for credentials (MongoDB, API keys)
- All models deployed as separate pods in same namespace

---

## Reference Documents

This file contains critical rules. For detailed decisions not covered here:

| Need | Document |
|------|----------|
| Decision inventory + traceability | `_bmad-output/architecture-decision-index.md` |
| Full architectural rationale | `_bmad-output/architecture.md` |
| AI Model implementation details | `_bmad-output/ai-model-developer-guide.md` |
| **UX Design Specification** | `_bmad-output/ux-design-specification/index.md` |
| Component specifications | `_bmad-output/ux-design-specification/6-component-strategy.md` |
| UX consistency patterns | `_bmad-output/ux-design-specification/7-ux-consistency-patterns.md` |
| Responsive & accessibility | `_bmad-output/ux-design-specification/8-responsive-design-accessibility.md` |

**When to look up more detail:**
- Implementing a specific domain model feature (Plantation, Collection, etc.)
- Unsure about a pattern not explicitly covered here
- Need the "why" behind a decision, not just the "what"
- **Implementing frontend components** - See UX Design Specification for visual patterns, component specs, and accessibility requirements

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Check `architecture-decision-index.md` for decisions not covered here
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

---

_Last Updated: 2025-12-23_
