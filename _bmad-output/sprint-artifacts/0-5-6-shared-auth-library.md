# Story 0.5.6: Shared Auth Library (Mock-First)

**Status:** done
**GitHub Issue:** #84

## Story

As a **frontend developer**,
I want **a shared authentication library with swappable providers**,
So that **all frontend apps work with mock auth locally and Azure B2C in production**.

## Acceptance Criteria

1. **Package Setup (AC1)**:
   - `libs/auth/` package exports as `@fp/auth` via npm workspaces
   - TypeScript configured with strict mode
   - Vitest configured for component testing
   - Package builds with Vite in library mode (same pattern as @fp/ui-components)

2. **Auth Provider Architecture (AC2)**:
   - `AuthProvider` component wraps apps and provides auth context
   - `MockAuthProvider` active when `VITE_AUTH_PROVIDER=mock`
   - `AzureB2CAuthProvider` stub created (full implementation in Story 0.5.8)
   - Provider selection happens at runtime via environment variable

3. **Mock Authentication (AC3)**:
   - `MockLoginSelector` component shows available personas as dropdown/buttons
   - On persona selection, JWT is generated with HS256 signing using `VITE_MOCK_JWT_SECRET`
   - JWT claims match BFF `TokenClaims` structure exactly
   - Tokens stored in localStorage (dev only)
   - Logout clears localStorage

4. **Mock User Personas (AC4)**:
   - 5 personas available matching ADR-003 specification:
     - `mock-manager-001`: Jane Mwangi (factory_manager, KEN-FAC-001)
     - `mock-owner-001`: John Ochieng (factory_owner, KEN-FAC-001 + KEN-FAC-002)
     - `mock-admin-001`: Admin User (platform_admin, all access)
     - `mock-clerk-001`: Mary Wanjiku (registration_clerk, KEN-FAC-001 + KEN-CP-001)
     - `mock-regulator-001`: TBK Inspector (regulator, nandi + kericho regions)
   - Each persona has complete permissions per role definition

5. **useAuth Hook (AC5)**:
   - `isAuthenticated: boolean` - whether user is logged in
   - `user: User | null` - current user object matching TokenClaims
   - `login(): void` - trigger login (mock: show selector, B2C: redirect)
   - `logout(): Promise<void>` - clear session and tokens
   - `getAccessToken(): Promise<string>` - get token for API calls
   - `isLoading: boolean` - true while checking auth state

6. **usePermission Hook (AC6)**:
   - `const canEdit = usePermission('sms_templates:write')` syntax
   - Returns `true` for platform_admin (wildcard permissions)
   - Checks `permissions` array in user claims
   - Returns `false` if not authenticated

7. **ProtectedRoute Component (AC7)**:
   - `<ProtectedRoute roles={['factory_manager', 'factory_owner']}>` syntax
   - Redirects to login if not authenticated
   - Shows access denied if authenticated but wrong role
   - Shows loading state during auth check
   - Optional `permissions` prop for finer control

8. **Testing (AC8)**:
   - Unit tests for all hooks and components in `tests/unit/web/`
   - Tests cover: login flow, logout, token generation, permission checks
   - Tests verify JWT structure matches BFF expectations
   - All tests pass with `npm run test`

9. **Type Exports (AC9)**:
   - `User` type exported (matches TokenClaims)
   - `AuthContextValue` type exported
   - `MockUser` type exported
   - `AuthProviderProps` type exported

## Tasks / Subtasks

- [x] **Task 1: Initialize Package Structure** (AC: #1)
  - [x] 1.1 Create `libs/auth/` directory structure
  - [x] 1.2 Create `package.json` with name `@fp/auth`
  - [x] 1.3 Configure `tsconfig.json` with strict mode
  - [x] 1.4 Configure `vite.config.ts` for library build
  - [x] 1.5 Configure `vitest.config.ts` for testing
  - [x] 1.6 Add to root `package.json` workspaces array

- [x] **Task 2: Create Type Definitions** (AC: #9)
  - [x] 2.1 Create `src/types.ts` with User, AuthContextValue types
  - [x] 2.2 Ensure User type matches BFF TokenClaims exactly
  - [x] 2.3 Export all types from `src/index.ts`

- [x] **Task 3: Implement Mock User Personas** (AC: #4)
  - [x] 3.1 Create `src/mock/users.ts` with MOCK_USERS array
  - [x] 3.2 Define all 5 personas with complete attributes
  - [x] 3.3 Include permissions array for each role

- [x] **Task 4: Implement JWT Generation** (AC: #3)
  - [x] 4.1 Create `src/mock/jwt.ts` with generateMockToken function
  - [x] 4.2 Sign JWT with HS256 using VITE_MOCK_JWT_SECRET
  - [x] 4.3 Include all claims matching BFF TokenClaims
  - [x] 4.4 Set expiry to 1 hour (configurable)

- [x] **Task 5: Implement AuthContext** (AC: #2, #5)
  - [x] 5.1 Create `src/context/AuthContext.tsx` with context definition
  - [x] 5.2 Implement state management for user, token, loading
  - [x] 5.3 Create context provider with login/logout functions

- [x] **Task 6: Implement MockAuthProvider** (AC: #2, #3)
  - [x] 6.1 Create `src/providers/MockAuthProvider.tsx`
  - [x] 6.2 Implement localStorage token persistence
  - [x] 6.3 Auto-restore session from localStorage on mount
  - [x] 6.4 Implement login (generate token), logout (clear storage)

- [x] **Task 7: Create AzureB2CAuthProvider Stub** (AC: #2)
  - [x] 7.1 Create `src/providers/AzureB2CAuthProvider.tsx`
  - [x] 7.2 Implement stub that throws "Not implemented" error
  - [x] 7.3 Add TODO comment pointing to Story 0.5.8

- [x] **Task 8: Implement AuthProvider Wrapper** (AC: #2)
  - [x] 8.1 Create `src/providers/AuthProvider.tsx`
  - [x] 8.2 Read VITE_AUTH_PROVIDER environment variable
  - [x] 8.3 Render MockAuthProvider or AzureB2CAuthProvider based on config
  - [x] 8.4 Block mock provider in production (APP_ENV check)

- [x] **Task 9: Implement MockLoginSelector** (AC: #3)
  - [x] 9.1 Create `src/components/MockLoginSelector.tsx`
  - [x] 9.2 Display personas as buttons with role badge, name, factory
  - [x] 9.3 Call onSelect callback with selected persona
  - [x] 9.4 Style with basic CSS (not MUI dependency)

- [x] **Task 10: Implement useAuth Hook** (AC: #5)
  - [x] 10.1 Create `src/hooks/useAuth.ts`
  - [x] 10.2 Return isAuthenticated, user, login, logout, getAccessToken, isLoading
  - [x] 10.3 Use React.useContext to access AuthContext

- [x] **Task 11: Implement usePermission Hook** (AC: #6)
  - [x] 11.1 Create `src/hooks/usePermission.ts`
  - [x] 11.2 Check permissions array in user claims
  - [x] 11.3 Handle platform_admin wildcard ("*")
  - [x] 11.4 Return false if not authenticated

- [x] **Task 12: Implement ProtectedRoute** (AC: #7)
  - [x] 12.1 Create `src/components/ProtectedRoute.tsx`
  - [x] 12.2 Check authentication status
  - [x] 12.3 Check role membership
  - [x] 12.4 Render loading state, access denied, or children
  - [x] 12.5 Accept optional permissions prop

- [x] **Task 13: Configure Exports** (AC: #1, #9)
  - [x] 13.1 Create `src/index.ts` with all public exports
  - [x] 13.2 Configure `package.json` exports field for tree-shaking
  - [x] 13.3 Verify build output with `npm run build`

- [x] **Task 14: Create Unit Tests** (AC: #8)
  - [x] 14.1 Create `tests/unit/web/test_auth_provider.test.tsx`
  - [x] 14.2 Create `tests/unit/web/test_use_auth.test.tsx`
  - [x] 14.3 Create `tests/unit/web/test_use_permission.test.tsx`
  - [x] 14.4 Create `tests/unit/web/test_protected_route.test.tsx`
  - [x] 14.5 Create `tests/unit/web/test_mock_jwt.test.ts`
  - [x] 14.6 All tests pass with `npm run test`

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.6: Shared Auth Library"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-6-shared-auth-library
  ```

**Branch name:** `story/0-5-6-shared-auth-library`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-6-shared-auth-library`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.6: Shared Auth Library" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-6-shared-auth-library`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
cd libs/auth && npm run test
```
**Output:**
```
 RUN  v2.1.9 /Users/jeanlouistournay/wks-farmerpower/farmer-power-platform/libs/auth

 ✓ ../../tests/unit/web/test_mock_jwt.test.ts (10 tests) 115ms
 ✓ ../../tests/unit/web/test_protected_route.test.tsx (10 tests) 110ms
 ✓ ../../tests/unit/web/test_use_permission.test.tsx (9 tests) 157ms
 ✓ ../../tests/unit/web/test_use_auth.test.tsx (6 tests) 168ms
 ✓ ../../tests/unit/web/test_auth_provider.test.tsx (10 tests) 235ms

 Test Files  5 passed (5)
      Tests  45 passed (45)
   Start at  16:58:15
   Duration  2.25s
```

### 2. Library Build
```bash
cd libs/auth && npm run build
```
**Output:**
```
vite v6.4.1 building for production...
✓ 94 modules transformed.
dist/index.js  42.19 kB │ gzip: 10.77 kB
dist/index.cjs  31.33 kB │ gzip: 9.56 kB
✓ built in 3.54s
```
**Build passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
cd libs/auth && npm run lint
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-5-6-shared-auth-library

# Wait ~30s, then check CI status
gh run list --branch feature/0-5-6-shared-auth-library --limit 3
```
**CI Run ID:** 20679638479
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-03

---

## Dev Notes

### CRITICAL: This is the Authentication Foundation

This story creates the authentication infrastructure for ALL frontend work. Pay extra attention to:

1. **Token Structure**: JWT claims MUST match BFF `TokenClaims` exactly (Story 0.5.3)
2. **Type Safety**: Strict TypeScript - no `any` types
3. **Testing**: Comprehensive coverage of auth flows
4. **Security**: Never log tokens, PII; block mock in production

### Directory Structure (MUST FOLLOW EXACTLY)

```
libs/auth/
├── src/
│   ├── components/
│   │   ├── MockLoginSelector.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── index.ts
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   └── index.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── usePermission.ts
│   │   └── index.ts
│   ├── mock/
│   │   ├── jwt.ts
│   │   ├── users.ts
│   │   └── index.ts
│   ├── providers/
│   │   ├── AuthProvider.tsx
│   │   ├── MockAuthProvider.tsx
│   │   ├── AzureB2CAuthProvider.tsx
│   │   └── index.ts
│   ├── types.ts
│   └── index.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
└── eslint.config.js
```

[Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#Frontend-Auth-Library]

### TokenClaims Type (MUST MATCH BFF EXACTLY)

```typescript
// src/types.ts
export interface User {
  sub: string;                        // User ID (Azure AD object ID)
  email: string;
  name: string;
  role: string;                       // Primary role
  factory_id: string | null;          // Single factory assignment
  factory_ids: string[];              // Multi-factory (owners)
  collection_point_id: string | null; // For clerks
  region_ids: string[];               // For regulators
  permissions: string[];              // Computed permissions
}
```

**BFF Reference:** `services/bff/src/bff/api/middleware/auth.py` TokenClaims model

[Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#JWT-Token-Claims]

### Mock User Personas (MANDATORY - ALL 5)

| ID | Name | Role | Factory | Permissions |
|----|------|------|---------|-------------|
| mock-manager-001 | Jane Mwangi | factory_manager | KEN-FAC-001 | farmers:read, quality_events:read, diagnoses:read, action_plans:read |
| mock-owner-001 | John Ochieng | factory_owner | KEN-FAC-001, KEN-FAC-002 | + payment_policies:write, factory_settings:write |
| mock-admin-001 | Admin User | platform_admin | (all) | * (wildcard) |
| mock-clerk-001 | Mary Wanjiku | registration_clerk | KEN-FAC-001 + KEN-CP-001 | farmers:create |
| mock-regulator-001 | TBK Inspector | regulator | regions: nandi, kericho | national_stats:read, regional_stats:read |

[Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#Mock-User-Personas]

### JWT Generation (Mock Mode)

```typescript
// src/mock/jwt.ts
import { SignJWT } from 'jose';

export async function generateMockToken(user: MockUser): Promise<string> {
  const secret = new TextEncoder().encode(import.meta.env.VITE_MOCK_JWT_SECRET);

  const token = await new SignJWT({
    sub: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    factory_id: user.factory_id,
    factory_ids: user.factory_ids,
    collection_point_id: user.collection_point_id,
    region_ids: user.region_ids,
    permissions: user.permissions,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('1h')
    .setIssuer('mock-auth')
    .setAudience('farmer-power-bff')
    .sign(secret);

  return token;
}
```

[Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#BFF-Mock-Token-Validation]

### Package.json Configuration

```json
{
  "name": "@fp/auth",
  "version": "0.1.0",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js",
      "require": "./dist/index.cjs"
    }
  },
  "files": ["dist"],
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "dependencies": {
    "jose": "^5.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "@typescript-eslint/parser": "^8.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^9.0.0",
    "jsdom": "^25.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vite-plugin-dts": "^4.4.0",
    "vitest": "^2.1.0"
  }
}
```

### Environment Variables

```bash
# Development (.env.local)
VITE_AUTH_PROVIDER=mock
VITE_MOCK_JWT_SECRET=local-dev-secret-key-32-chars-min

# Production (.env.production)
VITE_AUTH_PROVIDER=azure-b2c
# B2C config added in Story 0.5.8
```

### MockLoginSelector Component

```tsx
// src/components/MockLoginSelector.tsx
import { MOCK_USERS } from '../mock/users';
import type { MockUser } from '../types';

interface MockLoginSelectorProps {
  onSelect: (user: MockUser) => void;
}

export function MockLoginSelector({ onSelect }: MockLoginSelectorProps) {
  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: '0 auto' }}>
      <h3 style={{ marginBottom: '16px' }}>Select Test User</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {MOCK_USERS.map(user => (
          <button
            key={user.id}
            onClick={() => onSelect(user)}
            style={{
              padding: '12px 16px',
              border: '1px solid #ccc',
              borderRadius: '6px',
              cursor: 'pointer',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}
          >
            <span style={{
              padding: '2px 8px',
              backgroundColor: getRoleBadgeColor(user.role),
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {user.role}
            </span>
            <span>{user.name}</span>
            {user.factory_id && (
              <span style={{ color: '#666', fontSize: '12px' }}>
                {user.factory_id}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function getRoleBadgeColor(role: string): string {
  switch (role) {
    case 'platform_admin': return '#fce7f3';
    case 'factory_owner': return '#dbeafe';
    case 'factory_manager': return '#d1fae5';
    case 'registration_clerk': return '#fef3c7';
    case 'regulator': return '#e0e7ff';
    default: return '#f3f4f6';
  }
}
```

### ProtectedRoute Component

```tsx
// src/components/ProtectedRoute.tsx
import { ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: ReactNode;
  roles?: string[];
  permissions?: string[];
  fallback?: ReactNode;
  accessDenied?: ReactNode;
}

export function ProtectedRoute({
  children,
  roles,
  permissions,
  fallback = <div>Loading...</div>,
  accessDenied = <div>Access Denied</div>,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user, login } = useAuth();

  if (isLoading) {
    return <>{fallback}</>;
  }

  if (!isAuthenticated) {
    // Redirect to login
    login();
    return <>{fallback}</>;
  }

  // Check role access
  if (roles && roles.length > 0) {
    const hasRole = user?.role && roles.includes(user.role);
    const isPlatformAdmin = user?.role === 'platform_admin';
    if (!hasRole && !isPlatformAdmin) {
      return <>{accessDenied}</>;
    }
  }

  // Check permission access
  if (permissions && permissions.length > 0) {
    const hasPermission = permissions.every(
      p => user?.permissions.includes(p) || user?.permissions.includes('*')
    );
    if (!hasPermission) {
      return <>{accessDenied}</>;
    }
  }

  return <>{children}</>;
}
```

### Previous Story Intelligence

**From Story 0.5.5 (Shared Component Library):**
- Package structure pattern established in `libs/ui-components/`
- npm workspaces configured in root `package.json`
- Vite library build configuration pattern
- Test file location: `tests/unit/web/`
- ESLint flat config (eslint.config.js)
- TypeScript strict mode enabled

**From Story 0.5.3 (BFF Auth Middleware):**
- BFF validates JWT with same HS256 secret
- TokenClaims model defines exact claim structure
- Mock mode activated via `AUTH_PROVIDER=mock`
- Security guardrail: mock blocked in production

### Git History Insights

Recent commits show:
- Story 0.5.5 merged with 57 component tests
- BFF farmer API routes complete (0.5.4b)
- CI workflow updated for frontend testing

### Anti-Patterns to Avoid

1. **DO NOT** log tokens or PII (sub, email, name)
2. **DO NOT** allow mock provider in production builds
3. **DO NOT** hardcode JWT secrets
4. **DO NOT** create MUI dependencies (keep lightweight)
5. **DO NOT** skip any of the 5 mock personas
6. **DO NOT** diverge from BFF TokenClaims structure
7. **DO NOT** store tokens in sessionStorage (use localStorage for dev persistence)
8. **DO NOT** forget to handle token expiry gracefully

### Files to Create

| Path | Purpose |
|------|---------|
| `libs/auth/package.json` | Package manifest |
| `libs/auth/tsconfig.json` | TypeScript config |
| `libs/auth/vite.config.ts` | Vite library build |
| `libs/auth/vitest.config.ts` | Test runner config |
| `libs/auth/eslint.config.js` | ESLint flat config |
| `libs/auth/src/index.ts` | Public exports |
| `libs/auth/src/types.ts` | Type definitions |
| `libs/auth/src/context/AuthContext.tsx` | Auth context |
| `libs/auth/src/providers/AuthProvider.tsx` | Provider wrapper |
| `libs/auth/src/providers/MockAuthProvider.tsx` | Mock implementation |
| `libs/auth/src/providers/AzureB2CAuthProvider.tsx` | B2C stub |
| `libs/auth/src/hooks/useAuth.ts` | Main auth hook |
| `libs/auth/src/hooks/usePermission.ts` | Permission hook |
| `libs/auth/src/components/ProtectedRoute.tsx` | Route guard |
| `libs/auth/src/components/MockLoginSelector.tsx` | Mock login UI |
| `libs/auth/src/mock/users.ts` | Mock personas |
| `libs/auth/src/mock/jwt.ts` | JWT generation |
| `tests/unit/web/test_auth_provider.test.tsx` | Provider tests |
| `tests/unit/web/test_use_auth.test.tsx` | Hook tests |
| `tests/unit/web/test_use_permission.test.tsx` | Permission tests |
| `tests/unit/web/test_protected_route.test.tsx` | Route tests |
| `tests/unit/web/test_mock_jwt.test.ts` | JWT tests |

### Files to Modify

| Path | Change |
|------|--------|
| `package.json` (root) | Add `libs/auth` to workspaces |
| `.github/workflows/ci.yaml` | Add auth library test job (if needed) |

### References

- [Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md]
- [Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#Frontend-Auth-Library]
- [Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#Mock-User-Personas]
- [Source: _bmad-output/architecture/adr/ADR-003-identity-access-management.md#Development-Authentication-Strategy]
- [Source: _bmad-output/epics/epic-0-5-frontend.md#Story-0.5.6]
- [Source: _bmad-output/project-context.md]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed jsdom TextEncoder issue by switching to happy-dom environment
- Fixed React state update during render in ProtectedRoute by using useEffect
- Fixed localStorage persistence between tests by handling both states in test patterns

### Completion Notes List

- Implemented complete @fp/auth shared authentication library
- All 5 mock user personas match ADR-003 specification
- JWT generation uses jose library with HS256 signing
- MockAuthProvider handles localStorage persistence
- AzureB2CAuthProvider stub ready for Story 0.5.8
- AuthProvider wrapper with environment-based provider selection
- useAuth hook provides full auth state and actions
- usePermission hook supports permission checks with admin wildcard
- ProtectedRoute component supports role and permission-based access
- 45 unit tests covering all components and hooks

### File List

**Created:**
- libs/auth/package.json
- libs/auth/tsconfig.json
- libs/auth/vite.config.ts
- libs/auth/vitest.config.ts
- libs/auth/eslint.config.js
- libs/auth/src/index.ts
- libs/auth/src/types.ts
- libs/auth/src/test-setup.ts
- libs/auth/src/mock/users.ts
- libs/auth/src/mock/jwt.ts
- libs/auth/src/mock/index.ts
- libs/auth/src/context/AuthContext.tsx
- libs/auth/src/context/index.ts
- libs/auth/src/providers/MockAuthProvider.tsx
- libs/auth/src/providers/AzureB2CAuthProvider.tsx
- libs/auth/src/providers/AuthProvider.tsx
- libs/auth/src/providers/index.ts
- libs/auth/src/hooks/useAuth.ts
- libs/auth/src/hooks/usePermission.ts
- libs/auth/src/hooks/index.ts
- libs/auth/src/components/MockLoginSelector.tsx
- libs/auth/src/components/ProtectedRoute.tsx
- libs/auth/src/components/index.ts
- tests/unit/web/test_mock_jwt.test.ts
- tests/unit/web/test_use_auth.test.tsx
- tests/unit/web/test_use_permission.test.tsx
- tests/unit/web/test_protected_route.test.tsx
- tests/unit/web/test_auth_provider.test.tsx

**Modified:**
- package.json (root) - Added libs/auth to workspaces array
- package-lock.json - Updated dependency lock file
- _bmad-output/sprint-artifacts/sprint-status.yaml - Updated story status
- .github/workflows/ci.yaml - Added @fp/auth to frontend tests job
- libs/ui-components/vitest.config.ts - Excluded auth tests (run by @fp/auth config)
