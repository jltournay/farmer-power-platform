# ADR-012: BFF Service Composition and API Design Patterns

**Status:** Accepted
**Date:** 2026-01-03
**Deciders:** Winston (Architect), Amelia (Dev), Murat (Test Architect), Jeanlouistournay
**Related Stories:** Story 0.5.4 (BFF API Routes)

## Context

During Story 0.5.4 planning, we identified that the agent was hallucinating implementation details because architectural foundations were unclear:

1. **Service Composition Rules**: How should the BFF compose multiple gRPC client calls? When to use sequential vs parallel execution?
2. **API Schema Layer**: Should the BFF have its own Pydantic models separate from backend domain models?
3. **API Scope**: Which APIs are essential for MVP vs can be deferred?

This ADR captures decisions from a Party Mode architectural discussion on 2026-01-03.

---

## Decision 1: Service Composition Patterns

### Problem

The BFF service layer (`services/`) orchestrates calls to multiple gRPC clients (PlantationClient, CollectionClient). The story lacked explicit rules for:
- When to execute calls sequentially vs in parallel
- How to handle fan-out patterns (e.g., get farmers for N collection points)
- Concurrency limits to prevent backend overload

### Decision

**Adopt explicit composition patterns with bounded concurrency:**

| Pattern | Use When | Implementation |
|---------|----------|----------------|
| **Sequential** | Call B depends on output of Call A | `b_result = await b(await a())` |
| **Parallel (unbounded)** | ≤3 independent calls | `asyncio.gather(a(), b(), c())` |
| **Parallel (bounded)** | >3 calls OR fan-out scenarios | `Semaphore(5)` + `asyncio.gather()` |
| **Fan-out/Aggregate** | Enrich a list of items | Bounded parallel with result aggregation |

### Implementation

#### Base Service with Parallel Helpers

```python
# services/bff/src/bff/services/base_service.py
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

# Maximum concurrent gRPC calls to prevent backend overload
MAX_CONCURRENT_CALLS = 5


class BaseService:
    """Base service with parallel execution helpers."""

    _semaphore: asyncio.Semaphore | None = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """Lazy-init semaphore (one per event loop)."""
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
        return cls._semaphore

    async def _bounded_call(
        self,
        coro: Awaitable[T],
    ) -> T:
        """Execute a coroutine with bounded concurrency."""
        async with self._get_semaphore():
            return await coro

    async def _parallel_map(
        self,
        items: list,
        async_fn: Callable[..., Awaitable[T]],
    ) -> list[T]:
        """Apply async function to items with bounded concurrency.

        Example:
            results = await self._parallel_map(
                collection_points,
                lambda cp: self._plantation.list_farmers(collection_point_id=cp.id)
            )
        """
        tasks = [self._bounded_call(async_fn(item)) for item in items]
        return await asyncio.gather(*tasks)
```

#### Farmer Service Example

```python
# services/bff/src/bff/services/farmer_service.py
from bff.services.base_service import BaseService
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.infrastructure.clients.collection_client import CollectionClient
from bff.api.schemas.farmer_schemas import FarmerListResponse, FarmerSummary
from bff.transformers.farmer_transformer import FarmerTransformer


class FarmerService(BaseService):
    """Orchestrates farmer data from multiple backends."""

    def __init__(
        self,
        plantation_client: PlantationClient,
        collection_client: CollectionClient,
    ):
        self._plantation = plantation_client
        self._collection = collection_client

    async def list_farmers_by_factory(
        self,
        factory_id: str,
        page_size: int = 50,
    ) -> FarmerListResponse:
        """List farmers for a factory with quality summaries.

        Composition pattern:
        1. SEQUENTIAL: Get collection points (need factory_id)
        2. PARALLEL (bounded): Get farmers per collection point
        3. PARALLEL (bounded): Enrich each farmer with performance data
        """
        # Step 1: Sequential - get collection points for factory
        cps, _, _ = await self._plantation.list_collection_points(
            factory_id=factory_id
        )

        if not cps:
            return FarmerListResponse(farmers=[], total_count=0)

        # Step 2: Parallel (bounded) - get farmers for each CP
        farmer_lists = await self._parallel_map(
            cps,
            lambda cp: self._plantation.list_farmers(
                collection_point_id=cp.id,
                page_size=page_size,
            ),
        )

        # Flatten results
        all_farmers = [
            farmer
            for farmers, _, _ in farmer_lists
            for farmer in farmers
        ]

        # Step 3: Parallel (bounded) - enrich with performance
        summaries = await self._parallel_map(
            all_farmers,
            lambda f: self._enrich_farmer(f, factory_id),
        )

        return FarmerListResponse(
            farmers=summaries,
            total_count=len(summaries),
        )

    async def _enrich_farmer(
        self,
        farmer,
        factory_id: str,
    ) -> FarmerSummary:
        """Enrich farmer with performance data."""
        perf = await self._plantation.get_farmer_summary(farmer.id)
        return FarmerTransformer.to_summary(farmer, perf, factory_id)
```

### Anti-Patterns to Avoid

```python
# BAD: Sequential N+1 pattern
async def list_farmers_by_factory_bad(self, factory_id: str):
    cps, _, _ = await self._plantation.list_collection_points(factory_id)
    all_farmers = []
    for cp in cps:  # N+1 sequential calls!
        farmers, _, _ = await self._plantation.list_farmers(
            collection_point_id=cp.id
        )
        all_farmers.extend(farmers)
    return all_farmers

# BAD: Unbounded parallel for large fan-out
async def enrich_all_farmers_bad(self, farmers: list):
    # Could overwhelm backend with 1000+ concurrent calls
    return await asyncio.gather(*[
        self._get_performance(f.id) for f in farmers
    ])
```

### Service Layer Structure

```
services/bff/src/bff/services/
├── __init__.py
├── base_service.py           # Abstract base with parallel helpers
├── farmer_service.py         # Composes Plantation + Collection clients
└── dashboard_service.py      # Aggregation-heavy, uses fan-out patterns
```

---

## Decision 1b: Typed Response Wrappers for gRPC Clients

### Problem

The existing gRPC client pattern returns domain models, but **loses response-level metadata** like pagination:

```python
# Current pattern (implicit tuple)
async def list_farmers(...) -> tuple[list[Farmer], str | None, int]:
    # ...
    return farmers, next_token, response.total_count
```

Issues with this approach:
1. **Implicit contract** - No type safety on tuple structure
2. **Inconsistent** - Single entity returns `Farmer`, list returns `tuple`
3. **Fragile** - Easy to forget which position is `next_page_token` vs `total_count`
4. **Lost metadata** - If we just returned `list[Farmer]`, pagination would be lost

### Decision

**gRPC clients MUST return typed response wrappers that preserve response-level metadata alongside domain models.**

| Response Type | Wrapper | Contains |
|---------------|---------|----------|
| Single entity | Direct domain model | `Farmer`, `Factory`, etc. |
| Paginated list | `PaginatedResponse[T]` | `items: list[T]`, `next_page_token`, `total_count` |

### Implementation

#### Response Wrapper Types

```python
# services/bff/src/bff/infrastructure/clients/responses.py
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginatedResponse(Generic[T]):
    """Typed wrapper for paginated gRPC responses.

    This preserves pagination metadata that would be lost
    if we only returned domain models.

    Usage:
        response = await client.list_farmers(factory_id="FAC-001")
        for farmer in response.items:
            print(farmer.name)
        if response.next_page_token:
            # Fetch next page
    """
    items: list[T]
    next_page_token: str | None
    total_count: int

    def __iter__(self):
        """Allow iteration over items directly."""
        return iter(self.items)

    def __len__(self):
        """Return count of items in this page."""
        return len(self.items)

    @property
    def has_next_page(self) -> bool:
        """Check if more pages are available."""
        return self.next_page_token is not None


@dataclass(frozen=True)
class BoundedResponse(Generic[T]):
    """Typed wrapper for bounded (non-paginated) gRPC responses.

    Used when a method returns all items up to a limit without pagination cursor.
    Example: get_documents_by_farmer returns up to 100 docs, no next_page_token.

    Usage:
        response = await client.get_documents_by_farmer("WM-0001", "qc_results")
        print(f"Found {response.total_count} documents")
        for doc in response.items:
            print(doc.document_id)
    """
    items: list[T]
    total_count: int

    def __iter__(self):
        """Allow iteration over items directly."""
        return iter(self.items)

    def __len__(self):
        """Return count of items returned."""
        return len(self.items)
```

#### Updated gRPC Client Pattern

```python
# services/bff/src/bff/infrastructure/clients/plantation_client.py
from bff.infrastructure.clients.responses import PaginatedResponse
from fp_common.models import Farmer, CollectionPoint

class PlantationClient(BaseGrpcClient):

    @grpc_retry
    async def list_farmers(
        self,
        collection_point_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> PaginatedResponse[Farmer]:
        """List farmers with pagination.

        Returns:
            PaginatedResponse containing:
            - items: List of Farmer domain models
            - next_page_token: Token for next page (None if last page)
            - total_count: Total matching farmers across all pages
        """
        stub = await self._get_plantation_stub()
        request = plantation_pb2.ListFarmersRequest(
            collection_point_id=collection_point_id or "",
            page_size=page_size,
            page_token=page_token or "",
        )
        response = await stub.ListFarmers(request, metadata=self._get_metadata())

        return PaginatedResponse(
            items=[self._proto_to_farmer(f) for f in response.farmers],
            next_page_token=response.next_page_token or None,
            total_count=response.total_count,
        )

    @grpc_retry
    async def get_farmer(self, farmer_id: str) -> Farmer:
        """Get single farmer by ID.

        Returns:
            Farmer domain model directly (no wrapper needed for single entities).
        """
        stub = await self._get_plantation_stub()
        request = plantation_pb2.GetFarmerRequest(id=farmer_id)
        response = await stub.GetFarmer(request, metadata=self._get_metadata())
        return self._proto_to_farmer(response)
```

### Complete Data Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                     COMPLETE DATA FLOW WITH WRAPPERS                   │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Proto (ListFarmersResponse)                                           │
│  ├── farmers: repeated Farmer                                          │
│  ├── next_page_token: string                                           │
│  └── total_count: int32                                                │
│              │                                                         │
│              ▼                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  gRPC Client (PlantationClient)                                  │   │
│  │  Returns: PaginatedResponse[Farmer]                              │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  items: list[Farmer]       ← fp-common domain models     │   │   │
│  │  │  next_page_token: str|None ← PRESERVED from proto        │   │   │
│  │  │  total_count: int          ← PRESERVED from proto        │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│              │                                                         │
│              ▼                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  Service Layer (FarmerService)                                   │   │
│  │  - Accesses response.items for domain models                     │   │
│  │  - Accesses response.next_page_token for pagination              │   │
│  │  - Transforms domain models → API schemas                        │   │
│  │  Returns: FarmerListResponse (API Schema)                        │   │
│  └────────────────────────────────────────────────────────────────┘   │
│              │                                                         │
│              ▼                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  API Schema (FarmerListResponse)                                 │   │
│  │  ├── farmers: list[FarmerSummary]  ← transformed for UI         │   │
│  │  ├── next_page_token: str|None     ← passed through             │   │
│  │  └── total_count: int              ← passed through             │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

### Updated Service Layer Usage

```python
# services/bff/src/bff/services/farmer_service.py
class FarmerService(BaseService):

    async def list_farmers_by_factory(
        self,
        factory_id: str,
        page_size: int = 50,
    ) -> FarmerListResponse:
        # Step 1: Get collection points
        cp_response = await self._plantation.list_collection_points(
            factory_id=factory_id
        )

        if not cp_response.items:
            return FarmerListResponse(farmers=[], total_count=0)

        # Step 2: Parallel fetch farmers per CP
        farmer_responses = await self._parallel_map(
            cp_response.items,
            lambda cp: self._plantation.list_farmers(
                collection_point_id=cp.id,
                page_size=page_size,
            ),
        )

        # Flatten and transform
        all_farmers = [
            farmer
            for response in farmer_responses
            for farmer in response.items  # Access .items property
        ]

        # ... transform and return
```

### Migration Path

Existing clients use tuple returns. Migration required for **7 methods across 2 files**:

#### Step 1: Create Response Wrappers

Create `services/bff/src/bff/infrastructure/clients/responses.py`:

```python
@dataclass(frozen=True)
class PaginatedResponse(Generic[T]):
    """For paginated lists with cursor-based navigation."""
    items: list[T]
    next_page_token: str | None
    total_count: int

@dataclass(frozen=True)
class BoundedResponse(Generic[T]):
    """For bounded lists (all items up to limit, no pagination cursor)."""
    items: list[T]
    total_count: int
```

#### Step 2: Migrate PlantationClient (4 methods)

| Method | Line | Current | New |
|--------|------|---------|-----|
| `list_farmers` | 213 | `tuple[list[Farmer], str \| None, int]` | `PaginatedResponse[Farmer]` |
| `list_factories` | 307 | `tuple[list[Factory], str \| None, int]` | `PaginatedResponse[Factory]` |
| `list_collection_points` | 372 | `tuple[list[CollectionPoint], str \| None, int]` | `PaginatedResponse[CollectionPoint]` |
| `list_regions` | 440 | `tuple[list[Region], str \| None, int]` | `PaginatedResponse[Region]` |

#### Step 3: Migrate CollectionClient (3 methods)

| Method | Line | Current | New |
|--------|------|---------|-----|
| `list_documents` | 165 | `tuple[list[Document], str \| None, int]` | `PaginatedResponse[Document]` |
| `get_documents_by_farmer` | 204 | `tuple[list[Document], int]` | `BoundedResponse[Document]` |
| `search_documents` | 240 | `tuple[list[Document], str \| None, int]` | `PaginatedResponse[Document]` |

#### Step 4: Update Unit Tests

| Test File | Changes |
|-----------|---------|
| `tests/unit/bff/test_plantation_client.py` | Replace `farmers, next_token, total = await client.list_farmers(...)` with `response = await client.list_farmers(...); assert response.items == ...` |
| `tests/unit/bff/test_collection_client.py` | Same pattern |

#### NOT Affected (Separate Implementations)

- `mcp-servers/plantation-mcp/.../plantation_client.py` - Own client implementation
- `mcp-servers/collection-mcp/.../document_client.py` - Own client implementation
- E2E tests - Call MCP tools, not BFF clients
- Backend service tests - Test repository layer, not BFF clients

### Why This Pattern?

| Approach | Pros | Cons |
|----------|------|------|
| **Tuple** `(list, token, count)` | Simple | Implicit, error-prone |
| **Raw Proto** | Full data | Leaks proto to service layer |
| **Dict** `{"items": [], ...}` | Flexible | No type safety |
| **PaginatedResponse[T]** | Type-safe, explicit, iterable | Slightly more code |

**We choose `PaginatedResponse[T]`** because:
- Type checker validates usage
- IDE autocomplete works
- Impossible to confuse `next_page_token` with `total_count`
- Still returns domain models (not proto)
- Iterable for convenience

---

## Decision 2: BFF API Schema Layer

### Problem

The story showed confusion about whether to use `fp-common` domain models directly in FastAPI responses. Issues:
- Domain models have all fields; API may need subset or computed fields
- API responses often compose multiple domain entities
- Pagination, computed status, display names are API concerns

### Decision

**The BFF MUST have its own Pydantic API schemas in `api/schemas/`, separate from `fp-common` domain models.**

| Layer | Location | Purpose | Example |
|-------|----------|---------|---------|
| **Domain Models** | `libs/fp-common/fp_common/models/` | Backend service data structures | `Farmer`, `FarmerPerformance`, `Document` |
| **API Schemas** | `services/bff/src/bff/api/schemas/` | JSON contract with frontend | `FarmerSummary`, `FarmerListResponse` |
| **Transformers** | `services/bff/src/bff/transformers/` | Domain → API conversion | `FarmerTransformer.to_summary()` |

### Why Separate Schemas?

```
┌──────────────────────────────────────────────────────────────────┐
│                     DATA TRANSFORMATION FLOW                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PlantationClient          CollectionClient                       │
│       │                          │                                │
│       ▼                          ▼                                │
│  ┌────────────┐            ┌────────────┐                        │
│  │ Farmer     │            │ Document   │                        │
│  │ (20+ fields)│            │ (extracted_│                        │
│  │            │            │  fields{}) │                        │
│  └─────┬──────┘            └─────┬──────┘                        │
│        │                          │                               │
│        └──────────┬───────────────┘                               │
│                   │                                               │
│                   ▼                                               │
│        ┌─────────────────────┐                                   │
│        │  FarmerTransformer  │                                   │
│        │  - Merge entities   │                                   │
│        │  - Compute status   │                                   │
│        │  - Flatten nested   │                                   │
│        │  - Format for UI    │                                   │
│        └──────────┬──────────┘                                   │
│                   │                                               │
│                   ▼                                               │
│        ┌─────────────────────┐                                   │
│        │  FarmerSummary      │  ◄── What React frontend needs    │
│        │  (API Schema)       │                                   │
│        │  - id               │                                   │
│        │  - name (computed)  │                                   │
│        │  - status (computed)│                                   │
│        │  - primary_percent  │                                   │
│        │  - trend            │                                   │
│        └─────────────────────┘                                   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Key Differences

| Aspect | Domain Model (fp-common) | API Schema (BFF) |
|--------|--------------------------|------------------|
| **Purpose** | Backend data structure | Frontend JSON contract |
| **Fields** | All database fields | Only what UI needs |
| **Nesting** | Complex nested objects | Flattened for simplicity |
| **Computed** | Raw data only | `status`, `name`, `trend` computed |
| **Source** | Single entity | May combine multiple entities |
| **Pagination** | Not a concern | `next_page_token`, `total_count` |

### Implementation

#### API Schemas

```python
# services/bff/src/bff/api/schemas/farmer_schemas.py
from pydantic import BaseModel, Field
from datetime import datetime

class FarmerSummary(BaseModel):
    """API response for farmer list views.

    NOTE: This is an API schema, NOT a domain model.
    - `name` is computed from first_name + last_name
    - `tier` uses Plantation vocabulary (NOT Engagement vocabulary)
    """
    id: str = Field(..., description="Farmer ID")
    name: str = Field(..., description="Full name (computed)")
    factory_id: str = Field(..., description="Factory ID")
    collection_point_id: str
    primary_percentage_30d: float = Field(..., ge=0, le=100)
    tier: QualityTier = Field(..., description="tier_1, tier_2, tier_3, or below_tier_3")
    trend: str = Field(..., description="improving, stable, or declining")
    total_deliveries_today: int = Field(..., ge=0)


class FarmerListResponse(BaseModel):
    """Paginated farmer list - API-specific wrapper."""
    farmers: list[FarmerSummary] = Field(default_factory=list)
    next_page_token: str | None = None
    total_count: int = Field(..., ge=0)


class QualityEventResponse(BaseModel):
    """Quality event extracted from Document.

    NOTE: This flattens Document.extracted_fields into typed fields.
    """
    id: str
    farmer_id: str
    timestamp: datetime
    grade: str
    leaf_type: str
    weight_kg: float = Field(..., ge=0)
    grading_model_id: str
    attributes: dict = Field(default_factory=dict)
```

#### Transformer

```python
# services/bff/src/bff/transformers/farmer_transformer.py
from fp_common.models import Farmer, Factory
from fp_common.models.farmer_performance import FarmerPerformance
from bff.api.schemas.farmer_schemas import FarmerSummary, QualityTier, QualityEventResponse


def compute_tier(
    primary_percentage: float,
    tier_1_threshold: float,
    tier_2_threshold: float,
    tier_3_threshold: float,
) -> QualityTier:
    """Compute quality tier using factory-specific thresholds.

    Uses Factory.quality_thresholds, NOT hardcoded values.
    """
    if primary_percentage >= tier_1_threshold:
        return QualityTier.TIER_1
    elif primary_percentage >= tier_2_threshold:
        return QualityTier.TIER_2
    elif primary_percentage >= tier_3_threshold:
        return QualityTier.TIER_3
    return QualityTier.BELOW_TIER_3


class FarmerTransformer:
    """Transforms domain models to API schemas."""

    @staticmethod
    def to_summary(
        farmer: Farmer,
        performance: FarmerPerformance,
        factory: Factory,
    ) -> FarmerSummary:
        """Transform Farmer + FarmerPerformance + Factory → FarmerSummary.

        Note: Factory is required to get quality_thresholds for tier computation.
        """
        primary_pct = performance.historical.primary_percentage_30d
        thresholds = factory.quality_thresholds

        return FarmerSummary(
            id=farmer.id,
            name=f"{farmer.first_name} {farmer.last_name}",
            factory_id=factory.id,
            collection_point_id=farmer.collection_point_id,
            primary_percentage_30d=primary_pct,
            tier=compute_tier(
                primary_pct,
                thresholds.tier_1,
                thresholds.tier_2,
                thresholds.tier_3,
            ),
            trend=performance.historical.improvement_trend.value,
            total_deliveries_today=performance.today.deliveries,
        )

    @staticmethod
    def document_to_quality_event(doc: Document) -> QualityEventResponse:
        """Transform Document → QualityEventResponse."""
        ef = doc.extracted_fields
        lf = doc.linkage_fields

        return QualityEventResponse(
            id=doc.document_id,
            farmer_id=lf.get("farmer_id", ""),
            timestamp=doc.created_at,
            grade=ef.get("grade", ""),
            leaf_type=ef.get("leaf_type", ""),
            weight_kg=float(ef.get("weight_kg", 0)),
            grading_model_id=lf.get("grading_model_id", ""),
            attributes=ef.get("attributes", {}),
        )
```

### Schema Design Order

When implementing a new BFF endpoint:

1. **Define the API Schema first** - What does the frontend need?
2. **Identify source domain models** - Which backend services provide data?
3. **Implement transformer** - Map domain → API schema
4. **Implement service layer** - Orchestrate client calls
5. **Implement route** - Wire up FastAPI endpoint

---

## Decision 2b: Domain Vocabulary - Plantation vs Engagement

### Problem

The original Story 0.5.4 used Engagement Model vocabulary (`WIN`, `WATCH`, `ACTION_NEEDED`) in BFF API responses. However, looking at the proto:

```protobuf
// Factory-configurable quality thresholds for farmer categorization (Story 1.7)
// NEUTRAL NAMING: tier_1, tier_2, tier_3 (NOT WIN/WATCH/WORK)
// Engagement Model maps these to engagement categories.
message QualityThresholds {
  double tier_1 = 1;  // Premium tier threshold (default ≥85% Primary)
  double tier_2 = 2;  // Standard tier threshold (default ≥70% Primary)
  double tier_3 = 3;  // Acceptable tier threshold (default ≥50% Primary)
}
```

The proto explicitly states that **Engagement Model** owns the mapping to engagement categories.

### Decision

**BFF uses Plantation Model vocabulary (neutral tiers), NOT Engagement Model vocabulary.**

| Domain | Vocabulary | Example |
|--------|------------|---------|
| **Plantation Model** | `tier_1`, `tier_2`, `tier_3`, `below_tier_3` | Neutral, factory-configurable |
| **Engagement Model** | `WIN`, `WATCH`, `ACTION_NEEDED` | Engagement categories (future) |
| **BFF API** | Uses Plantation vocabulary | `"tier": "tier_1"` |
| **Frontend** | Maps tiers to display labels | `tier_1` → green badge "Excellent" |

### Domain Boundary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CORRECT DOMAIN FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Plantation Model                                                        │
│  ├── FarmerPerformance.primary_percentage_30d = 82.5                    │
│  └── Factory.quality_thresholds = {tier_1: 85, tier_2: 70, tier_3: 50}  │
│              │                                                           │
│              ▼                                                           │
│  BFF (computes tier from thresholds)                                    │
│  └── tier = "tier_2"  (82.5 >= 70, < 85)                                │
│              │                                                           │
│              ▼                                                           │
│  API Response                                                            │
│  └── {"primary_percentage": 82.5, "tier": "tier_2"}                     │
│              │                                                           │
│              ▼                                                           │
│  Frontend (maps to display)                                              │
│  └── tier_2 → Yellow badge, "Watch" label                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Updated API Schema

```python
# services/bff/src/bff/api/schemas/farmer_schemas.py
from enum import Enum

class QualityTier(str, Enum):
    """Neutral quality tier from Plantation Model.

    NOT engagement categories (WIN/WATCH/ACTION_NEEDED).
    Frontend maps these to display labels.
    """
    TIER_1 = "tier_1"      # Premium (default ≥85% primary)
    TIER_2 = "tier_2"      # Standard (default ≥70% primary)
    TIER_3 = "tier_3"      # Acceptable (default ≥50% primary)
    BELOW_TIER_3 = "below_tier_3"  # Below acceptable


class FarmerSummary(BaseModel):
    """API response for farmer list views."""
    id: str
    name: str
    factory_id: str
    collection_point_id: str
    primary_percentage_30d: float = Field(..., ge=0, le=100)
    tier: QualityTier  # Neutral tier, NOT engagement category
    trend: str  # "improving", "stable", "declining"
    total_deliveries_today: int = Field(..., ge=0)
```

### Tier Computation

```python
# services/bff/src/bff/transformers/farmer_transformer.py
from bff.api.schemas.farmer_schemas import QualityTier
from fp_common.models import Factory, FarmerPerformance


def compute_tier(
    primary_percentage: float,
    thresholds: QualityThresholds,
) -> QualityTier:
    """Compute quality tier using factory-specific thresholds.

    Uses Factory.quality_thresholds, NOT hardcoded values.
    """
    if primary_percentage >= thresholds.tier_1:
        return QualityTier.TIER_1
    elif primary_percentage >= thresholds.tier_2:
        return QualityTier.TIER_2
    elif primary_percentage >= thresholds.tier_3:
        return QualityTier.TIER_3
    else:
        return QualityTier.BELOW_TIER_3
```

### Why This Matters

1. **Thresholds are factory-configurable** - Some factories may use 80%/65% instead of 85%/70%
2. **Labels are UI concerns** - "WIN" vs "Excellent" vs localized text
3. **Engagement Model will own categories** - When built, it adds coaching/intervention logic
4. **BFF stays in its lane** - Passes Plantation data, doesn't own engagement logic

---

## Decision 3: Story 0.5.4 API Scope Reduction

### Problem

Story 0.5.4 originally defined 5 API endpoints covering factory portal use cases. This scope is too large for one story that also needs to:
1. Establish the BFF service composition pattern
2. Migrate 7 gRPC client methods to typed response wrappers
3. Create the API schema and transformer layer

### Decision

**Reduce Story 0.5.4 to the minimum APIs needed to validate the BFF pattern: list and detail farmers only.**

### MVP APIs for Story 0.5.4

| Endpoint | Purpose | Tests |
|----------|---------|-------|
| `GET /api/farmers` | List farmers with pagination | Service composition, parallel calls, `PaginatedResponse`, transformers |
| `GET /api/farmers/{id}` | Single farmer detail | Single entity fetch, authorization, `FarmerPerformance` enrichment |

That's it. Two endpoints to prove the pattern works.

### Deferred to Story 0.5.4b (Factory Portal)

| Endpoint | Reason for Deferral |
|----------|---------------------|
| `GET /api/farmers/{id}/quality-events` | Requires `CollectionClient` + Document → QualityEvent transform |
| `GET /api/dashboard/summary` | Requires aggregation logic across multiple clients |
| `GET /api/dashboard/farmers-by-status` | Requires grouping logic |

### Deferred to Epic 11 (Registration Kiosk)

| Endpoint | Reason for Deferral |
|----------|---------------------|
| `POST /api/farmers` | Write operation, offline-first PWA flow |
| `GET /api/collection-points` | Registration Kiosk specific |

### Deferred to Epic 9 (Admin Portal)

| Endpoint | Reason for Deferral |
|----------|---------------------|
| `POST /api/admin/factories` | Factory onboarding (admin only) |
| `/api/admin/*` | Admin-specific operations |

### Updated Story 0.5.4 Acceptance Criteria

```markdown
### AC1: Farmer List Endpoint
**Given** authenticated users need farmer data
**When** I call `GET /api/farmers?factory_id={id}&page_size={n}&page_token={token}`
**Then** Paginated farmer list is returned with quality summaries
**And** Response uses `FarmerListResponse` API schema
**And** Factory authorization is enforced

### AC2: Farmer Detail Endpoint
**Given** I need a specific farmer's details
**When** I call `GET /api/farmers/{farmer_id}`
**Then** Farmer profile with performance summary is returned
**And** Response uses `FarmerDetailResponse` API schema
**And** Factory authorization is enforced

### AC3: Error Handling
**Given** any API error occurs
**When** the error is returned to the client
**Then** Error response follows RFC 7807 Problem Details format
```

---

## Decision 4: API Error Response Format (RFC 7807)

### Problem

FastAPI default error responses are inconsistent:
- Validation errors return `{"detail": [...]}`
- HTTPException returns `{"detail": "message"}`
- Unhandled exceptions return generic 500

Frontends need a predictable error contract for:
- Displaying user-friendly messages
- Handling specific error types (retry, redirect, etc.)
- Correlating errors with backend logs

### Decision

**All BFF API errors MUST use RFC 7807 Problem Details format.**

### Error Response Schema

```python
# services/bff/src/bff/api/schemas/error_schemas.py
from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs.

    Reference: https://datatracker.ietf.org/doc/html/rfc7807
    """
    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type"
    )
    title: str = Field(
        ...,
        description="Short, human-readable summary of the problem"
    )
    status: int = Field(
        ...,
        description="HTTP status code"
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence"
    )
    instance: str | None = Field(
        default=None,
        description="URI reference to the specific occurrence"
    )
    # Extension fields
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code for client logic"
    )
    trace_id: str | None = Field(
        default=None,
        description="Correlation ID for log tracing"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "https://api.farmerpower.ai/errors/farmer-not-found",
                "title": "Farmer Not Found",
                "status": 404,
                "detail": "Farmer with ID 'FAR-999' does not exist",
                "instance": "/api/farmers/FAR-999",
                "error_code": "FARMER_NOT_FOUND",
                "trace_id": "abc123-def456"
            }
        }
```

### Error Type URIs

| Error Type | URI | Status | Use Case |
|------------|-----|--------|----------|
| `farmer-not-found` | `https://api.farmerpower.ai/errors/farmer-not-found` | 404 | Farmer ID doesn't exist |
| `factory-not-found` | `https://api.farmerpower.ai/errors/factory-not-found` | 404 | Factory ID doesn't exist |
| `factory-access-denied` | `https://api.farmerpower.ai/errors/factory-access-denied` | 403 | User lacks factory access |
| `token-expired` | `https://api.farmerpower.ai/errors/token-expired` | 401 | JWT token expired |
| `token-invalid` | `https://api.farmerpower.ai/errors/token-invalid` | 401 | JWT validation failed |
| `validation-error` | `https://api.farmerpower.ai/errors/validation-error` | 422 | Request validation failed |
| `service-unavailable` | `https://api.farmerpower.ai/errors/service-unavailable` | 503 | Backend service down |
| `internal-error` | `https://api.farmerpower.ai/errors/internal-error` | 500 | Unexpected server error |

### Error Codes (Machine-Readable)

```python
# services/bff/src/bff/api/schemas/error_codes.py
from enum import Enum


class ErrorCode(str, Enum):
    """Machine-readable error codes for frontend logic."""
    # Authentication (401)
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_MISSING = "TOKEN_MISSING"

    # Authorization (403)
    FACTORY_ACCESS_DENIED = "FACTORY_ACCESS_DENIED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Not Found (404)
    FARMER_NOT_FOUND = "FARMER_NOT_FOUND"
    FACTORY_NOT_FOUND = "FACTORY_NOT_FOUND"
    COLLECTION_POINT_NOT_FOUND = "COLLECTION_POINT_NOT_FOUND"

    # Validation (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PAGE_TOKEN = "INVALID_PAGE_TOKEN"

    # Server (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

### Implementation

#### Global Exception Handler

```python
# services/bff/src/bff/api/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from opentelemetry import trace

from bff.api.schemas.error_schemas import ProblemDetail
from bff.api.schemas.error_codes import ErrorCode


class BFFException(Exception):
    """Base exception for BFF-specific errors."""
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        title: str,
        detail: str | None = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.title = title
        self.detail = detail


class FarmerNotFoundError(BFFException):
    def __init__(self, farmer_id: str):
        super().__init__(
            status_code=404,
            error_code=ErrorCode.FARMER_NOT_FOUND,
            title="Farmer Not Found",
            detail=f"Farmer with ID '{farmer_id}' does not exist",
        )


class FactoryAccessDeniedError(BFFException):
    def __init__(self, factory_id: str):
        super().__init__(
            status_code=403,
            error_code=ErrorCode.FACTORY_ACCESS_DENIED,
            title="Factory Access Denied",
            detail=f"You do not have access to factory '{factory_id}'",
        )


def get_trace_id() -> str | None:
    """Get current OpenTelemetry trace ID."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


async def bff_exception_handler(request: Request, exc: BFFException) -> JSONResponse:
    """Handle BFF-specific exceptions."""
    error = ProblemDetail(
        type=f"https://api.farmerpower.ai/errors/{exc.error_code.value.lower().replace('_', '-')}",
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        error_code=exc.error_code.value,
        trace_id=get_trace_id(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(exclude_none=True),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    error = ProblemDetail(
        type="https://api.farmerpower.ai/errors/validation-error",
        title="Validation Error",
        status=422,
        detail="Request validation failed. See error details.",
        instance=str(request.url.path),
        error_code=ErrorCode.VALIDATION_ERROR.value,
        trace_id=get_trace_id(),
    )
    # Include validation errors in response (safe to expose)
    response = error.model_dump(exclude_none=True)
    response["errors"] = exc.errors()
    return JSONResponse(status_code=422, content=response)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    IMPORTANT: Do NOT expose internal error details to client.
    """
    error = ProblemDetail(
        type="https://api.farmerpower.ai/errors/internal-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred. Please try again later.",
        instance=str(request.url.path),
        error_code=ErrorCode.INTERNAL_ERROR.value,
        trace_id=get_trace_id(),
    )
    # Log the actual exception with trace_id for debugging
    # logger.exception(f"Unhandled exception trace_id={get_trace_id()}")
    return JSONResponse(
        status_code=500,
        content=error.model_dump(exclude_none=True),
    )
```

#### Register Handlers in main.py

```python
# services/bff/src/bff/main.py
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from bff.api.middleware.error_handler import (
    BFFException,
    bff_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

app = FastAPI(title="Farmer Power BFF")

# Register exception handlers
app.add_exception_handler(BFFException, bff_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

### Example Responses

#### 404 Not Found
```json
{
  "type": "https://api.farmerpower.ai/errors/farmer-not-found",
  "title": "Farmer Not Found",
  "status": 404,
  "detail": "Farmer with ID 'FAR-999' does not exist",
  "instance": "/api/farmers/FAR-999",
  "error_code": "FARMER_NOT_FOUND",
  "trace_id": "abc123def456789"
}
```

#### 403 Forbidden
```json
{
  "type": "https://api.farmerpower.ai/errors/factory-access-denied",
  "title": "Factory Access Denied",
  "status": 403,
  "detail": "You do not have access to factory 'KEN-FAC-002'",
  "instance": "/api/farmers",
  "error_code": "FACTORY_ACCESS_DENIED",
  "trace_id": "def456abc789012"
}
```

#### 401 Unauthorized (Token Expired)
```json
{
  "type": "https://api.farmerpower.ai/errors/token-expired",
  "title": "Token Expired",
  "status": 401,
  "detail": "Your authentication token has expired. Please refresh and retry.",
  "error_code": "TOKEN_EXPIRED",
  "trace_id": "ghi789jkl012345"
}
```

#### 422 Validation Error
```json
{
  "type": "https://api.farmerpower.ai/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed. See error details.",
  "instance": "/api/farmers",
  "error_code": "VALIDATION_ERROR",
  "trace_id": "mno345pqr678901",
  "errors": [
    {
      "loc": ["query", "page_size"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le"
    }
  ]
}
```

#### 500 Internal Server Error
```json
{
  "type": "https://api.farmerpower.ai/errors/internal-error",
  "title": "Internal Server Error",
  "status": 500,
  "detail": "An unexpected error occurred. Please try again later.",
  "instance": "/api/farmers/FAR-001",
  "error_code": "INTERNAL_ERROR",
  "trace_id": "stu901vwx234567"
}
```

### Security Considerations

1. **Never expose internal details** - Stack traces, database errors, and internal paths must NOT appear in responses
2. **Always include trace_id** - Enables log correlation without exposing sensitive info
3. **Sanitize user input in detail** - Don't echo unsanitized input back (XSS prevention)
4. **Log internally** - Full exception with stack trace goes to logs, not response

---

## Consequences

### Positive

- **Clear composition rules** prevent N+1 anti-patterns and backend overload
- **Bounded concurrency** protects backend services from burst traffic
- **Separate API schemas** give frontend-specific contracts without leaking backend structure
- **Consistent error format** (RFC 7807) enables frontend error handling without guessing
- **Reduced scope** allows faster delivery and focused testing
- **Agent clarity** - explicit patterns reduce hallucination during implementation

### Negative

- **More files** - `api/schemas/`, `transformers/`, `services/` add structure
- **Two schema layers** - Must maintain both domain models and API schemas
- **Story split** - Original scope now spans multiple stories

### Risks Mitigated

- **Concurrency risk** - Semaphore prevents backend service overload
- **Coupling risk** - API schemas can evolve independently of domain models
- **Scope creep risk** - Focused MVP enables faster validation

---

## Implementation Checklist for Story 0.5.4

When implementing Story 0.5.4, agents MUST:

### Infrastructure Layer
- [ ] Create `infrastructure/clients/responses.py` with `PaginatedResponse[T]` wrapper
- [ ] Update `PlantationClient` list methods to return `PaginatedResponse[T]` instead of tuple
- [ ] Update `CollectionClient` list methods to return `PaginatedResponse[T]` instead of tuple

### Service Layer
- [ ] Create `services/base_service.py` with `_parallel_map()` helper
- [ ] Implement `FarmerService` extending `BaseService`
- [ ] Use bounded parallel for collection point fan-out
- [ ] Access pagination via `response.items`, `response.next_page_token`

### API Layer
- [ ] Create `api/schemas/farmer_schemas.py` with `FarmerSummary`, `FarmerListResponse`
- [ ] Create `api/schemas/error_schemas.py` with `ProblemDetail`
- [ ] Create `api/schemas/error_codes.py` with `ErrorCode` enum
- [ ] Create `api/middleware/error_handler.py` with exception handlers
- [ ] Create `transformers/farmer_transformer.py` with `to_summary()`
- [ ] Register exception handlers in `main.py`

### Scope
- [ ] Implement only AC1-AC3 (farmers list, detail, error handling)
- [ ] Defer dashboard and quality-events endpoints to 0.5.4b

---

## References

- Story 0.5.4: `_bmad-output/sprint-artifacts/0-5-4-bff-api-routes.md`
- ADR-002: Frontend Architecture (BFF section)
- ADR-011: Service Architecture (gRPC + DAPR patterns)
- Project Context: `_bmad-output/project-context.md`
