# AI Model Service

Agent orchestration and LLM gateway for the Farmer Power Platform.

## Overview

The AI Model service provides:
- **LLM Gateway**: Centralized access to language models via OpenRouter
- **Agent Orchestration**: Coordinates AI agents (Extractor, Explorer, Generator, Conversational)
- **Prompt Management**: Stores and versions prompts in MongoDB
- **RAG Pipeline**: Document ingestion, embedding, and retrieval (future stories)

## Architecture (ADR-011)

Two-port service architecture:

| Port | Purpose | Protocol |
|------|---------|----------|
| **8000** | FastAPI health endpoints (`/health`, `/ready`) | HTTP |
| **50051** | gRPC API server (via DAPR sidecar) | gRPC |

## Quick Start

### Local Development

```bash
# From repository root
cd services/ai-model

# Install dependencies
poetry install

# Set environment variables
export AI_MODEL_MONGODB_URI=mongodb://localhost:27017
export AI_MODEL_MONGODB_DATABASE=ai_model

# Run the service
poetry run uvicorn ai_model.main:app --reload --port 8000
```

### With Docker

```bash
# From repository root
docker build -f services/ai-model/Dockerfile -t farmer-power/ai-model .
docker run -p 8000:8000 -p 50051:50051 farmer-power/ai-model
```

## API Endpoints

### Health Endpoints (HTTP)

- `GET /health` - Liveness probe (always returns 200)
- `GET /ready` - Readiness probe (checks MongoDB connection)

### gRPC Services

- `AiModelService.Extract` - Extract structured data using LLM
- `AiModelService.HealthCheck` - gRPC health check

## Configuration

Environment variables (prefix: `AI_MODEL_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `ai-model` | Service identifier |
| `SERVICE_VERSION` | `0.1.0` | Service version |
| `HOST` | `0.0.0.0` | HTTP server bind address |
| `PORT` | `8000` | HTTP server port |
| `GRPC_PORT` | `50051` | gRPC server port |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | `ai_model` | MongoDB database name |
| `DAPR_HOST` | `localhost` | DAPR sidecar host |
| `DAPR_HTTP_PORT` | `3500` | DAPR HTTP port |
| `DAPR_GRPC_PORT` | `50001` | DAPR gRPC port |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_ENDPOINT` | `http://localhost:4317` | OTLP exporter endpoint |

## Development

### Running Tests

```bash
# From repository root
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-proto/src" \
  pytest tests/unit/ai_model/ -v
```

### Linting

```bash
ruff check services/ai-model/
ruff format --check services/ai-model/
```

## Related Stories

- **Story 0.75.1**: This story - Service scaffold
- **Story 0.75.2**: Prompt storage with versioning
- **Story 0.75.3**: Agent configuration storage
- **Story 0.75.5**: OpenRouter LLM gateway
- **Story 0.75.8**: DAPR event pub/sub

## References

- [Architecture: AI Model](/_bmad-output/architecture/ai-model-architecture/index.md)
- [ADR-011: Service Architecture](/_bmad-output/architecture/adr/ADR-011-service-architecture-grpc-fastapi-dapr.md)
- [Epic 0.75: AI Model Foundation](/_bmad-output/epics/epic-0-75-ai-model.md)
