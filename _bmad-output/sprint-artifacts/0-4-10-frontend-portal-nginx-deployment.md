# Story 0.4.10: Frontend Portal NGINX Deployment for Human Validation

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

---

## Story

As a **platform developer**,
I want the admin portal and factory portal deployed via NGINX in docker-compose,
So that I can perform human validation of UI features with proper API routing and JWT auth.

**Background:**
Story 9.2 validation revealed pain points:
- Manual NPM dev server connection to API ports
- Token authorization header issues through dev proxy
- Difficulty validating real data display (e.g., last 7 days weather observations)

**This story blocks:** Epic 9 feature stories (9.3+) which require human UI validation

---

## Acceptance Criteria

1. **AC1: Admin Portal via NGINX** - Given docker-compose E2E stack is running, When I navigate to `http://localhost:8085/admin`, Then the platform-admin portal is served via NGINX

2. **AC2: Factory Portal via NGINX** - Given docker-compose E2E stack is running, When I navigate to `http://localhost:8085/factory`, Then the factory-portal is served via NGINX

3. **AC3: API Proxy Routing** - Given NGINX is configured as reverse proxy, When the frontend makes API calls to `/api/*`, Then requests are proxied to `bff-service:8080` with headers preserved (including Authorization)

4. **AC4: JWT Auth Flow** - Given a valid JWT token is obtained (via mock auth), When API requests include `Authorization: Bearer <token>` header, Then the BFF validates the token and returns data correctly

5. **AC5: Human Validation Ready** - Given I want to validate a UI feature, When I run `bash scripts/e2e-up.sh --build`, Then I can access both portals at `http://localhost:8085/{admin|factory}` for human validation

---

## Tasks / Subtasks

- [ ] **Task 1: Vite Base Path Configuration** (AC: 1, 2, 3)
  - [ ] Update `web/platform-admin/vite.config.ts` - add `base: process.env.VITE_BASE_URL || '/'`
  - [ ] Update `web/factory-portal/vite.config.ts` - add `base: process.env.VITE_BASE_URL || '/'`
  - [ ] Verify builds work locally with `VITE_BASE_URL=/admin/ npm run build`

- [ ] **Task 2: Platform Admin Dockerfile** (AC: 1, 3, 4)
  - [ ] Create `web/platform-admin/Dockerfile` (multi-stage: node build -> nginx serve)
  - [ ] Add build args: `VITE_BASE_URL`, `VITE_MOCK_JWT_SECRET`, `VITE_AUTH_PROVIDER`
  - [ ] Pass `VITE_MOCK_JWT_SECRET=test-secret-for-e2e` to match BFF E2E config
  - [ ] Match factory-portal Dockerfile pattern exactly

- [ ] **Task 3: Update Factory Portal Dockerfile** (AC: 2, 3, 4)
  - [ ] Update `web/factory-portal/Dockerfile` to add build args for base URL and JWT secret
  - [ ] Ensure `VITE_MOCK_JWT_SECRET=test-secret-for-e2e` matches BFF

- [ ] **Task 4: Unified NGINX Service for E2E** (AC: 1, 2, 3, 4)
  - [ ] Create `deploy/docker/nginx/Dockerfile` (copies built assets from portal images)
  - [ ] Create `deploy/docker/nginx/nginx.conf` (unified config)
  - [ ] Configure `/admin` location with `alias` to serve platform-admin
  - [ ] Configure `/factory` location with `alias` to serve factory-portal
  - [ ] Configure `/api/*` proxy to `bff:8080` with `Authorization` header passthrough
  - [ ] Configure `/health` endpoint for Docker healthcheck

- [ ] **Task 5: Docker Compose Updates** (AC: 1, 2, 5)
  - [ ] Add `nginx` service to `docker-compose.e2e.yaml` (port 8085)
  - [ ] Add `platform-admin` build service with correct build args
  - [ ] Update `factory-portal` build service with correct build args
  - [ ] Configure service dependencies (nginx depends on both portals and bff)

- [ ] **Task 6: E2E Script Updates** (AC: 5)
  - [ ] Update `scripts/e2e-preflight.sh` to validate NGINX health at port 8085

- [ ] **Task 7: Verification & Documentation** (AC: All)
  - [ ] Run `bash scripts/e2e-up.sh --build`
  - [ ] Verify http://localhost:8085/admin loads platform-admin
  - [ ] Verify http://localhost:8085/factory loads factory-portal
  - [ ] Login using MockLoginSelector UI (click Login, select persona)
  - [ ] Verify API calls work with mock JWT token
  - [ ] Update story file with test evidence

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.4.10: Frontend Portal NGINX Deployment"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-4-10-frontend-portal-nginx-deployment
  ```

**Branch name:** `story/0-4-10-frontend-portal-nginx-deployment`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-4-10-frontend-portal-nginx-deployment`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.4.10: Frontend Portal NGINX Deployment" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-4-10-frontend-portal-nginx-deployment`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
N/A - This is an infrastructure story, no unit tests added
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with frontend builds
bash scripts/e2e-up.sh --build

# Verify NGINX health
curl http://localhost:8085/health

# Verify admin portal
curl -s http://localhost:8085/admin | head -20

# Verify factory portal
curl -s http://localhost:8085/factory | head -20

# Verify API proxy works
curl -H "Authorization: Bearer test-token" http://localhost:8085/api/health

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste output here after implementation)
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
git push origin story/0-4-10-frontend-portal-nginx-deployment

# Wait ~30s, then check CI status
gh run list --branch story/0-4-10-frontend-portal-nginx-deployment --limit 3

# Trigger E2E tests (MANDATORY - does NOT auto-run)
gh workflow run e2e.yaml --ref story/0-4-10-frontend-portal-nginx-deployment
sleep 10
gh run list --workflow=e2e.yaml --branch story/0-4-10-frontend-portal-nginx-deployment --limit 1
```
**CI Run ID:** _______________
**E2E Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: JWT Secret Must Match

The frontend and BFF MUST use the same JWT secret for token validation:

| Component | Env Variable | Value for E2E |
|-----------|--------------|---------------|
| BFF (docker-compose) | `MOCK_JWT_SECRET` | `test-secret-for-e2e` |
| Frontend (build arg) | `VITE_MOCK_JWT_SECRET` | `test-secret-for-e2e` |

**If these don't match, all API calls will return 401 Unauthorized.**

### CRITICAL: Build Order (libs MUST build first)

```bash
# Correct order - libs/auth exports JWT signing functions used by portals
1. libs/ui-components  # Shared MUI components
2. libs/auth           # JWT generation (generateMockToken)
3. web/platform-admin  # Depends on both libs
4. web/factory-portal  # Depends on both libs
```

### Mock Auth Flow for Human Validation

The `@fp/auth` library provides a complete mock auth system:

1. **User clicks "Login"** → `MockLoginSelector` modal appears
2. **User selects a persona** → JWT token generated with `generateMockToken()`
3. **Token stored** → `localStorage.setItem('fp_auth_token', token)`
4. **API calls include** → `Authorization: Bearer <token>` header
5. **BFF validates** → HS256 signature check with shared secret

### Available Mock Users for Testing

| Persona | Role | Email | Factory Access |
|---------|------|-------|----------------|
| **Jane Mwangi** | factory_manager | jane.mwangi@factory.example.com | KEN-FAC-001 |
| **John Ochieng** | factory_owner | john.ochieng@factory.example.com | KEN-FAC-001, KEN-FAC-002 |
| **Admin User** | platform_admin | admin@farmerpower.example.com | All (wildcard) |
| **Mary Wanjiku** | registration_clerk | mary.wanjiku@factory.example.com | KEN-FAC-001, CP: KEN-CP-001 |
| **TBK Inspector** | regulator | inspector@tbk.go.ke | None (regional stats only) |

**For Admin Portal testing:** Use "Admin User" (platform_admin role)
**For Factory Portal testing:** Use "Jane Mwangi" or "John Ochieng"

### Existing Assets to Reuse

**Factory Portal (use as template):**
- `web/factory-portal/Dockerfile` - Multi-stage build (node -> nginx)
- `web/factory-portal/dist/` - Pre-built Vite output

**Platform Admin (NEEDS DOCKERFILE):**
- `web/platform-admin/dist/` - Pre-built Vite output exists
- `web/platform-admin/src/` - React + Vite source
- NO Dockerfile exists - must be created matching factory-portal pattern

**Shared Libraries (required for builds):**
- `libs/ui-components/` - @fp/ui-components (MUI v6 shared components)
- `libs/auth/` - @fp/auth (mock auth + JWT generation)
- Root `package.json` - npm workspaces configuration

### Port Allocation (808x HTTP pattern)

| Port | Service | Purpose |
|------|---------|---------|
| 8001 | Plantation Model | Health endpoint |
| 8002 | Collection Model | Health endpoint |
| 8083 | BFF | REST API |
| 8084 | Platform Cost | Health + gRPC |
| **8085** | **NGINX** | **Frontend portals (NEW)** |
| 8090 | AI Model | gRPC |
| 8091 | AI Model | Health endpoint |

### NGINX Configuration Strategy

**Unified E2E NGINX (`deploy/docker/nginx/nginx.conf`):**
```nginx
# Single NGINX serving both portals at different paths
server {
    listen 80;

    # Admin portal at /admin
    location /admin {
        alias /usr/share/nginx/html/admin;
        try_files $uri $uri/ /admin/index.html;
    }

    # Factory portal at /factory
    location /factory {
        alias /usr/share/nginx/html/factory;
        try_files $uri $uri/ /factory/index.html;
    }

    # API proxy to BFF
    location /api {
        proxy_pass http://bff:8080;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header Host $host;
        # ... other headers
    }

    # Health check
    location /health {
        return 200 'OK';
    }
}
```

### Docker Compose Service Pattern

```yaml
# ==========================================================================
# Frontend Portals + NGINX Reverse Proxy (Story 0.4.10)
# ==========================================================================

# Platform Admin build - outputs static files
platform-admin:
  build:
    context: ../../..
    dockerfile: web/platform-admin/Dockerfile
    args:
      VITE_BASE_URL: /admin/
      VITE_MOCK_JWT_SECRET: test-secret-for-e2e
      VITE_AUTH_PROVIDER: mock
  container_name: e2e-platform-admin
  # Build-only service - no ports, exits after build
  volumes:
    - platform-admin-dist:/app/web/platform-admin/dist

# Factory Portal build - outputs static files
factory-portal:
  build:
    context: ../../..
    dockerfile: web/factory-portal/Dockerfile
    args:
      VITE_BASE_URL: /factory/
      VITE_MOCK_JWT_SECRET: test-secret-for-e2e
      VITE_AUTH_PROVIDER: mock
  container_name: e2e-factory-portal
  # Build-only service - no ports, exits after build
  volumes:
    - factory-portal-dist:/app/web/factory-portal/dist

# NGINX - serves both portals and proxies API
nginx:
  build:
    context: ../../..
    dockerfile: deploy/docker/nginx/Dockerfile
  container_name: e2e-nginx
  ports:
    - "8085:80"
  volumes:
    - platform-admin-dist:/usr/share/nginx/html/admin:ro
    - factory-portal-dist:/usr/share/nginx/html/factory:ro
  depends_on:
    platform-admin:
      condition: service_completed_successfully
    factory-portal:
      condition: service_completed_successfully
    bff:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - e2e-network

volumes:
  platform-admin-dist:
  factory-portal-dist:
```

### Vite Config Change (REQUIRED)

Update both `web/platform-admin/vite.config.ts` and `web/factory-portal/vite.config.ts`:

```typescript
export default defineConfig({
  // ADD THIS LINE - enables path prefix for NGINX serving
  base: process.env.VITE_BASE_URL || '/',
  plugins: [react()],
  // ... rest of config unchanged
});
```

### Dockerfile Pattern with Build Args

```dockerfile
# web/platform-admin/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Build args for Vite (available at BUILD time only)
ARG VITE_BASE_URL=/admin/
ARG VITE_MOCK_JWT_SECRET=test-secret-for-e2e
ARG VITE_AUTH_PROVIDER=mock

# Copy workspace structure
COPY package*.json ./
COPY libs/ui-components/package.json ./libs/ui-components/
COPY libs/auth/package.json ./libs/auth/
COPY web/platform-admin/package.json ./web/platform-admin/

RUN npm ci

# Build libs first (correct order!)
COPY libs/ui-components/ ./libs/ui-components/
WORKDIR /app/libs/ui-components
RUN npm run build

COPY libs/auth/ ./libs/auth/
WORKDIR /app/libs/auth
RUN npm run build

# Build portal with env vars
WORKDIR /app
COPY web/platform-admin/ ./web/platform-admin/
WORKDIR /app/web/platform-admin
RUN npm run build

# Production stage - just the built assets
FROM nginx:alpine
COPY --from=builder /app/web/platform-admin/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Unified NGINX Config (`deploy/docker/nginx/nginx.conf`)

```nginx
server {
    listen 80;
    server_name localhost;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Admin Portal at /admin
    location /admin {
        alias /usr/share/nginx/html/admin;
        try_files $uri $uri/ /admin/index.html;
    }

    # Factory Portal at /factory
    location /factory {
        alias /usr/share/nginx/html/factory;
        try_files $uri $uri/ /factory/index.html;
    }

    # API proxy to BFF - MUST preserve Authorization header
    location /api {
        proxy_pass http://bff:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # CRITICAL: Pass through Authorization header for JWT
        proxy_set_header Authorization $http_authorization;
        proxy_cache_bypass $http_upgrade;
    }

    # Health check for Docker
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # Root redirect to admin
    location = / {
        return 302 /admin;
    }
}
```

### References

- [Source: `web/factory-portal/Dockerfile` - Template for platform-admin Dockerfile]
- [Source: `web/factory-portal/nginx.conf` - Template for NGINX SPA config]
- [Source: `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Add NGINX service here]
- [Source: `scripts/e2e-up.sh` - E2E launcher to update]
- [Source: `scripts/e2e-preflight.sh` - Add NGINX health check]
- [Source: `_bmad-output/project-context.md` - Project rules and patterns]

### Project Structure Notes

**File locations follow project conventions:**
- Frontend apps: `web/{app-name}/`
- Dockerfiles: In each app folder OR `deploy/docker/` for shared
- NGINX configs: In app folder for app-specific, `deploy/docker/nginx/` for shared

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `web/platform-admin/Dockerfile` - Multi-stage build with JWT secret build arg
- `deploy/docker/nginx/Dockerfile` - Simple nginx image for serving static files
- `deploy/docker/nginx/nginx.conf` - Unified config for /admin, /factory, /api proxy

**Modified:**
- `web/platform-admin/vite.config.ts` - Add `base: process.env.VITE_BASE_URL || '/'`
- `web/factory-portal/vite.config.ts` - Add `base: process.env.VITE_BASE_URL || '/'`
- `web/factory-portal/Dockerfile` - Add VITE_BASE_URL, VITE_MOCK_JWT_SECRET build args
- `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Add nginx, platform-admin, factory-portal services
- `scripts/e2e-preflight.sh` - Add NGINX health check at port 8085
