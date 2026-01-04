# Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **AI as Domain Model** | Yes (6th model) | Centralized intelligence, clean separation |
| **Agent Logic** | All in AI Model | Domain models stay simple, no AI dependencies |
| **Communication** | Event-driven async | Non-blocking, scalable, resilient |
| **Event Broker** | DAPR Pub/Sub | Broker-agnostic |
| **Event Payload** | References (IDs) | Small events, MCP for data fetch |
| **Result Delivery** | In completion event | Stateless AI Model, domain owns data |
| **Triggering** | Domain model responsibility | Business logic stays in domain |
| **Scheduler** | DAPR Jobs | Scheduler-backend agnostic |
| **RAG Access** | Internal only | Domain models don't need to know about RAG |
| **RAG Curation** | Admin UI (manual) | Agronomists manage knowledge |
| **Agent Types** | 5 (Extractor, Explorer, Generator, Conversational, Tiered-Vision) | Covers patterns including dialogue and cost-optimized image analysis |
| **Type Implementation** | In code | Workflow logic is code |
| **Instance Config** | YAML → MongoDB → Pydantic | Git source, MongoDB runtime, type-safe |
| **LLM Model Config** | Explicit per agent | Clarity over indirection; no task_type routing |
| **LLM Gateway Role** | Resilience only | Fallback, retry, cost tracking; not model selection |
| **LLM Gateway Config** | Pydantic Settings | Aligns with project pattern; env vars, no YAML |
| **Thumbnail Generation** | Collection Model at ingestion | Done once, AI fetches only what it needs |
| **Tiered Vision Agents** | Extractor (screen) + Explorer (diagnose) | Fast Haiku screen, Sonnet only when needed |
| **Prompts** | Separate .md files | Better review, can be long |
| **Observability** | DAPR OpenTelemetry | Backend-agnostic |
