# 2. Project Structure

## Directory Layout

```
ai-model/
├── src/
│   ├── agents/
│   │   ├── types/                    # Agent type implementations (code)
│   │   │   ├── extractor/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chain.py          # LangChain implementation
│   │   │   │   └── nodes.py          # Reusable node functions
│   │   │   ├── explorer/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── graph.py          # LangGraph implementation
│   │   │   │   ├── nodes.py
│   │   │   │   └── state.py          # State type definitions
│   │   │   ├── generator/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── graph.py
│   │   │   │   ├── nodes.py
│   │   │   │   └── state.py
│   │   │   └── conversational/
│   │   │       ├── __init__.py
│   │   │       ├── graph.py          # LangGraph for multi-turn dialogue
│   │   │       ├── nodes.py
│   │   │       ├── state.py
│   │   │       └── adapters/         # Channel adapters (voice, whatsapp, sms)
│   │   │           ├── __init__.py
│   │   │           ├── base.py
│   │   │           ├── voice_chatbot.py
│   │   │           ├── whatsapp.py
│   │   │           └── sms.py
│   │   │
│   │   └── instances/                # Agent instance configs (YAML)
│   │       ├── extractors/
│   │       │   └── qc-event-extractor.yaml
│   │       ├── explorers/
│   │       │   ├── disease-diagnosis.yaml
│   │       │   ├── weather-impact.yaml
│   │       │   └── trend-analysis.yaml
│   │       └── generators/
│   │           └── weekly-action-plan.yaml
│   │
│   ├── prompts/                      # Prompt source files (Git-versioned)
│   │   │                             # NOTE: Deployed to MongoDB, not read from disk at runtime
│   │   ├── extractors/
│   │   │   └── qc-event/
│   │   │       ├── prompt.yaml       # Combined prompt definition
│   │   │       └── examples.yaml     # Few-shot examples
│   │   ├── explorers/
│   │   │   ├── disease-diagnosis/
│   │   │   │   ├── prompt.yaml
│   │   │   │   └── examples.yaml
│   │   │   └── weather-impact/
│   │   │       ├── prompt.yaml
│   │   │       └── examples.yaml
│   │   └── generators/
│   │       └── action-plan/
│   │           ├── prompt.yaml
│   │           └── examples.yaml
│   │
│   ├── llm/                          # LLM Gateway
│   │   ├── __init__.py
│   │   ├── gateway.py                # OpenRouter client
│   │   ├── routing.py                # Model routing logic
│   │   └── cost_tracker.py
│   │
│   ├── rag/                          # RAG Engine
│   │   ├── __init__.py
│   │   ├── engine.py                 # Pinecone client
│   │   ├── embeddings.py
│   │   └── knowledge_domains.py
│   │
│   ├── mcp/                          # MCP Clients
│   │   ├── __init__.py
│   │   ├── collection_client.py
│   │   ├── plantation_client.py
│   │   └── knowledge_client.py
│   │
│   ├── events/                       # DAPR Event Handling
│   │   ├── __init__.py
│   │   ├── subscriber.py             # Event subscription
│   │   ├── publisher.py              # Result publishing
│   │   └── schemas.py                # Event payload schemas
│   │
│   └── core/                         # Core utilities
│       ├── __init__.py
│       ├── config.py                 # Configuration loading
│       ├── errors.py                 # Error types
│       └── tracing.py                # OpenTelemetry setup
│
├── config/
│   ├── llm-gateway.yaml              # OpenRouter config
│   ├── rag-engine.yaml               # Pinecone config
│   └── dapr/
│       ├── pubsub.yaml
│       └── jobs.yaml
│
├── tests/
│   ├── unit/
│   │   ├── agents/
│   │   ├── llm/
│   │   └── rag/
│   ├── integration/
│   │   ├── mcp/
│   │   └── events/
│   └── golden_samples/               # Golden sample test data
│       ├── extractors/
│       │   └── qc-event/
│       │       ├── input_001.json
│       │       └── expected_001.json
│       └── explorers/
│           └── disease-diagnosis/
│               ├── input_001.json
│               └── expected_001.json
│
└── docs/
    └── prompts/                      # Prompt documentation
        └── guidelines.md
```

## Naming Conventions

| Element              | Convention                | Example                   |
|----------------------|---------------------------|---------------------------|
| Agent type directory | lowercase, singular       | `extractor/`, `explorer/` |
| Agent instance file  | kebab-case                | `disease-diagnosis.yaml`  |
| Prompt directory     | kebab-case, matches agent | `disease-diagnosis/`      |
| Python modules       | snake_case                | `cost_tracker.py`         |
| Classes              | PascalCase                | `ExplorerState`           |
| Functions            | snake_case                | `fetch_document_node`     |
| Constants            | UPPER_SNAKE_CASE          | `MAX_RETRY_ATTEMPTS`      |

---
