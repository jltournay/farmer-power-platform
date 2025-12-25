# Story 0.2: MongoDB Integration Testing Infrastructure

**Status:** ready-for-dev

---

## Story

As a **developer**,
I want a local MongoDB integration testing infrastructure,
So that I can catch database integration issues early in the development cycle rather than discovering them in production.

---

## Context

**From Epic 1 Retrospective:**
- Story 1-4 deferred 4 MongoDB integration tests (Task 9)
- Current "integration" tests in `tests/integration/` use mocked MongoDB
- User feedback: "if the integration with MongoDB doesn't work, maybe it's better to see that early in the project"

**Problem:**
- Repository tests use `MagicMock` for MongoDB, not actual Motor/MongoDB operations
- No validation that async Motor operations work correctly
- Index creation, query patterns, and data serialization untested against real MongoDB

---

## Acceptance Criteria

1. **Given** a developer runs integration tests locally
   **When** the test suite starts
   **Then** a local MongoDB container is automatically started via docker-compose or testcontainers

2. **Given** the MongoDB test container is running
   **When** repository tests execute
   **Then** they perform real CRUD operations against the actual MongoDB instance

3. **Given** Story 1-4 deferred integration tests
   **When** this story is complete
   **Then** all 3 deferred tests pass:
   - Grading model creation and retrieval flow
   - Farmer registration creates performance record with correct grading_model_id
   - GetFarmerSummary returns complete performance data

4. **Given** the test suite completes
   **When** cleanup runs
   **Then** the MongoDB container is stopped and test data is removed

5. **Given** integration tests exist
   **When** they are run in CI
   **Then** they pass reliably without flaky failures

---

## Tasks / Subtasks

- [ ] **Task 1: Set up MongoDB test infrastructure** (AC: #1, #4)
  - [ ] 1.1 Add `docker-compose.test.yaml` with MongoDB service (mongo:7.0)
  - [ ] 1.2 Create `tests/conftest_integration.py` with MongoDB fixture
  - [ ] 1.3 Implement async fixture that connects to MongoDB and cleans up
  - [ ] 1.4 Add pytest marker `@pytest.mark.mongodb` for real MongoDB tests
  - [ ] 1.5 Create helper to wait for MongoDB readiness

- [ ] **Task 2: Create base test utilities** (AC: #2)
  - [ ] 2.1 Add `libs/fp-testing/fp_testing/mongodb.py` with test utilities
  - [ ] 2.2 Create `MongoTestClient` class with async context manager
  - [ ] 2.3 Add `create_test_database()` that creates unique DB per test run
  - [ ] 2.4 Add `cleanup_test_database()` to drop test databases

- [ ] **Task 3: Implement Story 1-4 deferred tests** (AC: #3)
  - [ ] 3.1 Create `tests/integration/test_grading_model_mongodb.py`
  - [ ] 3.2 Test grading model creation persists to MongoDB correctly
  - [ ] 3.3 Test grading model retrieval returns correct data types
  - [ ] 3.4 Test factory grading model lookup works with indexes
  - [ ] 3.5 Create `tests/integration/test_farmer_performance_mongodb.py`
  - [ ] 3.6 Test farmer registration auto-creates performance record
  - [ ] 3.7 Test performance record has correct grading_model_id reference
  - [ ] 3.8 Test GetFarmerSummary returns complete performance data
  - [ ] 3.9 Test FarmerPerformance upsert operations

- [ ] **Task 4: Validate repository operations** (AC: #2)
  - [ ] 4.1 Test GradingModelRepository with real MongoDB
  - [ ] 4.2 Test FarmerPerformanceRepository with real MongoDB
  - [ ] 4.3 Test FarmerRepository with real MongoDB
  - [ ] 4.4 Test index creation happens correctly
  - [ ] 4.5 Test unique constraints work (duplicate phone rejection)

- [ ] **Task 5: CI pipeline integration** (AC: #5)
  - [ ] 5.1 Add MongoDB service to GitHub Actions workflow
  - [ ] 5.2 Create separate test stage for integration tests
  - [ ] 5.3 Add retry logic for MongoDB connection in CI
  - [ ] 5.4 Document how to run integration tests locally

- [ ] **Task 6: Update Story 1-4 status** (AC: #3)
  - [ ] 6.1 Mark Task 9 as complete in story 1-4 file
  - [ ] 6.2 Update sprint-status.yaml if needed

---

## Dev Notes

### Test Infrastructure Location

```
tests/
├── conftest.py                    # Existing - shared fixtures
├── conftest_integration.py        # NEW - MongoDB fixtures
├── docker-compose.test.yaml       # NEW - Test services
├── integration/
│   ├── test_grading_model_mongodb.py    # NEW
│   ├── test_farmer_performance_mongodb.py # NEW
│   └── ...
libs/fp-testing/
└── fp_testing/
    ├── __init__.py
    ├── fixtures.py               # Existing
    └── mongodb.py                # NEW - MongoDB test utilities
```

### Docker Compose for Tests

```yaml
# tests/docker-compose.test.yaml
services:
  mongodb-test:
    image: mongo:7.0
    ports:
      - "27018:27017"  # Different port to avoid conflicts
    environment:
      MONGO_INITDB_DATABASE: test_plantation
    tmpfs:
      - /data/db  # RAM disk for speed
```

### MongoDB Test Fixture Pattern

```python
# tests/conftest_integration.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture(scope="session")
async def mongodb_client():
    """Session-scoped MongoDB client."""
    client = AsyncIOMotorClient("mongodb://localhost:27018")
    await client.admin.command("ping")  # Wait for ready
    yield client
    client.close()

@pytest.fixture
async def test_db(mongodb_client):
    """Function-scoped test database with cleanup."""
    import uuid
    db_name = f"test_{uuid.uuid4().hex[:8]}"
    db = mongodb_client[db_name]
    yield db
    await mongodb_client.drop_database(db_name)
```

### Example Integration Test

```python
# tests/integration/test_grading_model_mongodb.py
import pytest
from plantation_model.domain.models.grading_model import GradingModel
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)

@pytest.mark.mongodb
@pytest.mark.asyncio
async def test_grading_model_roundtrip(test_db):
    """Test grading model can be created and retrieved."""
    repo = GradingModelRepository(test_db)

    model = GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="1.0.0",
        grading_type="TERNARY",
        # ... full model data
    )

    # Create
    created = await repo.create(model)
    assert created.model_id == "tbk_kenya_tea_v1"

    # Retrieve
    retrieved = await repo.get_by_id("tbk_kenya_tea_v1", "1.0.0")
    assert retrieved is not None
    assert retrieved.grading_type == "TERNARY"
```

### Running Integration Tests

```bash
# Start MongoDB
docker-compose -f tests/docker-compose.test.yaml up -d

# Run integration tests only
PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing" \
  pytest tests/integration/ -m mongodb -v

# Cleanup
docker-compose -f tests/docker-compose.test.yaml down
```

### GitHub Actions Integration

```yaml
# .github/workflows/ci.yaml (addition)
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27018:27017
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: |
          pytest tests/integration/ -m mongodb -v
```

---

## Technical Decisions

1. **MongoDB 7.0** - Latest stable version, matches production target
2. **Port 27018** - Avoids conflict with local development MongoDB on 27017
3. **tmpfs** - RAM disk for test database improves speed
4. **Unique DB per test** - Ensures test isolation, prevents data leakage
5. **Session-scoped client** - Reuses connection, function-scoped DB for isolation

---

## Out of Scope

- Full testcontainers setup (docker-compose is simpler for now)
- Redis integration tests (not needed yet)
- Performance/load testing

---

## References

- Epic 1 Retrospective: `_bmad-output/sprint-artifacts/epic-1-retrospective.md`
- Story 1-4: `_bmad-output/sprint-artifacts/1-4-farmer-performance-history-structure.md` (Task 9)
- fp-testing library: `libs/fp-testing/`
