# BFF Service

Backend for Frontend (BFF) service for the Farmer Power Platform.

## Overview

The BFF is a REST API gateway that provides optimized endpoints for frontend React applications. It aggregates data from backend microservices (Plantation Model, Collection Model) via DAPR service invocation.

## Architecture

- **Port 8080**: FastAPI REST API
- **DAPR Sidecar**: Handles service-to-service communication with backend models

## Endpoints

- `GET /health` - Health check endpoint for Kubernetes liveness probes
- `GET /ready` - Readiness check endpoint for Kubernetes readiness probes

## Development

```bash
# Install dependencies
poetry install

# Run locally
uvicorn bff.main:app --host 0.0.0.0 --port 8080

# Run tests
pytest tests/
```

## Configuration

Environment variables:
- `APP_ENV`: Application environment (development, test, production)
- `AUTH_PROVIDER`: Authentication provider (mock, azure-ad-b2c)
- `DAPR_GRPC_PORT`: DAPR sidecar gRPC port (default: 50001)
- `OTEL_ENDPOINT`: OpenTelemetry collector endpoint
