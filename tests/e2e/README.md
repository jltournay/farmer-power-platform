# E2E Infrastructure Testing

End-to-end tests for the Farmer Power Platform that validate the full stack deployment with real services.

## Overview

These tests deploy all 4 existing modules (plantation-model, plantation-mcp, collection-model, collection-mcp) in Docker containers with real dependencies:

- **MongoDB** - Real database
- **Redis** - DAPR state/pubsub backend
- **Azurite** - Azure Blob Storage emulator
- **Google Elevation Mock** - Deterministic altitude responses
- **DAPR Sidecars** - Real inter-service communication

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Python 3.11+ (3.12 recommended)
- pytest, pytest-asyncio, httpx, grpcio, azure-storage-blob, motor

## Quick Start

### 1. Start the E2E Stack

```bash
# From repository root
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

# Wait for all services to be healthy
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

### 2. Run Infrastructure Verification Tests

```bash
# Run all E2E tests
pytest tests/e2e/scenarios/ -v --tb=short

# Run only infrastructure verification
pytest tests/e2e/scenarios/test_00_infrastructure_verification.py -v
```

### 3. Stop the Stack

```bash
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

## Directory Structure

```
tests/e2e/
├── conftest.py                       # E2E fixtures (clients, seed data)
├── pytest.ini                        # pytest-asyncio configuration
├── infrastructure/
│   ├── docker-compose.e2e.yaml       # Full stack definition
│   ├── dapr-components/
│   │   ├── pubsub.yaml               # Redis pubsub
│   │   └── statestore.yaml           # Redis state store
│   ├── mock-servers/
│   │   └── google-elevation/
│   │       ├── Dockerfile
│   │       └── server.py             # Returns deterministic altitudes
│   └── seed/
│       ├── grading_models.json       # Pre-loaded grading models (TBK, KTDA)
│       ├── regions.json              # Pre-loaded regions (5 test regions)
│       └── source_configs.json       # Collection Model ingestion configs
├── scenarios/
│   └── test_00_infrastructure_verification.py  # Infrastructure tests
└── helpers/
    ├── api_clients.py                # HTTP clients for APIs
    ├── mcp_clients.py                # gRPC clients for MCP
    ├── azure_blob.py                 # Azurite client
    ├── mongodb_direct.py             # Direct DB verification
    └── cleanup.py                    # Data cleanup utilities
```

## Infrastructure Verification Tests

The `test_00_infrastructure_verification.py` validates all components before running functional tests:

| Test Class | Tests | What It Verifies |
|------------|-------|------------------|
| `TestHTTPEndpoints` | 4 | Plantation & Collection Model health/ready endpoints |
| `TestMCPEndpoints` | 2 | Plantation MCP (9 tools), Collection MCP (5 tools) |
| `TestMongoDB` | 3 | Connection, plantation_e2e, collection_e2e databases |
| `TestAzurite` | 3 | Connection, create container, upload/download |
| `TestDAPRPubSub` | 2 | Both services healthy with DAPR sidecars |
| `TestSeedData` | 4 | Grading models, regions, source configs loaded |
| `TestInfrastructureSummary` | 1 | All components verified together |

**Total: 19 tests**

## Service Ports

| Service | Host Port | Container Port | Description |
|---------|-----------|----------------|-------------|
| MongoDB | 27017 | 27017 | Database |
| Redis | **6380** | 6379 | DAPR backend (avoids local Redis conflict) |
| Azurite | 10000-10002 | 10000-10002 | Blob/Queue/Table storage |
| Google Elevation Mock | 8080 | 8080 | Altitude API |
| Plantation Model | 8001 | 8000 | HTTP API |
| Plantation Model gRPC | 50051 | 50051 | gRPC API |
| Collection Model | 8002 | 8000 | HTTP API |
| Plantation MCP | 50052 | 50051 | gRPC MCP Server |
| Collection MCP | 50053 | 50051 | gRPC MCP Server |

## Seed Data

Located in `infrastructure/seed/`:

### grading_models.json
- **TBK** (Tobacco Kenya): Primary (50%, 3pts), Secondary (50%, 2pts)
- **KTDA** (Kenya Tea Development Agency): Grade A (33%, 3pts), Grade B (33%, 2pts), Rejected (34%, 0pts)

### regions.json
5 test regions with varying altitudes and coordinates:
- `region-highlands-001` (High altitude, 1500m)
- `region-midlands-001` (Medium altitude, 1000m)
- `region-lowlands-001` (Low altitude, 500m)
- `region-coastal-001` (Sea level, 50m)
- `region-valley-001` (Low altitude, 400m)

### source_configs.json
Collection Model ingestion configurations:
- `quality-events-e2e` container for quality data ingestion
- `weather-data-e2e` container for weather data ingestion

## Google Elevation Mock

The mock server returns deterministic altitudes based on latitude:

| Latitude Range | Altitude | Band |
|---------------|----------|------|
| < 0.5 | 600m | Low |
| 0.5 - 1.0 | 1000m | Medium |
| > 1.0 | 1400m | High |

This allows predictable testing of altitude-band assignment.

## Service Architecture

### Plantation Model
- **HTTP**: Only `/health` and `/ready` (Kubernetes probes) + DAPR event handlers
- **gRPC**: All data operations (factories, farmers, regions, grading models)
- **MCP**: Exposes gRPC operations as MCP tools via Plantation MCP Server

### Collection Model
- **HTTP**: `/health`, `/ready`, blob event trigger, job trigger
- **gRPC**: None (event-driven ingestion only)
- **MCP**: Document queries and blob SAS URL generation via Collection MCP Server

## Fixtures Available

| Fixture | Description |
|---------|-------------|
| `e2e_config` | Configuration dictionary with URLs and connection strings |
| `plantation_api` | HTTP client for health/ready endpoints only |
| `collection_api` | HTTP client for health/ready + event triggers |
| `plantation_mcp` | **gRPC MCP client** - use for farmer/factory/region operations |
| `collection_mcp` | **gRPC MCP client** - use for document queries |
| `mongodb_direct` | Direct MongoDB access for verification |
| `azurite_client` | Azurite blob storage client |
| `seed_data` | Pre-loaded test data (grading models, regions, source configs) |
| `wait_for_services` | Waits for services to be healthy |

**Important**: To create/query farmers, factories, regions, use `plantation_mcp` (MCP gRPC client), NOT `plantation_api` (HTTP client).

## Adding New Tests

1. Create a new test file in `tests/e2e/scenarios/`
2. Use `@pytest.mark.e2e` marker
3. Use fixtures from `conftest.py`

Example:
```python
import pytest

@pytest.mark.e2e
class TestMyNewFlow:
    @pytest.mark.asyncio
    async def test_my_scenario(
        self,
        plantation_api,      # HTTP client - health/ready only
        plantation_mcp,      # gRPC MCP client - data operations
        mongodb_direct,
        seed_data,
    ):
        # Verify service is healthy (HTTP)
        health = await plantation_api.health()
        assert health["status"] == "healthy"

        # List MCP tools available (gRPC)
        tools = await plantation_mcp.list_tools()
        assert len(tools) > 0

        # Query farmers via MCP (gRPC)
        result = await plantation_mcp.search_farmers(limit=10)
        # result contains tool response

        # Verify directly in database
        count = await mongodb_direct.plantation_db.regions.count_documents({})
        assert count >= 1
```

## Troubleshooting

### Port Conflicts

If you see "port is already allocated" errors:
```bash
# Check what's using the port
lsof -i :6379  # Local Redis
lsof -i :27017 # Local MongoDB

# The E2E stack uses port 6380 for Redis to avoid conflicts
```

### Services not starting
```bash
# Check service logs
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs

# Check specific service
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs plantation-model
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs plantation-mcp
```

### Azurite API Version Error
If you see "API version not supported" errors, ensure the Azurite command includes `--skipApiVersionCheck`:
```yaml
command: "azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --loose --skipApiVersionCheck"
```

### Connection refused errors
```bash
# Verify services are running and healthy
docker ps --filter "name=e2e-" --format "{{.Names}}: {{.Status}}"

# Check health endpoints
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### gRPC connection issues
```bash
# Verify MCP servers are running
docker logs e2e-plantation-mcp
docker logs e2e-collection-mcp

# Test gRPC connectivity (requires grpcurl)
grpcurl -plaintext localhost:50052 list
grpcurl -plaintext localhost:50053 list
```

### Event Loop Errors in Tests
If you see "Event loop is closed" errors, ensure:
1. `tests/e2e/pytest.ini` has `asyncio_default_fixture_loop_scope = function`
2. All fixtures use `@pytest_asyncio.fixture` (not `@pytest.fixture`)
3. Fixtures are function-scoped (not session-scoped)

## Clean Rebuild

To completely rebuild the E2E stack:
```bash
# Stop and remove all containers and volumes
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v

# Rebuild without cache
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build --no-cache

# Start fresh
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
```
