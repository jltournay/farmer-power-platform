# LangGraph Workflow Orchestration

The AI Model uses **LangGraph** for complex multi-step workflows that require:

- **Parallel execution** — Run multiple analyzers concurrently (e.g., disease + weather + technique)
- **Saga pattern** — Coordinate parallel branches with compensation on failure
- **Checkpointing** — Save state to MongoDB for long-running or resumable workflows
- **Conditional routing** — Triage results determine which analyzers to invoke

**Primary use case:** When triage confidence is low, the saga pattern orchestrates parallel analyzers and aggregates their findings into a unified diagnosis.

```
Triage (Haiku)
     │
     ├── confidence ≥ 0.8 → Single analyzer
     │
     └── confidence < 0.8 → Saga: parallel analyzers
                                  ├── Disease Analyzer
                                  ├── Weather Analyzer
                                  └── Technique Analyzer
                                           │
                                           ▼
                                    Aggregator (combine findings)
```

> **Implementation details:** See `ai-model-developer-guide/1-sdk-framework.md` § *LangGraph Saga Pattern* for workflow code, checkpointing configuration, and error compensation strategies.
