# Tests

Cross-service test suite for Farmer Power Platform.

## Directory Structure

```
tests/
├── conftest.py              # Core fixtures (ALWAYS import from here)
├── unit/                    # Per-domain-model unit tests
│   ├── collection/
│   ├── plantation/
│   ├── knowledge/
│   ├── action_plan/
│   ├── notification/
│   ├── market_analysis/
│   ├── ai_model/
│   └── conversational_ai/
├── integration/             # Cross-model integration tests
├── golden/                  # Golden sample tests (CRITICAL for AI)
│   ├── framework.py
│   ├── qc-event-extractor/
│   ├── quality-triage/
│   ├── disease-diagnosis/
│   └── ...
├── contracts/               # DAPR event and MCP contract tests
└── fixtures/
    ├── llm_responses/       # Recorded LLM responses
    ├── mongodb_data/        # Test data fixtures
    └── external_api_mocks/  # External API mocks
```

## Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Golden sample tests (AI accuracy)
pytest tests/ -m golden

# Integration tests
pytest tests/ -m integration

# Skip slow tests
pytest tests/ -m "not slow"

# With coverage
pytest tests/ --cov=src
```

## Test Markers

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.unit` | Fast, isolated unit tests |
| `@pytest.mark.integration` | Cross-model tests |
| `@pytest.mark.golden` | Golden sample accuracy tests |
| `@pytest.mark.contract` | Schema validation tests |
| `@pytest.mark.slow` | Slow tests (skip in CI fast mode) |

## Core Fixtures (conftest.py)

| Fixture | Purpose |
|---------|---------|
| `mock_dapr_client` | Mock DAPR service invocation & pub/sub |
| `mock_llm_client` | Mock OpenRouter with record/replay |
| `mock_mongodb_client` | In-memory MongoDB mock |
| `mock_collection_mcp` | Mock Collection MCP tools |
| `mock_plantation_mcp` | Mock Plantation MCP tools |
| `test_data_factory` | Factory for test data |
| `golden_sample_loader` | Load golden samples |

## Golden Sample Requirements

| Agent | Minimum Samples |
|-------|-----------------|
| qc_event_extractor | 100+ |
| quality_triage | 100+ |
| disease_diagnosis | 50+ |
| weather_impact_analyzer | 30+ |
| action_plan_generator | 20+ |

See `_bmad-output/test-design-system-level.md` for full test strategy.
