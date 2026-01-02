# Story 0.5.3: BFF Authentication Middleware (Dual-Mode)

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->
**Story Points:** 3

## Story

As a **backend developer**,
I want the BFF service to validate JWT tokens in both mock and B2C modes,
So that API endpoints are protected locally and in production.

## Acceptance Criteria

### AC1: Mock Mode Token Validation
**Given** `AUTH_PROVIDER=mock` is configured
**When** the middleware validates a token
**Then** JWT is validated using local HS256 secret (`MOCK_JWT_SECRET`)
**And** Token claims are extracted and available in request context
**And** Invalid tokens return 401 Unauthorized

### AC2: Azure B2C Mode Token Validation (Stub for Story 0.5.8)
**Given** `AUTH_PROVIDER=azure-b2c` is configured
**When** the middleware validates a token
**Then** JWT is validated against B2C JWKS endpoint (stub implementation)
**And** JWKS is cached for 24 hours (deferred to Story 0.5.8)
**And** Token claims are extracted identically to mock mode

### AC3: Token Claims Extraction
**Given** the JWT is validated (either mode)
**When** the middleware extracts claims
**Then** `TokenClaims` Pydantic model contains all user attributes
**And** Claims include: `sub`, `email`, `name`, `role`, `factory_id`, `factory_ids`, `collection_point_id`, `region_ids`, `permissions`
**And** Claims are added to OpenTelemetry trace context
**And** PII (email, name) is NOT logged

### AC4: Permission-Based Authorization
**Given** role-based authorization is needed
**When** I use the `@require_permission` decorator
**Then** Endpoints check specific permission (e.g., `farmers:read`)
**And** Platform admins bypass permission checks
**And** Unauthorized access returns 403 Forbidden

### AC5: Factory-Level Authorization
**Given** factory-level authorization is needed
**When** I use the `@require_factory_access` decorator
**Then** Users can only access their assigned factory's data
**And** Multi-factory users (owners) can access all their factories
**And** Regulators are blocked from factory-level data
**And** Platform admins bypass factory restriction

### AC6: Token Expiry Handling
**Given** a token is expired
**When** the client sends a request
**Then** 401 is returned with `token_expired` error code
**And** Client can refresh and retry

### AC7: Security Guardrail
**Given** mock mode is used in production build
**When** the app starts with `AUTH_PROVIDER=mock` and `APP_ENV=production`
**Then** Startup fails with configuration error (security guardrail)

## Tasks / Subtasks

- [ ] **Task 1: Directory Setup**
  - [ ] Create `services/bff/src/bff/api/middleware/__init__.py`
  - [ ] Create `services/bff/src/bff/api/schemas/__init__.py`

- [ ] **Task 2: TokenClaims Model** (AC: #3)
  - [ ] Create `services/bff/src/bff/api/schemas/auth.py` - TokenClaims Pydantic model
  - [ ] Define all claim fields with proper types and defaults
  - [ ] Add `from_jwt_payload()` class method for claim extraction
  - [ ] Add `AuthErrorCode` enum for consistent error codes

- [ ] **Task 3: JWT Validation Core** (AC: #1, #2, #6)
  - [ ] Add `python-jose[cryptography]>=3.3.0` to `pyproject.toml` dependencies
  - [ ] Create `services/bff/src/bff/api/middleware/auth.py` - Core auth module
  - [ ] Implement `validate_mock_token()` - HS256 validation with local secret
  - [ ] Implement `validate_azure_token()` - RS256 validation with JWKS (stub for now)
  - [ ] Implement `validate_token()` - Router that selects validator based on AUTH_PROVIDER
  - [ ] Handle expired tokens with specific error code

- [ ] **Task 4: Auth Dependencies** (AC: #3, #4, #5)
  - [ ] Implement `get_current_user()` FastAPI dependency
  - [ ] Implement `require_permission(permission: str)` decorator
  - [ ] Implement `require_factory_access` dependency
  - [ ] Add OTel trace context for user claims (exclude PII)

- [ ] **Task 5: Security Guardrail** (AC: #7)
  - [ ] Update `services/bff/src/bff/config.py` - Add `model_validator` for mock+production check
  - [ ] Use `model_validator(mode='after')` pattern (NOT field_validator)
  - [ ] Fail startup if mock mode in production environment

- [ ] **Task 6: Unit Tests** (AC: #1-7)
  - [ ] Add `create_mock_jwt_token()` helper to `tests/unit/bff/conftest.py`
  - [ ] Add `mock_auth_headers` fixture for authenticated requests
  - [ ] Create `tests/unit/bff/test_auth_middleware.py`
  - [ ] Test mock token validation (valid, invalid, expired)
  - [ ] Test permission decorator (allowed, denied, platform_admin bypass)
  - [ ] Test factory access decorator (own factory, other factory, multi-factory owner, regulator, platform_admin)
  - [ ] Test security guardrail (mock + production = fail)

- [ ] **Task 7: Verify E2E Infrastructure**
  - [ ] Verify BFF service uses mock mode for E2E tests (already configured)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.3: BFF Auth Middleware"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-3-bff-auth-middleware
  ```

**Branch name:** `story/0-5-3-bff-auth-middleware`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-3-bff-auth-middleware`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.3: BFF Auth Middleware" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-3-bff-auth-middleware`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src:libs/fp-common:services/bff/src" pytest tests/unit/bff/ -v
```
**Output:**
```
(paste test summary here - e.g., "XX passed in X.XXs")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (MUST use --build to rebuild images)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-5-3-bff-auth-middleware

# Wait ~30s, then check CI status
gh run list --branch story/0-5-3-bff-auth-middleware --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### What's Already Done (DO NOT DUPLICATE)

The following items already exist from Story 0.5.2 - do NOT recreate:

| Item | Location | Status |
|------|----------|--------|
| `auth_provider` config setting | `services/bff/src/bff/config.py:23` | ✅ Exists |
| `mock_jwt_secret` config setting | `services/bff/src/bff/config.py:24` | ✅ Exists |
| `MOCK_JWT_SECRET` E2E env var | `docker-compose.e2e.yaml:372` | ✅ Exists |
| `AUTH_PROVIDER=mock` E2E env var | `docker-compose.e2e.yaml:371` | ✅ Exists |

### Previous Story Intelligence (CRITICAL)

**From Story 0.5.2, the BFF service is now running with:**
- FastAPI application at port 8080
- Health endpoints `/health` and `/ready`
- DAPR sidecar with circuit breaker and retry policies
- OpenTelemetry tracing configured
- Clients for Plantation and Collection models already exist

**Directory structure established:**
```
services/bff/
├── src/bff/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   ├── middleware/          ← NEW: Create auth.py here
│   │   └── schemas/             ← NEW: Create auth.py here
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── clients/
│   │   │   ├── base.py
│   │   │   ├── plantation_client.py
│   │   │   └── collection_client.py
│   │   └── tracing.py
│   ├── services/                ← Story 0.5.4
│   └── transformers/            ← Story 0.5.4
├── dapr/
│   ├── config.yaml
│   └── resiliency.yaml
├── Dockerfile
└── pyproject.toml
```

**Code Review Findings from 0.5.2 to Apply:**
- Use `SettingsConfigDict` not deprecated dict format for model_config
- Add type hints with `TYPE_CHECKING` pattern for circular imports
- Remove duplicate fixtures from test files (use conftest.py)

### Architecture Requirements (ADR-003)

**Dual-Mode Authentication:**

| Mode | Validation | Secret | Use Case |
|------|------------|--------|----------|
| `mock` | HS256 local secret | `MOCK_JWT_SECRET` | Local dev, E2E tests |
| `azure-b2c` | RS256 with JWKS | Azure B2C public keys | Production |

**TokenClaims Model (from ADR-003 §321-392):**
```python
class TokenClaims(BaseModel):
    sub: str                              # User ID (Azure AD object ID)
    email: str
    name: str
    role: str                             # Primary role
    factory_id: Optional[str] = None      # Single factory assignment
    factory_ids: list[str] = []           # Multi-factory (owners)
    collection_point_id: Optional[str] = None  # For clerks
    region_ids: list[str] = []            # For regulators
    permissions: list[str] = []           # Computed permissions
```

**Authorization Decorators:**
| Decorator | Purpose | Example Usage |
|-----------|---------|---------------|
| `@require_permission("farmers:read")` | Check specific permission | Farmer list endpoint |
| `@require_factory_access` | Enforce factory isolation | All factory-scoped endpoints |

**Role Hierarchy (from ADR-003):**
```
platform_admin (bypasses all checks)
    ├── factory_owner (can do everything factory_manager can)
    │       ├── factory_manager (can do everything factory_viewer can)
    │       │       └── factory_viewer (read-only)
    │       └── factory_admin (settings only)
    └── registration_clerk (isolated to registration)

regulator (completely separate, no factory access)
```

### Mock User Personas (from ADR-003 §664-719)

**Use these for testing - copy directly into test fixtures:**

| ID | Name | Role | Factory | Key Permissions |
|----|------|------|---------|-----------------|
| `mock-manager-001` | Jane Mwangi | `factory_manager` | KEN-FAC-001 | farmers:read, quality_events:read, diagnoses:read, action_plans:read |
| `mock-owner-001` | John Ochieng | `factory_owner` | KEN-FAC-001, KEN-FAC-002 | + payment_policies:write, factory_settings:write |
| `mock-admin-001` | Admin User | `platform_admin` | (all) | `*` (wildcard) |
| `mock-clerk-001` | Mary Wanjiku | `registration_clerk` | KEN-FAC-001 + KEN-CP-001 | farmers:create |
| `mock-regulator-001` | TBK Inspector | `regulator` | regions: nandi, kericho | national_stats:read, regional_stats:read |

### Test Fixture Pattern (ADD to conftest.py)

```python
# tests/unit/bff/conftest.py - ADD these fixtures

from datetime import UTC, datetime, timedelta
from jose import jwt

MOCK_JWT_SECRET = "test-secret-for-unit-tests"

MOCK_USERS = {
    "factory_manager": {
        "sub": "mock-manager-001",
        "email": "jane@kericho-factory.test",
        "name": "Jane Mwangi",
        "role": "factory_manager",
        "factory_id": "KEN-FAC-001",
        "factory_ids": ["KEN-FAC-001"],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["farmers:read", "quality_events:read", "diagnoses:read", "action_plans:read"],
    },
    "factory_owner": {
        "sub": "mock-owner-001",
        "email": "john@owner.test",
        "name": "John Ochieng",
        "role": "factory_owner",
        "factory_id": "KEN-FAC-001",
        "factory_ids": ["KEN-FAC-001", "KEN-FAC-002"],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["farmers:read", "quality_events:read", "payment_policies:write", "factory_settings:write"],
    },
    "platform_admin": {
        "sub": "mock-admin-001",
        "email": "admin@farmerpower.test",
        "name": "Admin User",
        "role": "platform_admin",
        "factory_id": None,
        "factory_ids": [],
        "collection_point_id": None,
        "region_ids": [],
        "permissions": ["*"],
    },
    "regulator": {
        "sub": "mock-regulator-001",
        "email": "inspector@tbk.go.ke.test",
        "name": "TBK Inspector",
        "role": "regulator",
        "factory_id": None,
        "factory_ids": [],
        "collection_point_id": None,
        "region_ids": ["nandi", "kericho"],
        "permissions": ["national_stats:read", "regional_stats:read"],
    },
}

def create_mock_jwt_token(
    user_data: dict,
    secret: str = MOCK_JWT_SECRET,
    expires_delta: timedelta = timedelta(hours=1),
) -> str:
    """Create a mock JWT token for testing."""
    now = datetime.now(UTC)
    payload = {
        **user_data,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def mock_manager_token() -> str:
    """JWT token for factory_manager user."""
    return create_mock_jwt_token(MOCK_USERS["factory_manager"])

@pytest.fixture
def mock_admin_token() -> str:
    """JWT token for platform_admin user."""
    return create_mock_jwt_token(MOCK_USERS["platform_admin"])

@pytest.fixture
def mock_regulator_token() -> str:
    """JWT token for regulator user."""
    return create_mock_jwt_token(MOCK_USERS["regulator"])

@pytest.fixture
def expired_token() -> str:
    """Expired JWT token for testing expiry handling."""
    return create_mock_jwt_token(
        MOCK_USERS["factory_manager"],
        expires_delta=timedelta(hours=-1),  # Already expired
    )
```

### AuthErrorCode Enum (ADD to schemas/auth.py)

```python
from enum import Enum

class AuthErrorCode(str, Enum):
    """Standardized auth error codes for consistent API responses."""
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "invalid_token"
    TOKEN_MISSING = "missing_token"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    FACTORY_ACCESS_DENIED = "factory_access_denied"
    REGULATOR_RESTRICTED = "regulator_restricted"
```

### Implementation Patterns

**JWT Validation Pattern:**
```python
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> TokenClaims:
    """Validate JWT - supports both mock and Azure B2C."""
    try:
        if settings.auth_provider == "mock":
            payload = jwt.decode(
                credentials.credentials,
                settings.mock_jwt_secret,
                algorithms=["HS256"]
            )
        else:
            # Azure B2C - stub for now (Story 0.5.8)
            payload = await validate_azure_b2c_token(
                credentials.credentials,
                settings
            )

        return TokenClaims.from_jwt_payload(payload)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "token_expired", "message": "Token has expired"}
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Invalid token"}
        )
```

**Permission Decorator Pattern:**
```python
def require_permission(permission: str):
    """Decorator to check permission."""
    async def checker(user: TokenClaims = Depends(get_current_user)) -> TokenClaims:
        # Platform admins bypass all permission checks
        if user.role == "platform_admin":
            return user

        # Check for wildcard permission
        if "*" in user.permissions:
            return user

        # Check specific permission
        if permission not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail={"code": "insufficient_permissions", "message": f"Requires {permission}"}
            )
        return user
    return Depends(checker)
```

**Factory Access Pattern:**
```python
def require_factory_access(factory_id: str | None = None):
    """Ensure user has access to the requested factory."""
    async def checker(
        user: TokenClaims = Depends(get_current_user),
        path_factory_id: str = Path(alias="factory_id"),
    ) -> TokenClaims:
        target_factory = factory_id or path_factory_id

        # Platform admins can access all
        if user.role == "platform_admin":
            return user

        # Regulators cannot access factory data
        if user.role == "regulator":
            raise HTTPException(
                status_code=403,
                detail={"code": "regulator_restricted", "message": "Regulators cannot access factory data"}
            )

        # Check factory access
        allowed = user.factory_ids or ([user.factory_id] if user.factory_id else [])
        if target_factory not in allowed:
            raise HTTPException(
                status_code=403,
                detail={"code": "factory_access_denied", "message": "No access to this factory"}
            )

        return user
    return Depends(checker)
```

### pyproject.toml Update

Add `python-jose` dependency for JWT handling:

```toml
[project]
dependencies = [
    # ... existing deps
    "python-jose[cryptography]>=3.3.0",  # JWT validation
]
```

### Config Updates (Security Guardrail)

Add `model_validator` to existing config.py - **use `mode='after'` NOT `field_validator`**:

```python
# services/bff/src/bff/config.py - ADD this import and validator
from pydantic import model_validator

class Settings(BaseSettings):
    # ... existing settings already present ...

    # Azure B2C settings (Story 0.5.8) - ADD these
    b2c_tenant: str = ""
    b2c_client_id: str = ""

    @model_validator(mode='after')
    def validate_no_mock_in_production(self) -> 'Settings':
        """Security guardrail: prevent mock auth in production."""
        if self.auth_provider == "mock" and self.app_env == "production":
            raise ValueError(
                "SECURITY ERROR: Mock auth provider cannot be used in production. "
                "Set AUTH_PROVIDER=azure-b2c for production deployments."
            )
        return self
```

**⚠️ WARNING:** Do NOT use `@field_validator` for this check - it doesn't work in Pydantic v2 because `info.data` only contains fields validated alphabetically before the current field.

### OpenTelemetry Context

Add user context to traces (without PII):

```python
from opentelemetry import trace

def add_user_to_trace(user: TokenClaims) -> None:
    """Add user context to current span (no PII)."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("user.id", user.sub)
        span.set_attribute("user.role", user.role)
        if user.factory_id:
            span.set_attribute("user.factory_id", user.factory_id)
        # DO NOT add email or name (PII)
```

### Dependencies

**This story requires:**
- Story 0.5.2 complete (BFF service scaffold exists) ✅

**This story blocks:**
- Story 0.5.4: BFF API Routes

### References

| Document | Location | Relevant Sections |
|----------|----------|-------------------|
| ADR-003 IAM | `_bmad-output/architecture/adr/ADR-003-identity-access-management.md` | §321-392 (TokenClaims), §595-804 (Mock Auth), §721-751 (BFF Validation) |
| Epic 0.5 | `_bmad-output/epics/epic-0-5-frontend.md` | Story 0.5.3 requirements |
| Project Context | `_bmad-output/project-context.md` | Python rules, Pydantic 2.0 patterns |
| Story 0.5.2 | `_bmad-output/sprint-artifacts/0-5-2-bff-service-setup.md` | Previous story learnings |

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
| (none) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Infrastructure/Integration Changes (if any)
If you modified mock servers, docker-compose, env vars, or seed data that affects service behavior:

| File | What Changed | Why | Impact |
|------|--------------|-----|--------|
| (none expected - E2E already configured) | | | |

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
