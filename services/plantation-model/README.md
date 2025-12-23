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

```bash
# Install dependencies
poetry install

# Run locally
poetry run uvicorn plantation_model.main:app --reload

# Run tests
poetry run pytest
```

## API Endpoints

- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe (includes MongoDB check)
- `gRPC :50051` - Internal service communication

## References

- [Architecture](_bmad-output/architecture/plantation-model-architecture.md)
- [Story File](_bmad-output/sprint-artifacts/1-1-plantation-model-service-setup.md)
