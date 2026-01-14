# Story 9.1a: Platform Admin Application Scaffold

As a **platform developer**,
I want the Platform Admin React application scaffolded with routing, layout, and hierarchical navigation,
So that all admin screens can be built on a consistent foundation.

## Acceptance Criteria

**AC 9.1.1: Project Initialization**

**Given** the web folder structure exists
**When** I create `web/platform-admin/`
**Then** Vite + React + TypeScript project is initialized
**And** `@fp/ui-components` and `@fp/auth` are configured as dependencies
**And** ESLint and Prettier are configured
**And** Material UI v6 is installed with Earth & Growth theme

**AC 9.1.2: Theme Configuration**

**Given** the project is scaffolded
**When** I configure the MUI theme
**Then** the following colors are applied:
  - Primary: Forest Green (`#1B4332`)
  - Secondary: Earth Brown (`#5C4033`)
  - Warning: Harvest Gold (`#D4A03A`)
  - Error: Warm Red (`#C1292E`)
  - Background: Warm White (`#FFFDF9`)

**AC 9.1.3: Routing Configuration**

**Given** the project is scaffolded
**When** I configure routing
**Then** React Router v6 is configured with:

| Route | Screen | Description |
|-------|--------|-------------|
| `/` | Dashboard | Platform overview |
| `/regions` | Region List | All regions (top-level) |
| `/regions/:regionId` | Region Detail | Region configuration |
| `/farmers` | Farmer List | All farmers with filters (top-level) |
| `/farmers/:farmerId` | Farmer Detail | Full farmer edit |
| `/factories` | Factory List | All factories (top-level) |
| `/factories/:factoryId` | Factory Detail | Factory + CPs (hierarchical) |
| `/factories/:factoryId/collection-points/:cpId` | CP Detail | Collection point config |
| `/grading-models` | Grading Model List | All models |
| `/grading-models/:modelId` | Grading Model Detail | Model configuration |
| `/users` | User List | All platform users |
| `/health` | Platform Health | System metrics |
| `/knowledge` | Knowledge Library | RAG documents |
| `/costs` | Cost Dashboard | LLM spending |

**And** all routes require `platform_admin` role

**AC 9.1.4: Navigation Layout**

**Given** the app is built
**When** I view any screen
**Then** a persistent sidebar shows:
  - 🌍 Regions (top-level, independent)
  - 👨‍🌾 Farmers (top-level, independent with filters)
  - 🏭 Factories (hierarchical to CPs)
  - ────────────
  - 📊 Grading Models
  - 👤 Users
  - ────────────
  - 📈 Health
  - 📚 Knowledge
  - 💰 Costs
**And** breadcrumb navigation shows current position
**And** the Farmer Power logo appears in the header

## Wireframe: Application Shell

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌿 FARMER POWER ADMIN                                    [Search] [👤 Admin ▼] │
├────────────────┬────────────────────────────────────────────────────────────────┤
│                │                                                                 │
│  NAVIGATION    │  🏭 Factories › Nyeri Tea Factory › Collection Points          │
│  ────────────  │  ─────────────────────────────────────────────────────────────  │
│                │                                                                 │
│  🌍 Regions    │  [Page content loads here based on route]                      │
│  👨‍🌾 Farmers   │                                                                 │
│  🏭 Factories  │                                                                 │
│  ────────────  │                                                                 │
│  📊 Grading    │                                                                 │
│  👤 Users      │                                                                 │
│  ────────────  │                                                                 │
│  📈 Health     │                                                                 │
│  📚 Knowledge  │                                                                 │
│  💰 Costs      │                                                                 │
│                │                                                                 │
└────────────────┴────────────────────────────────────────────────────────────────┘
```

## Technical Notes
- Location: `web/platform-admin/`
- Deployment: `admin.farmerpower.co.ke` (internal access only)
- Reference: ADR-002 for folder structure
- Breadcrumb state derived from URL params + API data
- **Map Dependencies**: Install per [ADR-017: Map Services](architecture/adr/ADR-017-map-services-gps-region-assignment.md)

  ```bash
  npm install leaflet react-leaflet leaflet-draw @turf/turf
  npm install -D @types/leaflet @types/leaflet-draw
  ```

## Dependencies
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library
- ADR-017: Map Services and GPS-Based Region Assignment

## Story Points: 5

---
