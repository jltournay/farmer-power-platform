# Shared Libraries

Internal Python packages shared across services.

## Libraries

| Library | Purpose | Usage |
|---------|---------|-------|
| `fp-common/` | Common utilities (config, tracing, DAPR client) | All services |
| `fp-proto/` | Generated proto stubs | All services using gRPC |
| `fp-testing/` | Test utilities and fixtures | Test code only |

## Usage in Services

```toml
# In service's pyproject.toml
[tool.poetry.dependencies]
fp-common = { path = "../../libs/fp-common" }
fp-proto = { path = "../../libs/fp-proto" }

[tool.poetry.group.dev.dependencies]
fp-testing = { path = "../../libs/fp-testing" }
```

```python
# In code
from fp_common.config import load_config
from fp_common.dapr import DaprClient
from fp_proto.collection.v1 import collection_pb2
from fp_testing.fixtures import mock_dapr_client
```

## fp-common Structure

```
fp-common/fp_common/
├── config.py           # Configuration loading (Pydantic Settings)
├── errors.py           # Standard error types
├── tracing.py          # OpenTelemetry setup
├── logging.py          # Structured logging
├── dapr/               # DAPR client wrapper
└── health/             # Health check utilities
```

## fp-testing Structure

```
fp-testing/fp_testing/
├── fixtures.py         # Pytest fixtures
├── factories.py        # Factory Boy factories
├── golden/             # Golden sample framework
├── mocks/              # Mock implementations
└── assertions.py       # Custom assertions
```

See `_bmad-output/test-design-system-level.md` for testing details.
