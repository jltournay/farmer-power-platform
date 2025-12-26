# ADR-002: Frontend Architecture

**Status:** Accepted
**Date:** 2025-12-26
**Deciders:** Winston (Architect), Jeanlouistournay
**Related Stories:** Epic 3 (Factory Manager Dashboard), Story 3.1-3.7

## Context

The Farmer Power Platform requires multiple web-based user interfaces serving distinct user roles:

| UI | User | Screens | Purpose |
|----|------|---------|---------|
| Factory Manager Dashboard | Quality Manager (Joseph) | 4 | Daily operations, farmer intervention |
| Factory Owner Dashboard | Factory Owner | 3 | ROI validation, subscription value |
| Factory Admin | Factory Administrator | 4 | Payment policies, SMS templates |
| Platform Admin | Farmer Power team | 4 | Factory onboarding, user management |
| Regulator Dashboard | Tea Board of Kenya | 4 | National quality intelligence |
| Farmer Registration | Registration Clerk | 4 | Farmer enrollment at collection points |

**Total: 6 distinct UIs, 23 web screens**

### Key Considerations

1. **Security isolation**: Regulator (government) requires complete separation
2. **Deployment model**: Registration runs on dedicated devices at collection points
3. **Code sharing**: All UIs share design system (Material UI v6, custom components)
4. **Team structure**: Single team initially, potential for parallel development later
5. **Network conditions**: Registration kiosks operate in rural Kenya with unreliable connectivity

## Decision

**Hybrid architecture with 4 frontend applications** grouped by security boundary and deployment context.

```
web/
├── factory-portal/          # Factory Manager + Owner + Admin
├── platform-admin/          # Internal Farmer Power team
├── regulator/               # Tea Board of Kenya (isolated)
└── registration-kiosk/      # Collection point devices (PWA)

libs/
└── ui-components/           # Shared component library
```

## Alternatives Considered

### Option A: Single React App with Role-Based Permissions

```
web/
└── dashboard/    # One app, all roles
```

| Pros | Cons |
|------|------|
| Single deployment | All code ships to all users |
| Easy code sharing | Admin code exists in browser (hidden) |
| Simple dev experience | Regulator cannot be isolated |
| | One bad deploy affects everyone |

**Rejected:** Security isolation requirements for Regulator (TBK) make this unacceptable.

### Option B: Separate App Per Role (6 Apps)

```
web/
├── factory-manager/
├── factory-owner/
├── factory-admin/
├── platform-admin/
├── regulator/
└── registration/
```

| Pros | Cons |
|------|------|
| Maximum isolation | 6 build pipelines |
| Independent deployments | Significant duplication |
| | Over-engineered for factory users |

**Rejected:** Factory Manager, Owner, and Admin share the same organizational context and authentication. Separating them adds complexity without benefit.

### Option C: Hybrid by Security Boundary (Selected)

Groups applications by:
- **Security boundary**: Regulator must be isolated
- **Deployment context**: Registration kiosk has unique requirements
- **User context**: Factory users share organizational data

## Application Structure

### 1. Factory Portal (`web/factory-portal/`)

**Users:** Factory Manager, Factory Owner, Factory Admin
**Screens:** 11 total (4 + 3 + 4)
**Type:** Standard React SPA

```
web/factory-portal/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── providers/
│   │       ├── AuthProvider.tsx
│   │       └── ThemeProvider.tsx
│   │
│   ├── pages/
│   │   ├── manager/              # Joseph's screens
│   │   │   ├── CommandCenter/
│   │   │   ├── FarmerDetail/
│   │   │   ├── TemporalPatterns/
│   │   │   └── SMSPreview/
│   │   ├── owner/                # Factory Owner screens
│   │   │   ├── ROISummary/
│   │   │   ├── ROIDrillDown/
│   │   │   └── RegionalBenchmark/
│   │   └── admin/                # Factory Admin screens
│   │       ├── PaymentPolicy/
│   │       ├── GradeMultipliers/
│   │       ├── SMSTemplates/
│   │       └── ImpactCalculator/
│   │
│   ├── components/
│   │   └── [re-exports from @fp/ui-components]
│   │
│   ├── hooks/
│   │   ├── useFarmers.ts
│   │   ├── useQualityMetrics.ts
│   │   └── useReports.ts
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── farmers.ts
│   │   └── reports.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts
│   │   └── filtersStore.ts
│   │
│   └── types/
│
├── package.json
├── vite.config.ts
├── tsconfig.json
└── Dockerfile
```

**Role-based routing:**
```typescript
// routes.tsx
const routes = [
  // Manager routes (role: factory_manager, factory_owner, factory_admin)
  { path: '/command-center', element: <CommandCenter />, roles: ['factory_manager'] },
  { path: '/farmers/:id', element: <FarmerDetail />, roles: ['factory_manager', 'factory_owner'] },

  // Owner routes (role: factory_owner)
  { path: '/roi', element: <ROISummary />, roles: ['factory_owner'] },

  // Admin routes (role: factory_admin)
  { path: '/settings/payment', element: <PaymentPolicy />, roles: ['factory_admin'] },
];
```

### 2. Platform Admin (`web/platform-admin/`)

**Users:** Farmer Power internal team
**Screens:** 4
**Type:** Standard React SPA
**Access:** Internal network only / VPN required

```
web/platform-admin/
├── src/
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── FactoryOnboarding/
│   │   ├── UserManagement/
│   │   └── FactoryList/
│   └── ...
└── ...
```

### 3. Regulator Dashboard (`web/regulator/`)

**Users:** Tea Board of Kenya officials
**Screens:** 4
**Type:** Standard React SPA
**Access:** Completely isolated, separate authentication

```
web/regulator/
├── src/
│   ├── pages/
│   │   ├── NationalOverview/
│   │   ├── RegionalComparison/
│   │   ├── LeafTypeDistribution/
│   │   └── ExportReadiness/
│   └── ...
└── ...
```

**Isolation requirements:**
- Separate subdomain: `regulator.farmerpower.co.ke`
- Separate authentication (government SSO if required)
- No shared runtime state with other apps
- Read-only aggregated data (no individual farmer PII)

### 4. Registration Kiosk (`web/registration-kiosk/`)

**Users:** Registration Clerks at collection points
**Screens:** 4
**Type:** Progressive Web App (PWA)
**Deployment:** Dedicated tablets at collection points

```
web/registration-kiosk/
├── src/
│   ├── pages/
│   │   ├── PhoneVerification/
│   │   ├── FarmerDetails/
│   │   ├── CollectionPointAssignment/
│   │   └── IDCardPrint/
│   │
│   ├── services/
│   │   ├── offlineQueue.ts      # IndexedDB queue
│   │   ├── syncService.ts       # Background sync
│   │   └── printService.ts      # ID card printing
│   │
│   └── sw.ts                    # Service worker
│
├── vite.config.ts               # PWA plugin config
└── ...
```

**PWA requirements:**

| Requirement | Implementation |
|-------------|----------------|
| Offline-first | Service worker caches app shell |
| Offline data entry | IndexedDB stores registration queue |
| Background sync | Submits when connection restored |
| Installable | Web app manifest, install prompt |
| Printer support | Web Print API for ID cards |
| Long sessions | Refresh tokens, auto-renewal |

## Shared Component Library

```
libs/
└── ui-components/
    ├── src/
    │   ├── components/
    │   │   ├── StatusBadge/
    │   │   │   ├── StatusBadge.tsx
    │   │   │   ├── StatusBadge.test.tsx
    │   │   │   └── index.ts
    │   │   ├── TrendIndicator/
    │   │   ├── FarmerCard/
    │   │   ├── LeafTypeTag/
    │   │   ├── SMSPreview/
    │   │   ├── ROIMetricCard/
    │   │   └── ActionStrip/
    │   │
    │   ├── theme/
    │   │   ├── index.ts
    │   │   ├── palette.ts        # TBK color system
    │   │   ├── typography.ts
    │   │   └── components.ts     # MUI overrides
    │   │
    │   └── index.ts              # Public exports
    │
    ├── package.json              # @fp/ui-components
    └── tsconfig.json
```

**Usage in apps:**
```typescript
import { FarmerCard, StatusBadge, theme } from '@fp/ui-components';
```

## Technology Choices

| Category | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | React 18 | Team familiarity, ecosystem, MUI compatibility |
| **Build tool** | Vite | Fast builds, native ESM, simple config |
| **Language** | TypeScript | Type safety, better DX, catches errors early |
| **Styling** | Material UI v6 + Emotion | Per UX spec, accessible, theme system |
| **State (local)** | Zustand | Simple, no boilerplate, TypeScript-first |
| **State (server)** | TanStack Query | Caching, background refresh, loading states |
| **Routing** | React Router v6 | Standard, well-documented |
| **Forms** | React Hook Form + Zod | Performant, validation, type inference |
| **Testing** | Vitest + Testing Library | Fast, Vite-compatible, user-centric |
| **PWA** | Vite PWA Plugin + Workbox | Service worker generation, caching strategies |

## Consequences

### Positive

- **Security**: Regulator dashboard completely isolated from factory data
- **Deployment flexibility**: Apps deploy independently
- **Optimized bundles**: Users only download code for their app
- **Offline capability**: Registration kiosk works in rural areas
- **Shared design system**: Consistent UX across all apps
- **Parallel development**: Teams can work on different apps simultaneously

### Negative

- **4 build pipelines**: More CI/CD configuration
- **Component library maintenance**: Need to publish/version shared components
- **SSO complexity**: Multiple apps need coordinated authentication
- **Initial setup overhead**: More boilerplate than single app

### Mitigations

| Risk | Mitigation |
|------|------------|
| Build complexity | Turborepo or Nx for monorepo orchestration |
| Component versioning | Keep in monorepo, no publishing needed |
| SSO | Shared auth library, same identity provider |
| Duplication | Strict component library discipline |

## Repository Structure Update

Add to `repository-structure.md`:

```
farmer-power-platform/
├── services/                    # Backend (existing)
│
├── web/                         # Frontend applications
│   ├── factory-portal/          # Manager + Owner + Admin
│   ├── platform-admin/          # Internal admin
│   ├── regulator/               # TBK dashboard
│   └── registration-kiosk/      # Collection point PWA
│
├── libs/                        # Shared libraries
│   ├── fp-common/               # Python (existing)
│   ├── fp-proto/                # Python (existing)
│   ├── fp-testing/              # Python (existing)
│   └── ui-components/           # React component library (NEW)
│
└── ...
```

## Build & Deployment

### Monorepo Tooling

```json
// package.json (root)
{
  "workspaces": [
    "web/*",
    "libs/*"
  ],
  "scripts": {
    "dev:factory": "npm -w web/factory-portal run dev",
    "dev:admin": "npm -w web/platform-admin run dev",
    "dev:regulator": "npm -w web/regulator run dev",
    "dev:kiosk": "npm -w web/registration-kiosk run dev",
    "build:all": "npm -ws run build",
    "test:all": "npm -ws run test"
  }
}
```

### Deployment Targets

| App | URL | Hosting |
|-----|-----|---------|
| factory-portal | `app.farmerpower.co.ke` | Azure Static Web Apps |
| platform-admin | `admin.farmerpower.co.ke` | Azure Static Web Apps (internal) |
| regulator | `regulator.farmerpower.co.ke` | Azure Static Web Apps (isolated) |
| registration-kiosk | `register.farmerpower.co.ke` | Azure Static Web Apps + PWA |

## References

- [UI & Screens Inventory](../_bmad-output/ux-design-specification/ui-screens-inventory.md)
- [UX Design Specification](../_bmad-output/ux-design-specification/index.md)
- [Design System Foundation](../_bmad-output/ux-design-specification/design-system-foundation.md)
- [Component Strategy](../_bmad-output/ux-design-specification/6-component-strategy.md)
- Epic 3: Factory Manager Dashboard
