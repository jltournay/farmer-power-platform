# Plantation Model Service

Master data registry for the Farmer Power Platform. Stores core entities (regions, farmers, factories), configuration (payment policies, grading model references), and pre-computed performance summaries.

## Status

**Story 1.1:** Complete (Service Setup)

## Structure

```
services/plantation-model/
├── src/plantation_model/
│   ├── api/           # REST and gRPC handlers
│   ├── domain/        # Business logic and models
│   └── infrastructure/ # MongoDB, DAPR, external APIs
├── tests/
├── Dockerfile
└── pyproject.toml
```

## Quick Start

### Local Development Setup

```bash
# From repository root, install shared libraries first
pip install -e libs/fp-proto

# Install this service in editable mode (required for IDE imports)
pip install -e services/plantation-model

# Or use Poetry from service directory
cd services/plantation-model
poetry install
```

### Run Locally

```bash
# Run the service (requires MongoDB running)
uvicorn plantation_model.main:app --reload --port 8000

# Or with Poetry
poetry run uvicorn plantation_model.main:app --reload
```

### Run Tests

```bash
pytest tests/unit/plantation/
```

### Run with Docker Compose

```bash
# From repository root - starts MongoDB, Redis, DAPR, and this service
docker-compose -f deploy/docker/docker-compose.yml up
```

## API Endpoints

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe (includes MongoDB check)
- `gRPC :50051` - Internal service communication

## References

- [Architecture](_bmad-output/architecture/plantation-model-architecture.md)
- [Story File](_bmad-output/sprint-artifacts/1-1-plantation-model-service-setup.md)
