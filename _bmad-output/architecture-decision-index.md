# Architecture Decision Index

_This index maps all architectural decisions from `architecture.md` to their coverage in `project-context.md`. Use this to ensure no decisions are lost when AI agents work from the lean context file._

---

## Legend

| Status | Meaning |
|--------|---------|
| **COVERED** | Decision is captured in project-context.md |
| **PARTIAL** | Decision essence is there but details may differ |
| **GAP** | Decision is NOT in project-context.md - potential risk |

---

## Collection Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-001 | Collection Model is data gateway - does NOT make business decisions | Collection Model | COVERED | Domain Model Boundaries table |
| AD-002 | Trust provided IDs (no cross-model verification on ingest) | Trust Model | COVERED | Data Ingestion Rules section |
| AD-003 | Validation failures stored with warnings, not rejected | Trust Model | COVERED | Data Ingestion Rules section |
| AD-004 | Raw payload to Azure Blob, index to MongoDB | Document Storage | PARTIAL | Implied by MongoDB ownership |
| AD-005 | LLM Agent for extraction + semantic validation | Ingestion Pipeline | COVERED | Extractor agent type mentioned |

## Knowledge Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-010 | Knowledge Model DIAGNOSES only, does NOT prescribe | Overview | COVERED | Domain Model Boundaries table |
| AD-011 | Three-Tier Agent Pattern (Explorer → Triage → Analyzers) | Agent Pattern | COVERED | Triage-First Pattern section |
| AD-012 | Triage Agent uses Haiku for fast classification | Triage Agent | COVERED | LLM Cost Optimization |
| AD-013 | Confidence >= 0.7: single analyzer; < 0.7: parallel | Routing Logic | COVERED | Confidence Thresholds section |
| AD-014 | LangGraph Saga for parallel analyzer orchestration | LangGraph Saga | COVERED | LangGraph Patterns section |
| AD-015 | MongoDB checkpointing for crash recovery | Crash Recovery | COVERED | LangGraph Patterns section |
| AD-016 | Weather lag correlation (3-7 days lookback) | Weather Analyzer | COVERED | Weather Correlation Pattern section |
| AD-017 | Diagnosis deduplication via DAPR Jobs aggregation | Deduplication | COVERED | Event Deduplication section |
| AD-018 | Triage feedback loop for continuous improvement | Feedback Loop | COVERED | Triage Feedback Loop section |
| AD-019 | Aggregation rules: primary=highest confidence, secondary>=0.5 | Aggregation | COVERED | Confidence Thresholds section |

## Plantation Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-020 | Plantation Model is master data registry | Overview | COVERED | Domain Model Boundaries table |
| AD-021 | Regions defined by county + altitude band | Region Entity | COVERED | Region Definition section |
| AD-022 | Weather collected per region, not per farm (cost optimization) | Weather Collection | COVERED | Region Definition section |
| AD-023 | Hybrid performance summaries (batch + streaming) | Performance Summary | GAP | Implementation detail |
| AD-024 | Google Elevation API for farm altitude | Farmer Registration | COVERED | Region Definition section |
| AD-025 | Flush calendar per region (seasonal context) | Region Entity | COVERED | Region Definition section |

## Action Plan Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-030 | Action Plan Model PRESCRIBES only | Overview | COVERED | Domain Model Boundaries table |
| AD-031 | Two-Agent Pattern (Selector + Generator) | Agent Pattern | GAP | Specific pattern not in context |
| AD-032 | Dual-format output (detailed + simplified) | Output Format | COVERED | Farmer Context section |
| AD-033 | Action Plan Model does NOT expose MCP Server | MCP Decision | PARTIAL | "Tools return data" implies it |
| AD-034 | Message delivery is separate infrastructure | Notification | COVERED | Notification in Domain Model Boundaries |
| AD-035 | Tiered SMS strategy (1-2 segments, GSM-7) | SMS Cost | COVERED | SMS Cost Optimization section |
| AD-036 | Two-way communication with keyword commands | Inbound Messages | COVERED | SMS Cost Optimization section |
| AD-037 | Message delivery retry with escalation | Delivery Assurance | GAP | Infrastructure detail |
| AD-038 | Group messaging tiers (individual, cooperative, regional) | Group Messaging | GAP | Feature detail |

## AI Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-040 | AI Model is 6th Domain Model (centralized intelligence) | Overview | COVERED | Domain Model Boundaries table |
| AD-041 | AI Model is STATELESS, results via events | Communication | COVERED | Anti-patterns section |
| AD-042 | AI Model does NOT expose MCP Server | MCP Decision | PARTIAL | Implied |
| AD-043 | Four agent types: Extractor, Explorer, Generator, Conversational | Agent Types | COVERED | AI Model Agent Types table |
| AD-044 | Agent instances in YAML, types in code | Configuration | GAP | Implementation detail |
| AD-045 | Triggering is domain model responsibility | Triggering | COVERED | Triggering Responsibility section |
| AD-046 | OpenRouter as unified LLM gateway | LLM Gateway | COVERED | Technology Stack table |
| AD-047 | Tiered vision processing (Haiku screen → Sonnet full) | Vision Processing | COVERED | Vision Processing section |
| AD-048 | RAG is internal to AI Model only | RAG Engine | PARTIAL | Implied by MCP rules |
| AD-049 | Prompts externalized to MongoDB | Prompt Management | COVERED | Externalized Configuration |
| AD-050 | Prompt A/B testing capability | Prompt Management | COVERED | A/B test traffic in Confidence Thresholds |

## Notification Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-080 | Notification Model is 7th Domain Model (message delivery) | Overview | COVERED | Domain Model Boundaries table |
| AD-081 | One-way message delivery only (no dialogue) | Scope | COVERED | Domain Model Boundaries table |
| AD-082 | Channels: SMS, WhatsApp, Voice IVR | Channels | COVERED | Notification row in boundaries |
| AD-083 | Voice IVR for low-literacy farmers | Voice IVR | COVERED | Voice IVR Rules section |
| AD-084 | TTS providers: Google Cloud TTS, Amazon Polly | TTS | COVERED | Voice IVR Rules section |
| AD-085 | IVR providers: Africa's Talking (primary), Twilio (fallback) | IVR | COVERED | Voice IVR Rules section |
| AD-086 | Voice script max 2000 chars (~3 min speech) | Voice Script | COVERED | Voice IVR Rules section |
| AD-087 | Languages: Swahili, Kikuyu, Luo | Localization | COVERED | Voice IVR Rules section |
| AD-088 | Notification Model does NOT generate content | Scope | COVERED | Domain Model Boundaries table |

## Conversational AI Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-090 | Conversational AI Model is 8th Domain Model (two-way dialogue) | Overview | COVERED | Domain Model Boundaries table |
| AD-091 | Channels: Voice chatbot, WhatsApp chat, SMS text | Channels | COVERED | Conversational AI Rules section |
| AD-092 | Open-Closed Principle: base handler + channel adapters | Architecture | COVERED | Conversational AI Rules section |
| AD-093 | Session-based conversation management | Session | COVERED | Conversational AI Rules section |
| AD-094 | 30-minute session timeout | Session | COVERED | Conversational AI Rules section |
| AD-095 | Invokes AI Model for LLM processing (no direct LLM calls) | Integration | COVERED | Conversational AI Anti-Patterns |
| AD-096 | Uses existing MCP servers for data retrieval | Data Access | COVERED | Conversational AI Rules section |
| AD-097 | Hands off final delivery to Notification Model | Delivery | COVERED | Conversational AI Anti-Patterns |
| AD-098 | Does NOT expose own MCP server | MCP | COVERED | Conversational AI Rules section |
| AD-099 | MongoDB collections: sessions, conversation_history, channel_configs | Storage | COVERED | MongoDB Collection Ownership |

## Engagement Model Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-100 | Engagement Model is 9th Domain Model (farmer motivation engine) | Overview | COVERED | Domain Model Boundaries table |
| AD-101 | Duolingo-style encouragement patterns adapted for farmers | UX | COVERED | engagement-model-architecture.md |
| AD-102 | Streaks based on weekly collection cycles, not daily | Business | COVERED | Core Concepts section |
| AD-103 | Streak freeze (1/month + weather bonus) for compassion | Business | COVERED | Streak Freeze section |
| AD-104 | 5-level progression: Newcomer → Learner → Practitioner → Expert → Master | Gamification | COVERED | Level Progression section |
| AD-105 | NO leaderboards (farmers not competing) | Anti-Pattern | COVERED | Anti-Patterns Avoided table |
| AD-106 | NO points system (use real quality metrics instead) | Anti-Pattern | COVERED | Anti-Patterns Avoided table |
| AD-107 | 5-state motivation machine: THRIVING → STEADY → AT_RISK → DECLINING → RECOVERING | State | COVERED | Motivation State Machine section |
| AD-108 | Consumes plantation.performance_updated (not raw collection events) | Events | COVERED | Event Integration section |
| AD-109 | Exposes MCP server for Action Plan personalization | MCP | COVERED | MCP Server Tools section |
| AD-110 | Factory-configurable quality thresholds (tier_1/tier_2/tier_3) | Config | COVERED | Plantation stores neutral thresholds; Engagement maps to WIN/WATCH/WORK/WARN; UI shows Premium/Standard/Acceptable |
| AD-111 | MongoDB collections: engagement_state, milestones, celebrations | Storage | COVERED | MongoDB Collection Ownership |

## Cross-Cutting Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-060 | All inter-model communication via DAPR Pub/Sub | Communication | COVERED | DAPR Communication Rules |
| AD-061 | No direct database access across models | Communication | COVERED | Cross-Model Communication |
| AD-062 | MCP servers for data retrieval between models | Communication | COVERED | MCP Server Rules |
| AD-063 | gRPC via DAPR for inter-model calls | Communication | COVERED | DAPR Communication Rules |
| AD-064 | DAPR Jobs for scheduling (not cron) | Scheduling | COVERED | Anti-Patterns section |
| AD-065 | DAPR Secret Store for credentials | Secrets | COVERED | Anti-Patterns section |
| AD-066 | MongoDB (managed: Atlas/CosmosDB) | Infrastructure | COVERED | Technology Stack table |
| AD-067 | Pinecone for vector database | Infrastructure | COVERED | Technology Stack table |
| AD-068 | Azure Blob Storage for raw documents | Infrastructure | GAP | Not in project-context |
| AD-069 | OpenTelemetry via DAPR | Observability | COVERED | Version Constraints |
| AD-075 | Grading Model is fully configurable (not hardcoded A/B/C/D) | Grading | COVERED | Grading Model Flexibility section |
| AD-076 | Grades computed from weighted attributes defined in Grading Model | Grading | COVERED | Grading Model Flexibility section |
| AD-077 | Use semantic categories or thresholds for triggers, not grade labels | Grading | COVERED | Grading Model Flexibility section |

## Kubernetes Deployment Decisions

| ID | Decision | Section | In Context? | Notes |
|----|----------|---------|-------------|-------|
| AD-070 | Single namespace per environment | Deployment | COVERED | Deployment section |
| AD-071 | BFF pattern (REST+WebSocket external, gRPC internal) | Deployment | COVERED | FastAPI/BFF Rules |
| AD-072 | ConfigMaps for environment settings | Deployment | COVERED | Deployment section |
| AD-073 | MCP servers as separate scalable pods | Deployment | GAP | Implementation detail |

---

## Gap Analysis Summary

### HIGH PRIORITY GAPS - ALL RESOLVED

All high-priority gaps have been added to `project-context.md`:

| ID | Decision | Status |
|----|----------|--------|
| AD-002 | Trust provided IDs on ingest | RESOLVED - Data Ingestion Rules |
| AD-003 | Store validation failures with warnings | RESOLVED - Data Ingestion Rules |
| AD-034 | Message delivery is separate infrastructure | RESOLVED - Domain Model Boundaries |
| AD-045 | Triggering is domain model responsibility | RESOLVED - Triggering Responsibility |

### MEDIUM PRIORITY GAPS - ALL RESOLVED

All medium-priority gaps have been added to `project-context.md`:

| ID | Decision | Status |
|----|----------|--------|
| AD-016 | Weather lag correlation (3-7 days) | RESOLVED - Weather Correlation Pattern |
| AD-018 | Triage feedback loop | RESOLVED - Triage Feedback Loop |
| AD-021 | Regions by county + altitude band | RESOLVED - Region Definition |
| AD-022 | Weather per region (cost optimization) | RESOLVED - Region Definition |
| AD-024 | Google Elevation API | RESOLVED - Region Definition |
| AD-025 | Flush calendar per region | RESOLVED - Region Definition |
| AD-035 | Tiered SMS strategy | RESOLVED - SMS Cost Optimization |
| AD-036 | Two-way SMS with keywords | RESOLVED - SMS Cost Optimization |

### LOW PRIORITY GAPS (Implementation details)

| ID | Decision | Risk |
|----|----------|------|
| AD-023 | Hybrid performance summaries | Detail can be referenced when needed |
| AD-031 | Two-Agent Pattern (Selector + Generator) | Detail can be referenced when needed |
| AD-037 | Message delivery retry with escalation | Infrastructure detail |
| AD-038 | Group messaging tiers | Feature detail |
| AD-044 | Agent instances in YAML | Detail can be referenced when needed |
| AD-068 | Azure Blob Storage for raw documents | Infrastructure detail |
| AD-073 | MCP servers as separate scalable pods | Deployment detail |

---

## Recommendations

1. **All critical gaps resolved** - project-context.md now covers all high and medium priority decisions
2. **Keep as reference** - Low priority gaps are implementation details that agents can look up when needed
3. **Periodic review** - Update this index when architecture.md changes

---

_Generated: 2025-12-17_
_Updated: 2025-12-20 - Added Notification Model (AD-080-088) and Conversational AI Model (AD-090-099) decisions; Updated agent types to 4_
_Source: architecture.md (as of commit b0e6a62)_