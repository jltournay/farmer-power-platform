# Document Boundaries

> **This is the source of truth for HOW AI works.** Other domain model documents define WHAT and WHEN; this document defines HOW.

```
┌─────────────────────────────────────────────────────────────────────────┐
│              ARCHITECTURE DOCUMENT RESPONSIBILITIES                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  KNOWLEDGE MODEL ARCHITECTURE                                           │
│  ├── Owns: WHAT to diagnose, WHEN to trigger, WHERE to store results   │
│  ├── Owns: Business requirements for analysis outputs                   │
│  ├── Owns: MCP tools exposed to other models                           │
│  └── References: AI Model for agent implementation details              │
│                                                                         │
│  ACTION PLAN MODEL ARCHITECTURE                                         │
│  ├── Owns: WHAT to generate, WHEN to run (weekly), WHO receives        │
│  ├── Owns: Output formats (detailed report + farmer message)           │
│  ├── Owns: Translation/simplification requirements                      │
│  └── References: AI Model for generator implementation details          │
│                                                                         │
│  CONVERSATIONAL AI MODEL ARCHITECTURE                                   │
│  ├── Owns: Channel adapters (voice, WhatsApp, web chat)                │
│  ├── Owns: Persona configurations (tone, language, constraints)        │
│  ├── Owns: Session management, turn coordination                        │
│  ├── Owns: Intent handlers (plugin registry)                           │
│  └── References: AI Model for conversational agent implementation       │
│                                                                         │
│  AI MODEL ARCHITECTURE (this document)                                  │
│  ├── Owns: Agent types (5: Extractor, Explorer, Generator,             │
│  │         Conversational, Tiered-Vision)                              │
│  ├── Owns: Agent instance configurations (YAML specs)                  │
│  ├── Owns: LLM gateway configuration (OpenRouter, model routing)       │
│  ├── Owns: RAG engine (Pinecone, knowledge domains, versioning)        │
│  ├── Owns: Prompt management (MongoDB, A/B testing, lifecycle)         │
│  ├── Owns: LangGraph workflows (saga patterns, checkpointing)          │
│  ├── Owns: Tiered processing (vision cost optimization)                │
│  └── Owns: Observability (tracing, cost tracking)                      │
│                                                                         │
│  CROSS-REFERENCES:                                                      │
│  • Knowledge Model → AI Model: "Analyzer implementation in AI Model"   │
│  • Action Plan → AI Model: "Generator implementation in AI Model"      │
│  • Conversational → AI Model: "Conversational agent implementation"    │
│  • AI Model → Knowledge Model: "Business context for diagnosis agents" │
│  • AI Model → Action Plan: "Business context for generator agents"     │
│  • AI Model → Conversational: "Channel/persona context for dialogue"   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this separation matters:**
- **Avoid duplication:** Agent specs live in ONE place (here)
- **Clear ownership:** Business logic vs implementation logic
- **Easier maintenance:** Change prompts here, not in 3 documents
- **Reduced confusion:** Developers know where to look
