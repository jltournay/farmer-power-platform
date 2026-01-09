# ADR-014: MongoDB Async Driver Migration (Motor → PyMongo Async)

**Status:** Accepted
**Date:** 2026-01-09
**Deciders:** Winston (Architect), Jeanlouistournay
**Related:** ADR-007 (Source Config Cache), ADR-013 (AI Model Configuration Cache)

> **Note:** Application is NOT in production. No backwards compatibility required.

## Context

### Motor Deprecation

MongoDB has announced the deprecation of **Motor** (the async MongoDB driver):

| Milestone | Date |
|-----------|------|
| Deprecation announced | May 14, 2025 |
| End of new features | May 14, 2025 |
| Bug fixes only | Until May 14, 2026 |
| Critical fixes only | Until May 14, 2027 |
| End of life | May 14, 2027 |

### PyMongo Native Async

PyMongo 4.8+ introduced **native async support** via `AsyncMongoClient`:

```python
# Old (Motor - deprecated)
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient(uri)

# New (PyMongo Async)
from pymongo import AsyncMongoClient
client = AsyncMongoClient(uri)
```

### Performance Comparison

| Benchmark | Motor | PyMongo Async | Improvement |
|-----------|-------|---------------|-------------|
| Find (single task) | 74 MB/s | 112 MB/s | **+52%** |
| Find (80 concurrent tasks) | 37 MB/s | 89 MB/s | **+141%** |
| Bulk Insert | 83 MB/s | 102 MB/s | **+24%** |
| Insert (unlimited tasks) | 120 MB/s | 164 MB/s | **+36%** |
| GridFS Download | 574 MB/s | 604 MB/s | +5% |
| GridFS Upload | 431 MB/s | 444 MB/s | +3% |

**Why PyMongo Async is faster:**
- Motor uses a **thread pool** for network operations (asyncio → thread → network)
- PyMongo Async uses **native asyncio** (asyncio → network directly)
- Performance gains are most significant under **high concurrency**

### Current Motor Usage in Project

| Service/Module | Files | Usage Pattern |
|----------------|-------|---------------|
| ai-model | 8+ | Repositories, checkpointing |
| collection-model | 5+ | Repositories, Change Streams, caching |
| plantation-model | 8+ | Repositories |
| collection-mcp | 2 | Document queries |
| fp-common | 2 | DLQ, Change Stream Cache base |
| fp-testing | 1 | Test fixtures |
| E2E tests | 1 | Direct MongoDB verification |
| Scripts | 3 | Config deployment |

**Total: ~35+ files using Motor**

### LangGraph Checkpointer Issue

The `langgraph-checkpoint-mongodb` package has two modes:

| Mode | Class | MongoDB Client | Status |
|------|-------|----------------|--------|
| Sync | `MongoDBSaver` | `pymongo.MongoClient` | ✅ Working |
| Async | `AsyncMongoDBSaver` | `pymongo.AsyncMongoClient` | ✅ Available in v0.3.0 |

Currently, we use the **sync** `MongoDBSaver` with a separate `MongoClient`, creating two MongoDB connections per service (Motor for repositories, PyMongo for checkpointing).

## Decision

**Migrate from Motor to PyMongo AsyncMongoClient service-by-service:**

### Migration Strategy

Since the application is **not in production**, we will:

1. **Disable LangGraph checkpointing** temporarily until migration is complete
2. **Migrate one service at a time** (not by component type)
3. **Investigate Change Streams first** before migrating services that use them
4. **No backwards compatibility** - clean cut, no deprecation warnings

### Migration Order

| Phase | Service | Change Streams? | Priority |
|-------|---------|-----------------|----------|
| 0 | **Spike: Change Streams** | Yes | **First** |
| 1 | plantation-model | No | High |
| 2 | ai-model (disable checkpointing) | No | High |
| 3 | collection-model | **Yes** | Medium |
| 4 | collection-mcp | No | Medium |
| 5 | fp-common (base classes) | **Yes** | Medium |
| 6 | fp-testing, scripts, E2E | No | Low |
| 7 | Re-enable LangGraph checkpointing | No | Last |

### LangGraph Checkpointing

**Temporarily disabled** until full migration is complete:

- Remove `use_checkpointer=True` calls
- Comment out checkpointer initialization in `WorkflowExecutionService`
- Re-enable with `AsyncMongoDBSaver` after all services migrated

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Keep Motor until EOL | Continue using Motor until May 2027 | Rejected: Tech debt, no new features |
| Migrate all at once | Single big-bang migration | Rejected: High risk |
| Start with checkpointer | Migrate checkpointer first, then services | Rejected: Checkpointing not priority |
| **Service-by-service** | Migrate one service at a time | **Selected** |
| Use sync PyMongo everywhere | Drop async entirely | Rejected: Loses async benefits |

## Implementation

### Phase 0: Change Streams Spike (Required First)

Before migrating services that use Change Streams, we must verify compatibility.

**Services using Change Streams:**
- `collection-model` - Source config caching (ADR-007)
- `fp-common` - `MongoChangeStreamCache` base class (ADR-013)

#### Change Streams API Comparison

| Feature | Motor | PyMongo Async | Notes |
|---------|-------|---------------|-------|
| Watch call | `async with collection.watch()` | `async with await collection.watch()` | **Extra `await` required** |
| Iteration | `async for change in stream` | `async for change in stream` | Same |
| Resume token | `stream.resume_token` | `stream.resume_token` | Same |
| Pipeline syntax | Same | Same | No changes |
| full_document | Same | Same | No changes |

**Key difference:** PyMongo async requires `await` on `watch()`:
```python
# Motor (current)
async with collection.watch(pipeline) as stream:

# PyMongo Async (new) - note the 'await'
async with await collection.watch(pipeline) as stream:
```

#### MongoDB Replica Set Requirement

**⚠️ Change Streams require a Replica Set** - standalone MongoDB is NOT supported.

| Deployment | Change Streams? |
|------------|-----------------|
| Standalone | ❌ Error: `$changeStream stage is only supported on replica sets` |
| Single-node Replica Set | ✅ Supported |
| Multi-node Replica Set | ✅ Supported |
| Sharded Cluster | ✅ Supported |

**Current status:** If Change Streams work today, we already have a replica set configured.

#### Spike Tasks

1. Create test script with PyMongo `AsyncMongoClient` + `collection.watch()`
2. Verify the `await` syntax difference works correctly
3. Test resume token persistence and recovery
4. Test pipeline filtering (insert/update/delete)
5. Benchmark performance vs Motor

```python
# Spike: Verify Change Streams work with PyMongo Async
from pymongo import AsyncMongoClient

async def test_change_stream():
    client = AsyncMongoClient("mongodb://localhost:27017")
    db = client["test_db"]
    collection = db["test_collection"]

    pipeline = [
        {"$match": {"operationType": {"$in": ["insert", "update", "delete"]}}}
    ]

    # Note: 'await' required on watch() - different from Motor!
    async with await collection.watch(
        pipeline=pipeline,
        full_document="updateLookup"
    ) as stream:
        async for change in stream:
            print(f"Operation: {change['operationType']}")
            resume_token = stream.resume_token
```

### Phase 1: Plantation Model (No Change Streams)

Simplest service to migrate - no Change Streams, straightforward repositories.

**Files to update:**
- `services/plantation-model/src/plantation_model/infrastructure/mongodb.py`
- `services/plantation-model/src/plantation_model/infrastructure/repositories/base.py`
- `services/plantation-model/src/plantation_model/infrastructure/repositories/*.py` (7 files)

**Changes per file:**

```python
# Old (Motor)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# New (PyMongo Async)
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
```

### Phase 2: AI Model (Disable Checkpointing)

**Step 1:** Disable LangGraph checkpointing temporarily

```python
# execution_service.py - Comment out checkpointer
def __init__(self, ...):
    # ADR-014: Checkpointing disabled during Motor→PyMongo migration
    # self._pymongo_client = MongoClient(mongodb_uri)
    self._checkpointer = None  # Disabled

async def execute(self, ..., use_checkpointer: bool = False, ...):
    # ADR-014: Force checkpointing off during migration
    use_checkpointer = False  # Disabled
    ...
```

**Step 2:** Migrate Motor to PyMongo Async in all repositories

### Phase 3-5: Collection Model, MCP, fp-common

Migrate after Change Streams spike confirms compatibility.

### Phase 6: Testing & Scripts

Update test fixtures and deployment scripts.

### Phase 7: Re-enable LangGraph Checkpointing

After full migration, re-enable with `AsyncMongoDBSaver`:

```python
from pymongo import AsyncMongoClient
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

client = AsyncMongoClient(mongodb_uri)
checkpointer = AsyncMongoDBSaver(client=client, db_name=database)
```

### Per-Service Migration Checklist

For each service migration:

1. **Update imports across all services:**
   ```python
   # Old
   from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

   # New
   from pymongo import AsyncMongoClient
   from pymongo.asynchronous.database import AsyncDatabase
   ```

2. **Update type hints:**
   ```python
   # Old
   def __init__(self, db: AsyncIOMotorDatabase): ...

   # New
   def __init__(self, db: AsyncDatabase): ...
   ```

3. **Update Change Stream code:**
   ```python
   # Motor
   async with collection.watch(...) as stream:
       async for change in stream:
           ...

   # PyMongo Async (same API, but verify)
   async with collection.watch(...) as stream:
       async for change in stream:
           ...
   ```

4. **Remove Motor dependency from all pyproject.toml files**

5. **Update root pyproject.toml:**
   ```toml
   # Remove
   "motor>=3.3.0",

   # Update pymongo constraint (remove upper bound if stable)
   "pymongo>=4.12",
   ```

## API Changes (Motor → PyMongo Async)

Since we're **not in production**, these are direct replacements with no backwards compatibility layer:

| Motor | PyMongo Async |
|-------|---------------|
| `from motor.motor_asyncio import AsyncIOMotorClient` | `from pymongo import AsyncMongoClient` |
| `from motor.motor_asyncio import AsyncIOMotorDatabase` | `from pymongo.asynchronous.database import AsyncDatabase` |
| `from motor.motor_asyncio import AsyncIOMotorCollection` | `from pymongo.asynchronous.collection import AsyncCollection` |
| `io_loop` parameter in client | Removed - not needed |
| `cursor.each()` | Use `async for` instead |
| `to_list(0)` | Use `to_list(None)` |
| `async with collection.watch()` | `async with await collection.watch()` (**extra `await`**) |

## Consequences

### Positive

- **50-140% performance improvement** under concurrent workloads
- **Future-proof** - Motor deprecated, PyMongo Async is the standard
- **Single MongoDB client type** - Eliminates dual client issue (Motor + PyMongo)
- **Native asyncio** - No thread pool overhead
- **Maintained by MongoDB** - Official driver

### Negative

- **Migration effort** - ~35 files need updates
- **Change Streams investigation required** - Must verify compatibility first
- **Not thread-safe** - `AsyncMongoClient` bound to single event loop
- **Checkpointing temporarily disabled** - Re-enabled after full migration

### Risks

| Risk | Mitigation |
|------|------------|
| Change Streams incompatibility | Phase 0 spike before migrating affected services |
| Hidden Motor-specific patterns | Code review during each service migration |
| Performance regression | Benchmark before/after for first service |

## Version Requirements

```toml
# Minimum for AsyncMongoClient
pymongo = ">=4.8"

# Current constraint (compatible)
pymongo = ">=4.12,<4.16"
```

## Revisit Triggers

Re-evaluate this decision if:

1. **Change Streams spike fails** - May need workaround or delay services using them
2. **PyMongo Async has stability issues** - May need to wait for fixes
3. **Motor gets un-deprecated** - Unlikely but possible

## References

- [PyMongo Migration Guide](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)
- [Motor Deprecation Announcement](https://www.mongodb.com/docs/drivers/motor/)
- [langgraph-checkpoint-mongodb](https://pypi.org/project/langgraph-checkpoint-mongodb/)
- [GitHub Issue #6506 - AsyncMongoDBSaver](https://github.com/langchain-ai/langgraph/issues/6506)
