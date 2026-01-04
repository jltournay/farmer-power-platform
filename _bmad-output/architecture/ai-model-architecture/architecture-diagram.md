# Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI MODEL                                       │
│                   (6th Domain Model)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKFLOW ENGINE                               │   │
│  │                                                                  │   │
│  │  Agent Types (in code):                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │  EXTRACTOR  │  │  EXPLORER   │  │  GENERATOR  │              │   │
│  │  │             │  │             │  │             │              │   │
│  │  │ • Extract   │  │ • Analyze   │  │ • Create    │              │   │
│  │  │ • Validate  │  │ • Diagnose  │  │ • Translate │              │   │
│  │  │ • Normalize │  │ • Pattern   │  │ • Format    │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │  ┌───────────────────────────────────────────────┐              │   │
│  │  │  CONVERSATIONAL                               │              │   │
│  │  │                                               │              │   │
│  │  │ • Intent classify  • Dialogue respond        │              │   │
│  │  │ • Context manage   • Persona adapt           │              │   │
│  │  └───────────────────────────────────────────────┘              │   │
│  │                                                                  │   │
│  │  Agent Instances (YAML → MongoDB → Pydantic):                                  │   │
│  │  • qc-event-extractor                                            │   │
│  │  • quality-triage (fast cause classification)                    │   │
│  │  • disease-diagnosis                                             │   │
│  │  • weather-impact-analyzer                                       │   │
│  │  • technique-assessment                                          │   │
│  │  • trend-analyzer                                                │   │
│  │  • weekly-action-plan                                            │   │
│  │  • market-analyzer                                               │   │
│  │  • dialogue-responder (multi-turn conversation)                  │   │
│  │  • intent-classifier (fast intent detection)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│            ┌─────────────┴─────────────┐                                │
│            ▼                           ▼                                │
│  ┌──────────────────┐       ┌──────────────────────┐                   │
│  │   LLM GATEWAY    │       │     RAG ENGINE       │                   │
│  │                  │       │                      │                   │
│  │  • OpenRouter    │       │  ┌────────────────┐  │                   │
│  │  • Model routing │       │  │  Vector DB     │  │                   │
│  │  • Cost tracking │       │  │  (Pinecone)    │  │                   │
│  │  • Retry/fallback│       │  │                │  │                   │
│  │                  │       │  │  • Tea diseases│  │                   │
│  └──────────────────┘       │  │  • Best practices│ │                   │
│                             │  │  • Weather patterns│                   │
│                             │  │  • Regional knowledge                  │
│                             │  └────────────────┘  │                   │
│                             │                      │                   │
│                             │  Access: internal    │                   │
│                             │  Curation: Admin UI  │                   │
│                             └──────────────────────┘                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP CLIENTS (gRPC via DAPR)                   │   │
│  │  • Collection MCP (fetch documents)                              │   │
│  │  • Plantation MCP (fetch farmer context)                         │   │
│  │  • Knowledge MCP (fetch analyses)                                │   │
│  │                                                                  │   │
│  │  Protocol: gRPC (not JSON-RPC) - see infrastructure-decisions   │   │
│  │  Transport: DAPR service invocation                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Persistence: STATELESS (results published via events)                  │
│  MCP Server: NONE (domain models don't query AI Model)                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```
