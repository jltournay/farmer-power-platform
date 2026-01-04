# Prompt Management

**Decision:** Prompts are externalized to MongoDB, enabling hot-reload and A/B testing without redeployment, with **MongoDB Change Streams for real-time cache invalidation** (see ADR-013).

**Problem:** Storing prompts in source code requires rebuild and redeploy for every prompt change:
- Slow iteration during prompt tuning
- Risky deployments for text-only changes
- Cannot A/B test prompts in production
- Cannot rollback prompts independently of code

**Solution:** Externalized prompt management with the same versioning pattern as RAG knowledge, and the same cache pattern as Agent Configurations.

> **Implementation details:** See `ai-model-developer-guide/4-prompt-engineering.md` for writing effective prompts and `ai-model-developer-guide/5-testing-tuning.md` for prompt validation with golden samples.

## Prompt Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNALIZED PROMPT MANAGEMENT                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SOURCE OF TRUTH: Git Repository                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  prompts/                                                        │   │
│  │  ├── explorers/disease-diagnosis/                               │   │
│  │  │   ├── system.md                                              │   │
│  │  │   ├── template.md                                            │   │
│  │  │   └── prompt.yaml  (metadata, version, A/B config)           │   │
│  │  └── generators/action-plan/                                    │   │
│  │      └── ...                                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ CI/CD: farmer-cli prompt publish         │
│                              ▼                                          │
│  RUNTIME STORAGE: MongoDB                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Collection: prompts                                             │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  {                                                         │  │   │
│  │  │    prompt_id: "disease-diagnosis",                         │  │   │
│  │  │    version: "2.1.0",                                       │  │   │
│  │  │    status: "active",                                       │  │   │
│  │  │    system_prompt: "You are an expert...",                  │  │   │
│  │  │    template: "## Context\n{{document}}...",                │  │   │
│  │  │    metadata: { author, updated_at, changelog }             │  │   │
│  │  │  }                                                         │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│            ┌─────────────────┴─────────────────┐                        │
│            │      MongoDB Change Stream         │                        │
│            │   (insert, update, delete watch)   │                        │
│            └─────────────────┬─────────────────┘                        │
│                              │ Invalidate on change                     │
│                              ▼                                          │
│  AI MODEL RUNTIME (PromptService)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Prompt Cache (ADR-013 Pattern)                                 │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  • Warmed on startup (before accepting requests)          │  │   │
│  │  │  • Invalidated via Change Stream (real-time)              │  │   │
│  │  │  • TTL fallback: 5 minutes (safety net)                   │  │   │
│  │  │  • Metrics: hits, misses, invalidations, age, size        │  │   │
│  │  │  • Base class: MongoChangeStreamCache[PromptDocument]     │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │  Cached Prompts:                                                 │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                      │   │
│  │  │ disease-diag    │  │ action-plan     │                      │   │
│  │  │ v2.1.0 (active) │  │ v1.3.0 (active) │                      │   │
│  │  └─────────────────┘  └─────────────────┘                      │   │
│  │                                                                  │   │
│  │  Staged prompts (A/B): queried fresh (not cached)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prompt Cache Behavior (ADR-013)

| Event | Behavior |
|-------|----------|
| Service starts | Cache warmed immediately before accepting requests |
| Prompt inserted | Change Stream fires → cache invalidated → next request loads fresh |
| Prompt updated | Change Stream fires → cache invalidated → next request loads fresh |
| Prompt deleted | Change Stream fires → cache invalidated → next request loads fresh |
| TTL expires (fallback) | Next request reloads from database |
| Staged prompt request | Queried fresh from MongoDB (not cached, A/B test traffic only) |

**OpenTelemetry Metrics:**

| Metric | Type | Purpose |
|--------|------|---------|
| `prompt_cache_hits_total` | Counter | Track cache efficiency |
| `prompt_cache_misses_total` | Counter | Alert on high miss rate |
| `prompt_cache_invalidations_total` | Counter | Monitor change frequency |
| `prompt_cache_age_seconds` | Gauge | Detect stale cache |
| `prompt_cache_size` | Gauge | Verify prompts loaded |

## Prompt Document Schema

```yaml
# MongoDB: prompts collection
prompt_document:
  prompt_id: string              # "disease-diagnosis"
  agent_id: string               # "diagnose-quality-issue"
  version: string                # "2.1.0" (semver)
  status: enum                   # "draft" | "staged" | "active" | "archived"

  content:
    system_prompt: string        # Full system prompt text
    template: string             # Template with {{variables}}
    output_schema: object        # JSON schema for validation
    few_shot_examples: array     # Optional examples

  metadata:
    author: string
    created_at: datetime
    updated_at: datetime
    changelog: string            # What changed in this version
    git_commit: string           # Source commit SHA

  ab_test:
    enabled: boolean
    traffic_percentage: number   # 0-100
    test_id: string              # For metrics grouping

  # Compound index: (prompt_id, status) for fast lookups
  # Compound index: (prompt_id, version) for version queries
```

## Prompt Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROMPT LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Git: Edit .md file                                                    │
│          │                                                              │
│          │ PR merged to main                                            │
│          ▼                                                              │
│   CI/CD: farmer-cli prompt publish --status staged                      │
│          │                                                              │
│          │ Published to MongoDB with status=staged                      │
│          ▼                                                              │
│   STAGED ──────────────────────────────────────────────────────────────│
│          │                                                              │
│          ├──► Option A: Direct promote                                  │
│          │    farmer-cli prompt promote --id disease-diagnosis          │
│          │                                                                 │
│          └──► Option B: A/B test first                                  │
│               farmer-cli prompt ab-test start --id disease-diagnosis    │
│               --traffic 20 --duration 7d                                │
│                    │                                                    │
│                    │ Monitor metrics                                    │
│                    ▼                                                    │
│               farmer-cli prompt ab-test analyze                         │
│                    │                                                    │
│                    ├──► Success: farmer-cli prompt promote              │
│                    └──► Failure: farmer-cli prompt rollback             │
│                                                                         │
│   ACTIVE ──────────────────────────────────────────────────────────────│
│          │                                                              │
│          │ Issue detected in production                                 │
│          ▼                                                              │
│   farmer-cli prompt rollback --id disease-diagnosis --to-version 2.0.0  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Runtime Prompt Loading

```yaml
# ai-model/config/prompt-loader.yaml
prompt_loader:
  source: mongodb
  connection:
    uri_secret: MONGODB_URI
    database: ai_model
    collection: prompts

  cache:
    enabled: true
    ttl_seconds: 300          # 5 minutes - balance between freshness and performance
    max_entries: 100

  fallback:
    enabled: true
    source: filesystem        # Fall back to bundled prompts if MongoDB unavailable
    path: /app/prompts/fallback/

  ab_test:
    routing_key: farmer_id    # Consistent routing per farmer
    metrics_enabled: true
```

## Prompt A/B Testing

```yaml
# Example: A/B test configuration in MongoDB
prompt_ab_test:
  test_id: "disease-diagnosis-v2.2-test"
  prompt_id: "disease-diagnosis"
  status: active
  started_at: "2024-06-15T00:00:00Z"

  control:
    version: "2.1.0"
    traffic_percentage: 80

  variant:
    version: "2.2.0"
    traffic_percentage: 20

  metrics:
    - diagnosis_accuracy
    - confidence_calibration
    - agronomist_override_rate

  success_criteria:
    diagnosis_accuracy: ">= 0"     # No regression
    confidence_calibration: ">= 0"
    min_samples: 200

  auto_promote:
    enabled: false                 # Require manual review
```

## Prompt-Agent Validation Rules

Prompts reference agents via `agent_id`. Validation ensures referential integrity.

```
┌─────────────────────────────────────────────────────────────────┐
│  VALIDATION FLOW                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  farmer-cli prompt publish                                       │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  1. Read prompt YAML from git                               ││
│  │  2. Check prompt status                                     ││
│  │       │                                                     ││
│  │       ├── draft → Skip agent validation (dev flexibility)  ││
│  │       │                                                     ││
│  │       └── staged/active → Validate agent_id exists         ││
│  │              │                                              ││
│  │              ├── Agent exists → Publish to MongoDB          ││
│  │              │                                              ││
│  │              └── Agent missing → ERROR, abort publish       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Validation Rules:**

| Prompt Status | Agent Validation | Rationale |
|---------------|------------------|-----------|
| `draft` | Not required | Development flexibility - prompts can be drafted before agent config |
| `staged` | Required | Pre-production must have valid agent reference |
| `active` | Required | Production prompts must have valid agent |
| `archived` | Not checked | Historical record, agent may have been deleted |

**Implementation:**

```python
# In farmer-cli prompt publish command
async def validate_prompt_agent_reference(prompt: PromptDocument) -> None:
    """Validate agent_id exists in agent_configs collection."""
    if prompt.status in ("staged", "active"):
        agent = await agent_config_repo.get_by_id(prompt.agent_id)
        if agent is None:
            raise ValidationError(
                f"Cannot publish prompt '{prompt.prompt_id}' with status '{prompt.status}': "
                f"agent_id '{prompt.agent_id}' does not exist in agent_configs"
            )
```

**Why CLI validation, not runtime:**

| Approach | Pros | Cons |
|----------|------|------|
| CLI validation | No runtime overhead, early error detection | Requires CI/CD discipline |
| Runtime validation | Always consistent | Adds latency to every request |
| Database constraints | Enforced at DB level | MongoDB lacks foreign keys |

**Decision:** CLI validation at publish time. Trust CI/CD pipeline. No runtime validation overhead.

## Key Benefits

| Benefit | Description |
|---------|-------------|
| **No Redeploy** | Prompt changes take effect within cache TTL (5 min) |
| **Safe Rollback** | Instant rollback to any previous version |
| **A/B Testing** | Test prompt changes on subset of traffic |
| **Audit Trail** | Full history of all prompt versions |
| **Git Integration** | Prompts still version-controlled in Git |
