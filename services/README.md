# Services

Microservices implementing the 8 domain models + supporting services.

## Domain Model Services

| Service | Description | Port |
|---------|-------------|------|
| `collection-model/` | Quality data ingestion and document storage | 50051 |
| `plantation-model/` | Farmer/factory digital twin management | 50052 |
| `knowledge-model/` | Quality diagnosis and analysis | 50053 |
| `action-plan-model/` | Recommendation generation | 50054 |
| `notification-model/` | SMS, WhatsApp, Voice IVR delivery | 50055 |
| `market-analysis-model/` | Buyer profiles and lot matching | 50056 |
| `ai-model/` | LLM agent orchestration | 50057 |
| `conversational-ai/` | Two-way dialogue (voice chatbot, text chat) | 50058 |

## Supporting Services

| Service | Description | Port |
|---------|-------------|------|
| `bff/` | Backend-for-Frontend (external REST API) | 8080 |
| `inbound-webhook/` | External webhook receiver | 8081 |

## Service Template

Each service follows this structure:

```
services/{service-name}/
├── src/{service_name}/      # Python package (snake_case)
│   ├── main.py              # Entrypoint
│   ├── config.py            # Configuration
│   ├── api/                 # gRPC/REST handlers
│   ├── domain/              # Business logic
│   └── infrastructure/      # MongoDB, DAPR, external APIs
├── tests/                   # Service-specific tests
├── Dockerfile
└── pyproject.toml
```

## Naming Conventions

- Service folder: `kebab-case` (collection-model)
- Python package: `snake_case` (collection_model)
- gRPC service: `PascalCase` (CollectionService)

See `_bmad-output/architecture/repository-structure.md` for details.
