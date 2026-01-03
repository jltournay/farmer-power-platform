# Story 0.5.4a: BFF Client Response Wrappers

**Status:** in-progress
**GitHub Issue:** #77
**Story Points:** 3

## Story

As a **backend developer**,
I want standardized API response wrappers (ApiResponse, PaginatedResponse, ApiError) in the BFF,
So that all API endpoints return consistent, typed responses following ADR-012 patterns.

## Acceptance Criteria

### AC1: ApiResponse Generic Wrapper
**Given** I need to return a single entity from an API endpoint
**When** I use `ApiResponse[T]`
**Then** The response follows Google JSON style: `{"data": <T>, "meta": {...}}`
**And** Meta includes optional request_id, timestamp, and version fields
**And** Response is fully typed with generic T support

### AC2: PaginatedResponse Generic Wrapper
**Given** I need to return a list of entities with pagination
**When** I use `PaginatedResponse[T]`
**Then** The response follows: `{"data": [<T>...], "pagination": {...}, "meta": {...}}`
**And** Pagination includes page, page_size, total_count, total_pages, has_next, has_prev
**And** Cursor-based pagination is also supported via next_page_token

### AC2b: BoundedResponse Generic Wrapper
**Given** I need to return a bounded list (all items up to limit, no pagination cursor)
**When** I use `BoundedResponse[T]`
**Then** The response follows: `{"data": [<T>...], "total_count": N, "meta": {...}}`
**And** No pagination metadata (no next_page_token, no page number)
**And** Used for methods like `get_documents_by_farmer` that return limited but complete results

### AC3: ApiError Structured Error Response
**Given** An error occurs during API processing
**When** The error is returned to the client
**Then** Response follows: `{"error": {"code": "...", "message": "...", "details": {...}}}`
**And** Error codes are standardized (validation_error, not_found, unauthorized, forbidden, etc.)
**And** Details may include field-level validation errors

### AC4: ErrorDetail Validation Support
**Given** A request validation error occurs
**When** I return field-level errors
**Then** Each field error has: field, message, and optional code
**And** Multiple field errors can be returned in a single response
**And** Field paths support nested fields (e.g., "contact.phone")

### AC5: Integration with Auth Error Codes
**Given** Authentication or authorization fails
**When** The error response is generated
**Then** AuthErrorCode enum values are used as error codes
**And** Existing auth middleware can use ApiError for consistent responses

### AC6: Schema Module Organization
**Given** The new response schemas exist
**When** I import from `bff.api.schemas`
**Then** All response types are exported from `__init__.py`
**And** Import path is: `from bff.api.schemas import ApiResponse, PaginatedResponse, BoundedResponse, ApiError`

### AC7: Migrate PlantationClient List Methods
**Given** PlantationClient has 4 list methods returning tuples
**When** I migrate to response wrappers
**Then** `list_farmers` returns `PaginatedResponse[Farmer]`
**And** `list_factories` returns `PaginatedResponse[Factory]`
**And** `list_collection_points` returns `PaginatedResponse[CollectionPoint]`
**And** `list_regions` returns `PaginatedResponse[Region]`
**And** Existing unit tests are updated to use new return types

### AC8: Migrate CollectionClient List Methods
**Given** CollectionClient has 3 list methods returning tuples
**When** I migrate to response wrappers
**Then** `list_documents` returns `PaginatedResponse[Document]`
**And** `search_documents` returns `PaginatedResponse[Document]`
**And** `get_documents_by_farmer` returns `BoundedResponse[Document]` (no pagination cursor)
**And** Existing unit tests are updated to use new return types

## Tasks / Subtasks

- [x] **Task 1: Create Response Wrapper Schemas**
  - [x] Create `services/bff/src/bff/api/schemas/responses.py`
  - [x] Implement `ApiResponse[T]` generic model per ADR-012
  - [x] Implement `PaginatedResponse[T]` with cursor and offset pagination
  - [x] Implement `BoundedResponse[T]` for bounded lists (no pagination cursor)
  - [x] Implement `ApiError` structured error response
  - [x] Implement `ErrorDetail` for field-level validation errors
  - [x] Implement `PaginationMeta` for pagination metadata
  - [x] Implement `ResponseMeta` for response metadata

- [x] **Task 2: Error Code Enumeration**
  - [x] Create `ApiErrorCode` enum in responses.py (distinct from AuthErrorCode)
  - [x] Include: validation_error, not_found, unauthorized, forbidden, internal_error, service_unavailable
  - [x] Ensure compatibility with existing AuthErrorCode

- [x] **Task 3: Update Schema Exports**
  - [x] Update `services/bff/src/bff/api/schemas/__init__.py`
  - [x] Export all new response types
  - [x] Maintain existing auth schema exports

- [x] **Task 4: Migrate PlantationClient** (AC: #7)
  - [x] Update `list_farmers` to return `PaginatedResponse[Farmer]`
  - [x] Update `list_factories` to return `PaginatedResponse[Factory]`
  - [x] Update `list_collection_points` to return `PaginatedResponse[CollectionPoint]`
  - [x] Update `list_regions` to return `PaginatedResponse[Region]`
  - [x] Update existing unit tests in `tests/unit/bff/test_plantation_client.py`

- [x] **Task 5: Migrate CollectionClient** (AC: #8)
  - [x] Update `list_documents` to return `PaginatedResponse[Document]`
  - [x] Update `search_documents` to return `PaginatedResponse[Document]`
  - [x] Update `get_documents_by_farmer` to return `BoundedResponse[Document]`
  - [x] Update existing unit tests in `tests/unit/bff/test_collection_client.py`

- [x] **Task 6: Unit Tests for Response Schemas**
  - [x] Create `tests/unit/bff/test_response_schemas.py`
  - [x] Test ApiResponse serialization with various domain models
  - [x] Test PaginatedResponse with pagination metadata
  - [x] Test BoundedResponse with items and total_count
  - [x] Test ApiError with different error codes and details
  - [x] Test ErrorDetail field-level error formatting
  - [x] Test generic type inference with Pydantic

- [x] **Task 7: Documentation**
  - [x] Add docstrings with usage examples
  - [x] Reference ADR-012 in module docstring

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.4a: BFF Client Response Wrappers"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-4a-bff-response-wrappers
  ```

**Branch name:** `story/0-5-4a-bff-response-wrappers`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-4a-bff-response-wrappers`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.4a: BFF Client Response Wrappers" --base main`
- [ ] CI passes on PR (Quality CI)
- [ ] E2E tests pass (E2E CI)
- [ ] Code review completed (`/code-review`)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-4a-bff-response-wrappers`

**PR URL:** (to be added)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/bff/src:libs/fp-proto/src:libs/fp-common:libs/fp-testing/src" pytest tests/unit/bff/test_response_schemas.py -v
```
**Output:**
```
tests/unit/bff/test_response_schemas.py::TestResponseMeta::test_default_values PASSED
tests/unit/bff/test_response_schemas.py::TestResponseMeta::test_custom_values PASSED
tests/unit/bff/test_response_schemas.py::TestPaginationMeta::test_default_values PASSED
tests/unit/bff/test_response_schemas.py::TestPaginationMeta::test_from_client_response_with_next_page PASSED
tests/unit/bff/test_response_schemas.py::TestPaginationMeta::test_from_client_response_no_next_page PASSED
tests/unit/bff/test_response_schemas.py::TestPaginationMeta::test_from_client_response_middle_page PASSED
tests/unit/bff/test_response_schemas.py::TestPaginationMeta::test_from_client_response_zero_total PASSED
tests/unit/bff/test_response_schemas.py::TestApiResponse::test_simple_entity PASSED
tests/unit/bff/test_response_schemas.py::TestApiResponse::test_dict_serialization PASSED
tests/unit/bff/test_response_schemas.py::TestApiResponse::test_custom_meta PASSED
tests/unit/bff/test_response_schemas.py::TestPaginatedResponse::test_from_client_response PASSED
tests/unit/bff/test_response_schemas.py::TestPaginatedResponse::test_empty_list PASSED
tests/unit/bff/test_response_schemas.py::TestPaginatedResponse::test_last_page PASSED
tests/unit/bff/test_response_schemas.py::TestBoundedResponse::test_from_client_response PASSED
tests/unit/bff/test_response_schemas.py::TestBoundedResponse::test_len_method PASSED
tests/unit/bff/test_response_schemas.py::TestBoundedResponse::test_empty_response PASSED
tests/unit/bff/test_response_schemas.py::TestErrorDetail::test_basic_error PASSED
tests/unit/bff/test_response_schemas.py::TestErrorDetail::test_error_with_code PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_direct_creation PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_validation_error_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_not_found_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_unauthorized_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_unauthorized_custom_message PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_forbidden_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_forbidden_custom_message PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_service_unavailable_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_internal_error_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_internal_error_custom_message PASSED
tests/unit/bff/test_response_schemas.py::TestApiError::test_bad_request_factory PASSED
tests/unit/bff/test_response_schemas.py::TestApiErrorCode::test_all_error_codes_defined PASSED
tests/unit/bff/test_response_schemas.py::TestApiErrorCode::test_enum_string_values PASSED
tests/unit/bff/test_response_schemas.py::TestSchemaExports::test_all_exports_importable PASSED

======================== 32 passed, 1 warning in 0.17s =========================
```

### 2. Full BFF Unit Tests
```bash
PYTHONPATH=".:services/bff/src:libs/fp-proto/src:libs/fp-common:libs/fp-testing/src" pytest tests/unit/bff/ -v
```
**Output:**
```
====================== 148 passed, 22 warnings in 13.97s =======================
```

### 3. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Validate seed data first
python tests/e2e/infrastructure/validate_seed_data.py
# Output: VALIDATION PASSED: All seed data is valid

# Start infrastructure (MUST use --build to rebuild images)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH=".:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 85 passed, 1 skipped in 126.16s (0:02:06) ===================
```
**E2E passed:** [x] Yes / [ ] No

### 4. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
341 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

### 5. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-5-4a-bff-response-wrappers

# Wait ~30s, then check CI status
gh run list --branch story/0-5-4a-bff-response-wrappers --limit 3
```
**Quality CI Run ID:** (to be filled)
**E2E CI Run ID:** (to be filled)
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** (to be filled)

---

## Dev Notes

### What's Already Done (DO NOT DUPLICATE)

The following items already exist from previous stories - do NOT recreate:

| Item | Location | Status |
|------|----------|--------|
| TokenClaims model | `services/bff/src/bff/api/schemas/auth.py` | Exists |
| AuthErrorCode enum | `services/bff/src/bff/api/schemas/auth.py` | Exists |
| Schema __init__.py | `services/bff/src/bff/api/schemas/__init__.py` | Exists |
| PlantationClient | `services/bff/src/bff/infrastructure/clients/plantation_client.py` | Exists |
| CollectionClient | `services/bff/src/bff/infrastructure/clients/collection_client.py` | Exists |
| Base client errors | `services/bff/src/bff/infrastructure/clients/base.py` | Exists |

### Previous Story Intelligence (CRITICAL)

**From Story 0.5.3, the BFF auth system provides:**
- JWT validation (mock + Azure B2C stub)
- TokenClaims with role, factory_id, permissions
- AuthErrorCode enum for auth-specific errors
- Permission and factory access decorators

**From Story 0.5.2, BFF clients exist with:**
- PlantationClient: 13 read + 11 write methods returning fp-common domain models
- CollectionClient: 4 document query methods returning fp-common Document models
- All return typed Pydantic models (NOT dicts)
- Base client has ServiceUnavailableError and NotFoundError

**Directory structure for this story:**
```
services/bff/
├── src/bff/
│   ├── api/
│   │   ├── schemas/
│   │   │   ├── __init__.py      ← Update exports
│   │   │   ├── auth.py          ← Existing (AuthErrorCode)
│   │   │   └── responses.py     ← NEW: Response wrappers
│   │   ├── routes/              ← Story 0.5.4b
│   │   └── middleware/          ← Story 0.5.3 (done)
│   ├── infrastructure/
│   │   └── clients/             ← Story 0.5.2 (done)
│   ├── services/                ← Story 0.5.4b
│   └── transformers/            ← Story 0.5.4b
```

### Architecture Requirements (ADR-012)

**Response Patterns (from ADR-012 §4.1-4.3):**

```python
# Single entity response
{
    "data": { ... },
    "meta": {
        "request_id": "uuid",
        "timestamp": "2026-01-03T10:00:00Z",
        "version": "1.0"
    }
}

# Paginated list response (with cursor)
{
    "data": [ ... ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_count": 150,
        "total_pages": 8,
        "has_next": true,
        "has_prev": false,
        "next_page_token": "cursor-abc"
    },
    "meta": { ... }
}

# Bounded list response (no pagination cursor)
{
    "data": [ ... ],
    "total_count": 42,
    "meta": { ... }
}

# Error response
{
    "error": {
        "code": "validation_error",
        "message": "Request validation failed",
        "details": {
            "fields": [
                {"field": "phone", "message": "Invalid phone format", "code": "invalid_format"}
            ]
        }
    }
}
```

### Implementation Patterns

**Generic Response Pattern (Pydantic 2.0):**
```python
from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime, UTC
import uuid

T = TypeVar("T")

class ResponseMeta(BaseModel):
    """Metadata included in all API responses."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"

class ApiResponse(BaseModel, Generic[T]):
    """Standard wrapper for single-entity API responses."""
    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    page: int = 1
    page_size: int = 20
    total_count: int = 0
    total_pages: int = Field(default=0)
    has_next: bool = False
    has_prev: bool = False
    next_page_token: str | None = None

    @classmethod
    def from_list_response(
        cls,
        total_count: int,
        page_size: int,
        next_page_token: str | None = None,
        page: int = 1,
    ) -> "PaginationMeta":
        """Create from client list_* response."""
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=next_page_token is not None,
            has_prev=page > 1,
            next_page_token=next_page_token,
        )

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard wrapper for paginated list API responses."""
    data: list[T]
    pagination: PaginationMeta
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

class BoundedResponse(BaseModel, Generic[T]):
    """Wrapper for bounded lists (all items up to limit, no pagination cursor).

    Used for methods like get_documents_by_farmer that return:
    - All items up to a limit
    - Total count
    - No next_page_token
    """
    data: list[T]
    total_count: int
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    def __len__(self) -> int:
        """Return count of items returned."""
        return len(self.data)
```

**Error Response Pattern:**
```python
from enum import Enum

class ApiErrorCode(str, Enum):
    """Standard API error codes."""
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    BAD_REQUEST = "bad_request"

class ErrorDetail(BaseModel):
    """Field-level validation error detail."""
    field: str
    message: str
    code: str | None = None

class ApiError(BaseModel):
    """Structured error response per ADR-012."""
    code: str
    message: str
    details: dict | None = None

    @classmethod
    def validation_error(cls, errors: list[ErrorDetail]) -> "ApiError":
        """Create validation error with field details."""
        return cls(
            code=ApiErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details={"fields": [e.model_dump() for e in errors]},
        )

    @classmethod
    def not_found(cls, resource: str, resource_id: str) -> "ApiError":
        """Create not found error."""
        return cls(
            code=ApiErrorCode.NOT_FOUND,
            message=f"{resource} with ID '{resource_id}' not found",
        )
```

### Testing Requirements

- Test generic type serialization works with Pydantic 2.0
- Test pagination calculation (total_pages, has_next, has_prev)
- Test error response factory methods
- Verify JSON serialization matches expected format
- Use fixtures from root `tests/conftest.py`

### Dependencies

**This story requires:**
- Story 0.5.3 complete (BFF auth middleware exists)

**This story blocks:**
- Story 0.5.4b: BFF API Routes (needs response wrappers)

### References

| Document | Location | Relevant Sections |
|----------|----------|-------------------|
| ADR-012 | `_bmad-output/architecture/adr/ADR-012-bff-service-composition-api-design.md` | §4.1-4.3 Response patterns |
| Epic 0.5 | `_bmad-output/epics/epic-0-5-frontend.md` | Story 0.5.4a requirements |
| Project Context | `_bmad-output/project-context.md` | Python rules, Pydantic 2.0 patterns |
| Story 0.5.3 | `_bmad-output/sprint-artifacts/0-5-3-bff-auth-middleware.md` | Previous story patterns |

---

## E2E Story Checklist

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none expected - new code only) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green (Quality CI + E2E CI)
- [ ] If production code changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

(to be filled if issues arise)

### Completion Notes List

(to be filled after implementation)

### File List

**To Create:**
- `services/bff/src/bff/api/schemas/responses.py` - Response wrapper schemas
- `tests/unit/bff/test_response_schemas.py` - Unit tests for response schemas

**To Modify:**
- `services/bff/src/bff/api/schemas/__init__.py` - Add new exports
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` - Migrate 4 list methods
- `services/bff/src/bff/infrastructure/clients/collection_client.py` - Migrate 3 list methods
- `tests/unit/bff/test_plantation_client.py` - Update tests for new return types
- `tests/unit/bff/test_collection_client.py` - Update tests for new return types
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Update story status

---

## Code Review Record

### Review Date
(to be filled)

### Reviewer
(to be filled)

### Review Outcome
(to be filled)

### Findings Summary
(to be filled)

### Action Items
(to be filled)

### Verification
(to be filled)
