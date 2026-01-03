# Story 0.5.7: Factory Portal Scaffold

**Status:** in-progress
**GitHub Issue:** #86

## Story

As a **frontend developer**,
I want **the Factory Portal React application scaffolded with routing and layout**,
So that **Factory Manager, Owner, and Admin screens can be built**.

## Acceptance Criteria

1. **Project Setup (AC1)**:
   - `web/factory-portal/` directory created with Vite + React + TypeScript
   - `@fp/ui-components` and `@fp/auth` configured as workspace dependencies
   - ESLint and Prettier configured matching project patterns
   - TypeScript strict mode enabled
   - Package builds with `npm run build` (bundle < 500KB gzipped)

2. **Routing Configuration (AC2)**:
   - React Router v6 configured with routes:
     - `/` redirects to `/command-center`
     - `/command-center` (Factory Manager dashboard)
     - `/farmers/:id` (Farmer Detail)
     - `/roi` (Factory Owner ROI)
     - `/settings/*` (Factory Admin)
   - Routes protected by `ProtectedRoute` from `@fp/auth`
   - Unknown routes show 404 page
   - Role-based route guards enforced

3. **Layout Implementation (AC3)**:
   - App Shell with Sidebar navigation and Header
   - Sidebar shows role-appropriate menu items (factory_manager, factory_owner, factory_admin)
   - Header shows user name and factory name from auth context
   - Logout button available in header
   - Layout is responsive using MUI breakpoints

4. **Placeholder Pages (AC4)**:
   - Each route has a placeholder component
   - Placeholders show page title and "Coming soon" message
   - Placeholders demonstrate layout integration
   - Pages: CommandCenter, FarmerDetail, ROISummary, Settings

5. **Development Server (AC5)**:
   - `npm run dev` starts development server with HMR
   - API proxy configured: `/api` -> `http://localhost:8080` (BFF service)
   - Environment variables loaded from `.env.local`

6. **Build Output (AC6)**:
   - Production bundle generated with `npm run build`
   - Bundle size < 500KB (gzipped, excluding node_modules)
   - Source maps generated for debugging
   - Output in `dist/` directory

7. **Testing (AC7)**:
   - Vitest configured for component testing
   - Tests in `tests/unit/web/factory-portal/`
   - Test coverage: App mounting, routing, layout rendering
   - All tests pass with `npm run test`

8. **Docker Configuration (AC8)**:
   - Dockerfile created for production build
   - Multi-stage build with nginx for serving static files
   - Dockerfile follows project patterns

## Tasks / Subtasks

- [x] **Task 1: Initialize Project Structure** (AC: #1)
  - [x] 1.1 Create `web/factory-portal/` directory
  - [x] 1.2 Initialize with `npm create vite@latest` (React + TypeScript)
  - [x] 1.3 Create `package.json` with workspace dependencies
  - [x] 1.4 Configure `tsconfig.json` with strict mode
  - [x] 1.5 Configure `vite.config.ts` with React plugin and path aliases
  - [x] 1.6 Add to root `package.json` workspaces array
  - [x] 1.7 Configure `eslint.config.js` matching project pattern

- [x] **Task 2: Configure Dependencies** (AC: #1)
  - [x] 2.1 Add `@fp/ui-components` as workspace dependency
  - [x] 2.2 Add `@fp/auth` as workspace dependency
  - [x] 2.3 Add React Router v6: `react-router-dom`
  - [x] 2.4 Add Material UI v6: `@mui/material`, `@emotion/react`, `@emotion/styled`
  - [x] 2.5 Run `npm install` from root to link workspaces

- [x] **Task 3: Create App Shell Layout** (AC: #3)
  - [x] 3.1 Create `src/components/Layout/Layout.tsx` - main app shell
  - [x] 3.2 Create `src/components/Sidebar/Sidebar.tsx` - navigation sidebar
  - [x] 3.3 Create `src/components/Header/Header.tsx` - app header with user info
  - [x] 3.4 Implement responsive layout using MUI Box/Grid
  - [x] 3.5 Style with @fp/ui-components theme

- [x] **Task 4: Implement Routing** (AC: #2)
  - [x] 4.1 Create `src/app/routes.tsx` with route definitions
  - [x] 4.2 Configure React Router BrowserRouter in `src/app/App.tsx`
  - [x] 4.3 Implement role-based route protection using `ProtectedRoute` from @fp/auth
  - [x] 4.4 Create `src/pages/NotFound.tsx` for 404 handling
  - [x] 4.5 Configure redirect from `/` to `/command-center`

- [x] **Task 5: Create Placeholder Pages** (AC: #4)
  - [x] 5.1 Create `src/pages/manager/CommandCenter/CommandCenter.tsx`
  - [x] 5.2 Create `src/pages/manager/FarmerDetail/FarmerDetail.tsx`
  - [x] 5.3 Create `src/pages/owner/ROISummary/ROISummary.tsx`
  - [x] 5.4 Create `src/pages/admin/Settings/Settings.tsx`
  - [x] 5.5 Each placeholder shows title and "Coming soon" message

- [x] **Task 6: Configure Providers** (AC: #1, #3)
  - [x] 6.1 Create `src/app/providers/ThemeProvider.tsx` wrapping MUI ThemeProvider
  - [x] 6.2 Import and use theme from `@fp/ui-components`
  - [x] 6.3 Create `src/app/providers/AuthProviderWrapper.tsx` using `@fp/auth`
  - [x] 6.4 Compose providers in `src/main.tsx`

- [x] **Task 7: Configure Dev Server** (AC: #5)
  - [x] 7.1 Configure Vite proxy for `/api` -> BFF service
  - [x] 7.2 Create `.env.local.example` with required environment variables
  - [x] 7.3 Configure HMR and fast refresh
  - [x] 7.4 Test development server with `npm run dev`

- [x] **Task 8: Configure Build** (AC: #6)
  - [x] 8.1 Configure Vite build output
  - [x] 8.2 Verify bundle size < 500KB gzipped
  - [x] 8.3 Configure source map generation
  - [x] 8.4 Test production build with `npm run build && npm run preview`

- [x] **Task 9: Create Dockerfile** (AC: #8)
  - [x] 9.1 Create `web/factory-portal/Dockerfile`
  - [x] 9.2 Multi-stage build: node for build, nginx for serving
  - [x] 9.3 Configure nginx for SPA routing (fallback to index.html)
  - [ ] 9.4 Test Docker build locally (deferred - visual validation first)

- [x] **Task 10: Create Unit Tests** (AC: #7)
  - [x] 10.1 Configure `vitest.config.ts`
  - [x] 10.2 Create `tests/unit/web/factory-portal/test_app.test.tsx`
  - [x] 10.3 Create `tests/unit/web/factory-portal/test_routing.test.tsx`
  - [x] 10.4 Create `tests/unit/web/factory-portal/test_layout.test.tsx`
  - [x] 10.5 All tests pass with `npm run test`

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 0.5.7: Factory Portal Scaffold"`
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-7-factory-portal-scaffold
  ```

**Branch name:** `story/0-5-7-factory-portal-scaffold`

### During Development
- [x] All commits reference GitHub issue: `Relates to #86`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-7-factory-portal-scaffold`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.7: Factory Portal Scaffold" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-7-factory-portal-scaffold`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
cd web/factory-portal && npm run test
```
**Output:**
```
 RUN  v2.1.9 /Users/jeanlouistournay/wks-farmerpower/farmer-power-platform/web/factory-portal

 ✓ ../../tests/unit/web/factory-portal/test_app.test.tsx (5 tests) 240ms
 ✓ ../../tests/unit/web/factory-portal/test_routing.test.tsx (12 tests) 277ms
 ✓ ../../tests/unit/web/factory-portal/test_layout.test.tsx (15 tests) 363ms

 Test Files  3 passed (3)
      Tests  32 passed (32)
   Start at  17:53:36
   Duration  4.09s
```

### 2. Build Verification
```bash
cd web/factory-portal && npm run build
```
**Output:**
```
vite v6.4.1 building for production...
transforming...
✓ 954 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.64 kB │ gzip:  0.35 kB
dist/assets/index-CrfbgZKF.js   132.69 kB │ gzip: 43.99 kB │ map: 509.63 kB
dist/assets/vendor-RVwsST1e.js  176.67 kB │ gzip: 58.18 kB │ map: 763.14 kB
dist/assets/mui-D7C8sUMF.js     177.89 kB │ gzip: 54.95 kB │ map: 874.85 kB
✓ built in 10.12s

Total gzipped: ~157 KB (index: 43.99 + vendor: 58.18 + mui: 54.95)
```
**Bundle size < 500KB gzipped:** [x] Yes / [ ] No

### 3. Lint Check
```bash
cd web/factory-portal && npm run lint
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-5-7-factory-portal-scaffold

# Wait ~30s, then check CI status
gh run list --branch story/0-5-7-factory-portal-scaffold --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

### 5. E2E Tests

> **N/A - Frontend-only story. No Docker/DAPR E2E infrastructure required.**
>
> Visual Browser Validation (next section) replaces E2E for frontend stories.

---

## Visual Browser Validation (MANDATORY - Human Approval Required)

> **This section MUST be completed by a human reviewer before marking story as "done"**
> **Story CANNOT proceed to code review until visual validation is approved**

### 1. Start the Application

```bash
# Terminal 1: Start BFF service (for API proxy)
cd services/bff && python -m uvicorn bff.main:app --reload --port 8080

# Terminal 2: Start Factory Portal
cd web/factory-portal && npm run dev
```

**App URL:** http://localhost:3000

### 2. Visual Validation Checklist

#### Authentication Flow
- [ ] Mock login selector appears on first visit
- [ ] Can select "Jane Mwangi (Factory Manager)" persona
- [ ] After login, redirected to Command Center
- [ ] User name displayed in header
- [ ] Factory name displayed in header
- [ ] Logout button visible and functional

#### Layout & Navigation
- [ ] Sidebar visible on left side
- [ ] Sidebar shows role-appropriate menu items only
- [ ] Header spans full width at top
- [ ] Main content area displays correctly
- [ ] Clicking sidebar items navigates to correct routes
- [ ] Active route is highlighted in sidebar

#### Routes & Pages
- [ ] `/` redirects to `/command-center`
- [ ] `/command-center` shows placeholder with "Command Center" title
- [ ] `/farmers/123` shows placeholder with "Farmer Detail" title
- [ ] `/roi` shows placeholder with "ROI Summary" title
- [ ] `/settings` shows placeholder with "Settings" title
- [ ] Unknown route (e.g., `/xyz`) shows 404 page

#### Role-Based Access (Test with different personas)
- [ ] Factory Manager: sees Command Center, NOT ROI or Settings
- [ ] Factory Owner: sees Command Center AND ROI, NOT Settings
- [ ] Factory Admin: sees Settings
- [ ] Platform Admin: sees ALL menu items

#### Responsive Design
- [ ] Desktop (1920px): Full sidebar visible
- [ ] Tablet (768px): Sidebar collapses or becomes hamburger menu
- [ ] Mobile (375px): Mobile-friendly layout

#### Theme & Styling
- [ ] Colors match Farmer Power palette (Forest Green #1B4332)
- [ ] Typography uses Inter font
- [ ] Components use @fp/ui-components styling
- [ ] No unstyled/broken components

### 3. Browser Compatibility (Optional)
- [ ] Chrome: Works correctly
- [ ] Firefox: Works correctly
- [ ] Safari: Works correctly

### 4. Screenshots (Attach or Describe)

**Command Center View:**
```
(paste screenshot path or describe what you see)
```

**Sidebar Navigation:**
```
(paste screenshot path or describe what you see)
```

**Mobile View:**
```
(paste screenshot path or describe what you see)
```

### 5. Human Approval

| Field | Value |
|-------|-------|
| **Reviewer Name** | _______________ |
| **Review Date** | _______________ |
| **Validation Result** | [ ] APPROVED / [ ] REJECTED |
| **Comments/Issues** | |

**If REJECTED, list issues to fix:**
1.
2.
3.

---

**Signature:** _______________  **Date:** _______________

> After approval, proceed to mark story status as "review" and run `/code-review`

---

## Dev Notes

### CRITICAL: This is the First Frontend Application

This story creates the first React application in the platform. Pay extra attention to:

1. **Project Structure**: Follow ADR-002 exactly - this sets the pattern for all other web apps
2. **Workspace Integration**: @fp/ui-components and @fp/auth MUST work as workspace dependencies
3. **Auth Integration**: MockAuthProvider must work correctly for local development
4. **Theme Consistency**: Use the theme from @fp/ui-components, do NOT create a new theme

### Directory Structure (MUST FOLLOW EXACTLY)

```
web/factory-portal/
├── src/
│   ├── app/
│   │   ├── App.tsx                    # Root component
│   │   ├── routes.tsx                 # Route definitions
│   │   └── providers/
│   │       ├── AuthProviderWrapper.tsx
│   │       └── ThemeProvider.tsx
│   ├── pages/
│   │   ├── manager/
│   │   │   ├── CommandCenter/
│   │   │   │   ├── CommandCenter.tsx
│   │   │   │   └── index.ts
│   │   │   └── FarmerDetail/
│   │   │       ├── FarmerDetail.tsx
│   │   │       └── index.ts
│   │   ├── owner/
│   │   │   └── ROISummary/
│   │   │       ├── ROISummary.tsx
│   │   │       └── index.ts
│   │   └── admin/
│   │       └── Settings/
│   │           ├── Settings.tsx
│   │           └── index.ts
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Layout.tsx
│   │   │   └── index.ts
│   │   ├── Sidebar/
│   │   │   ├── Sidebar.tsx
│   │   │   └── index.ts
│   │   └── Header/
│   │       ├── Header.tsx
│   │       └── index.ts
│   └── main.tsx
├── public/
│   └── favicon.ico
├── .env.local.example
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── eslint.config.js
└── Dockerfile
```

[Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#Application-Structure]

### Route Definitions (React Router v6)

```typescript
// src/app/routes.tsx
import { Navigate, RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '@fp/auth';
import { Layout } from '../components/Layout';
import { CommandCenter } from '../pages/manager/CommandCenter';
import { FarmerDetail } from '../pages/manager/FarmerDetail';
import { ROISummary } from '../pages/owner/ROISummary';
import { Settings } from '../pages/admin/Settings';
import { NotFound } from '../pages/NotFound';

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/command-center" replace />,
      },
      {
        path: 'command-center',
        element: (
          <ProtectedRoute roles={['factory_manager', 'factory_owner', 'platform_admin']}>
            <CommandCenter />
          </ProtectedRoute>
        ),
      },
      {
        path: 'farmers/:id',
        element: (
          <ProtectedRoute roles={['factory_manager', 'factory_owner', 'platform_admin']}>
            <FarmerDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'roi',
        element: (
          <ProtectedRoute roles={['factory_owner', 'platform_admin']}>
            <ROISummary />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings/*',
        element: (
          <ProtectedRoute roles={['factory_admin', 'platform_admin']}>
            <Settings />
          </ProtectedRoute>
        ),
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
];
```

[Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#Role-based-routing]

### Sidebar Navigation Menu Items

```typescript
// src/components/Sidebar/menuItems.ts
export interface MenuItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  roles: string[]; // Show only if user has one of these roles
}

export const menuItems: MenuItem[] = [
  {
    label: 'Command Center',
    path: '/command-center',
    icon: <DashboardIcon />,
    roles: ['factory_manager', 'factory_owner', 'platform_admin'],
  },
  {
    label: 'ROI Summary',
    path: '/roi',
    icon: <BarChartIcon />,
    roles: ['factory_owner', 'platform_admin'],
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: <SettingsIcon />,
    roles: ['factory_admin', 'platform_admin'],
  },
];
```

### Package.json Configuration

```json
{
  "name": "@fp/factory-portal",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src"
  },
  "dependencies": {
    "@emotion/react": "^11.13.0",
    "@emotion/styled": "^11.13.0",
    "@fp/auth": "workspace:*",
    "@fp/ui-components": "workspace:*",
    "@mui/icons-material": "^6.0.0",
    "@mui/material": "^6.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.0.0"
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
    "happy-dom": "^15.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
        },
      },
    },
  },
});
```

### Environment Variables

```bash
# .env.local.example
VITE_AUTH_PROVIDER=mock
VITE_MOCK_JWT_SECRET=local-dev-secret-key-32-chars-min
VITE_API_BASE_URL=/api
```

### Dockerfile (Multi-stage)

```dockerfile
# web/factory-portal/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace files
COPY package*.json ./
COPY libs/ui-components/package.json ./libs/ui-components/
COPY libs/auth/package.json ./libs/auth/
COPY web/factory-portal/package.json ./web/factory-portal/

# Install dependencies
RUN npm ci

# Copy source files
COPY libs/ ./libs/
COPY web/factory-portal/ ./web/factory-portal/

# Build shared libraries first
WORKDIR /app/libs/ui-components
RUN npm run build

WORKDIR /app/libs/auth
RUN npm run build

# Build factory portal
WORKDIR /app/web/factory-portal
RUN npm run build

# Production image
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/web/factory-portal/dist /usr/share/nginx/html

# Configure nginx for SPA routing
COPY web/factory-portal/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Previous Story Intelligence

**From Story 0.5.6 (Shared Auth Library):**
- `@fp/auth` exports: `AuthProvider`, `MockAuthProvider`, `useAuth`, `usePermission`, `ProtectedRoute`
- Mock user personas available for local development
- JWT token generated and stored in localStorage
- Environment variable: `VITE_AUTH_PROVIDER=mock`
- Test pattern: happy-dom environment for Vitest

**From Story 0.5.5 (Shared Component Library):**
- `@fp/ui-components` exports: `StatusBadge`, `TrendIndicator`, `LeafTypeTag`, `theme`
- MUI v6 theme with Farmer Power color palette
- Storybook configured for component documentation
- Vitest configured for component testing

**From Story 0.5.4b (BFF API Routes):**
- BFF exposes REST API on port 8080
- Endpoints: `GET /api/farmers`, `GET /api/farmers/{id}`
- Authentication via JWT in Authorization header
- Response includes farmer with quality summary

### Git History Insights

Recent commits show:
- Story 0.5.6 merged: @fp/auth with 45 tests passing
- Story 0.5.5 merged: @fp/ui-components with 57 tests passing
- BFF complete with farmer API routes (0.5.4b)
- CI workflow includes frontend test job

### Anti-Patterns to Avoid

1. **DO NOT** create a new theme - use theme from `@fp/ui-components`
2. **DO NOT** implement authentication logic - use `@fp/auth` hooks and components
3. **DO NOT** hardcode user roles - use `useAuth()` hook to get current user
4. **DO NOT** skip ProtectedRoute on any page - all routes require authentication
5. **DO NOT** create custom API client - this story is scaffold only
6. **DO NOT** implement actual page content - placeholders only
7. **DO NOT** add direct MUI theme customization - extend via ui-components
8. **DO NOT** forget to add workspace dependency syntax: `"workspace:*"`

### Files to Create

| Path | Purpose |
|------|---------|
| `web/factory-portal/package.json` | Package manifest |
| `web/factory-portal/tsconfig.json` | TypeScript config |
| `web/factory-portal/vite.config.ts` | Vite configuration |
| `web/factory-portal/vitest.config.ts` | Test runner config |
| `web/factory-portal/eslint.config.js` | ESLint flat config |
| `web/factory-portal/.env.local.example` | Environment template |
| `web/factory-portal/Dockerfile` | Docker build config |
| `web/factory-portal/nginx.conf` | Nginx SPA config |
| `web/factory-portal/src/main.tsx` | App entry point |
| `web/factory-portal/src/app/App.tsx` | Root component |
| `web/factory-portal/src/app/routes.tsx` | Route definitions |
| `web/factory-portal/src/app/providers/*.tsx` | Provider wrappers |
| `web/factory-portal/src/components/Layout/*.tsx` | App shell layout |
| `web/factory-portal/src/components/Sidebar/*.tsx` | Navigation sidebar |
| `web/factory-portal/src/components/Header/*.tsx` | App header |
| `web/factory-portal/src/pages/manager/CommandCenter/*.tsx` | Placeholder |
| `web/factory-portal/src/pages/manager/FarmerDetail/*.tsx` | Placeholder |
| `web/factory-portal/src/pages/owner/ROISummary/*.tsx` | Placeholder |
| `web/factory-portal/src/pages/admin/Settings/*.tsx` | Placeholder |
| `web/factory-portal/src/pages/NotFound.tsx` | 404 page |
| `tests/unit/web/factory-portal/test_app.test.tsx` | App tests |
| `tests/unit/web/factory-portal/test_routing.test.tsx` | Routing tests |
| `tests/unit/web/factory-portal/test_layout.test.tsx` | Layout tests |

### Files to Modify

| Path | Change |
|------|--------|
| `package.json` (root) | Add `web/factory-portal` to workspaces |
| `.github/workflows/ci.yaml` | Add factory-portal to frontend tests job |

### References

- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md]
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#Application-Structure]
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#Role-based-routing]
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#Technology-Choices]
- [Source: _bmad-output/epics/epic-0-5-frontend.md#Story-0.5.7]
- [Source: _bmad-output/ux-design-specification/index.md]
- [Source: _bmad-output/project-context.md]

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
