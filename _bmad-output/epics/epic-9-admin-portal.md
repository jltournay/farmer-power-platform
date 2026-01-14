# Epic 9: Platform Admin Portal

**Priority:** P1 (Critical for Pilot Operations)

**Dependencies:** Epic 0.5 (Frontend Infrastructure), Epic 1 (Plantation Model)

**Strategic Purpose:** The Platform Admin Portal is the **primary operational interface** for pilot deployment. It enables the Farmer Power team to manage ALL plantation data (regions, factories, collection points, farmers) without depending on Factory Admin (Epic 10) or Clerk interfaces. This is the control center for pilot operations.

**Related ADRs:** ADR-002 (Frontend Architecture), ADR-003 (Identity & Access Management)

**Design Direction:** Command Center (per UX Design Specification)

**Component Library:** Material UI v6

---

## Scope Overview

### Data Model Relationships (Important!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REGIONS are geographic areas based on GPS + altitude                       │
│  - Farmers are AUTO-ASSIGNED to regions based on their farm GPS location    │
│  - A farmer's region may DIFFER from the factory they deliver to            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  FACTORIES own COLLECTION POINTS (true hierarchy)                           │
│  🏭 Factory                                                                  │
│    └── 📍 Collection Point (belongs to exactly one factory)                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  FARMERS are independent entities                                           │
│  - Have a PRIMARY collection point (for registration)                       │
│  - Can DELIVER to ANY collection point (tracked in deliveries)              │
│  - Region based on FARM GPS, not factory location                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Navigation Model: Option C (Hybrid)

| Screen | Type | Access | Notes |
|--------|------|--------|-------|
| 🌍 **Regions** | Top-level | Sidebar | Independent geographic management |
| 👨‍🌾 **Farmers** | Top-level | Sidebar | Independent, filter by region/factory/CP |
| 🏭 **Factories** | Hierarchical | Sidebar | Drill-down to Collection Points |
| 📍 **Collection Points** | Child | Via Factory | Accessed through factory detail |
| 📊 Grading Models | Standalone | Sidebar | Assigned to factories |
| 👤 Users | Standalone | Sidebar | Azure AD B2C |
| 📈 Health | Standalone | Sidebar | Platform metrics |
| 📚 Knowledge | Standalone | Sidebar | RAG documents |
| 💰 Costs | Standalone | Sidebar | LLM spending |

---

## Story 9.1: Platform Admin Application Scaffold

As a **platform developer**,
I want the Platform Admin React application scaffolded with routing, layout, and hierarchical navigation,
So that all admin screens can be built on a consistent foundation.

### Acceptance Criteria

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

### Wireframe: Application Shell

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

### Technical Notes
- Location: `web/platform-admin/`
- Deployment: `admin.farmerpower.co.ke` (internal access only)
- Reference: ADR-002 for folder structure
- Breadcrumb state derived from URL params + API data

### Dependencies
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library

### Story Points: 5

---

## Story 9.2: Region Management

As a **Platform Administrator**,
I want to view, create, edit, and manage regions,
So that I can configure the geographic foundation for all plantation data.

### Acceptance Criteria

**AC 9.2.1: Region List View**

**Given** I navigate to `/regions`
**When** the page loads
**Then** I see a card grid of all regions with:
  - Region name and county
  - Altitude band badge (Highland/Midland/Lowland)
  - Factory count
  - Farmer count (aggregated)
  - Status indicator (Active/Inactive)
**And** I can filter by county and altitude band
**And** I can search by region name

**AC 9.2.2: Region Detail View (Top-Level)**

**Given** I click on a region card
**When** the region detail page loads
**Then** I see the region information panel (editable)
**And** I see a read-only summary of factories in this region (count, names)
**And** I see a read-only summary of farmers in this region (count)
**And** factory links navigate to the Factories screen (filtered by region)

**AC 9.2.3: Region Creation**

**Given** I click "+ Add Region"
**When** I complete the form
**Then** I provide:
  - Name, County, Country (default: Kenya)
  - Center GPS coordinates + radius
  - Altitude band (Highland/Midland/Lowland)
  - Flush calendar (first flush, monsoon, autumn, dormant periods)
  - Agronomic factors (soil type, diseases, harvest hours, frost risk)
  - Weather API configuration
**And** the region is created with status Active
**And** I'm redirected to the new region detail page

**AC 9.2.4: Region Editing**

**Given** I'm on a region detail page
**When** I click "Edit"
**Then** the region fields become editable inline
**And** I can modify any field
**And** changes are saved when I click "Save"
**And** I can cancel to discard changes

### Wireframe: Region List

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌍 REGIONS                                                      [+ Add Region] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                           SEARCH                                        │
│  County: [All ▼]  Altitude: [All ▼]   [🔍 Search regions...              ]      │
│                                                                                  │
│  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌─────────────────┐│
│  │  🌍 NYERI HIGHLAND       │  │  🌍 NYERI MIDLAND        │  │  🌍 KERICHO     ││
│  │  ─────────────────────   │  │  ─────────────────────   │  │  HIGHLAND       ││
│  │  County: Nyeri           │  │  County: Nyeri           │  │  ─────────────  ││
│  │  🏔️ Highland (1800m+)    │  │  🏔️ Midland (1400-1800m) │  │  County: Kericho││
│  │                          │  │                          │  │  🏔️ Highland    ││
│  │  🏭 3 Factories          │  │  🏭 2 Factories          │  │                 ││
│  │  👨‍🌾 342 Farmers          │  │  👨‍🌾 187 Farmers          │  │  🏭 4 Factories ││
│  │                          │  │                          │  │  👨‍🌾 521 Farmers ││
│  │  ● Active                │  │  ● Active                │  │                 ││
│  │                          │  │                          │  │  ● Active       ││
│  │  [View Details →]        │  │  [View Details →]        │  │  [View Details→]││
│  └──────────────────────────┘  └──────────────────────────┘  └─────────────────┘│
│                                                                                  │
│  Showing 8 regions                                     [← Previous] [Next →]    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Region Detail (Top-Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌍 Regions › NYERI HIGHLAND                              [Edit] [← Back]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  REGION INFORMATION                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name: Nyeri Highland              County: Nyeri         Country: Kenya   │  │
│  │  Altitude: Highland (1800m+)       Center: -0.4197, 36.9553   Radius: 25km│  │
│  │  Status: ● Active                                                         │  │
│  │                                                                           │  │
│  │  FLUSH CALENDAR                                                           │  │
│  │  ┌─────────────┬─────────────┬─────────────┬─────────────┐               │  │
│  │  │ First Flush │ Monsoon     │ Autumn      │ Dormant     │               │  │
│  │  │ Mar 15-May 15│ Jun 1-Sep 30│ Oct 1-Nov 30│ Dec 1-Mar 14│               │  │
│  │  └─────────────┴─────────────┴─────────────┴─────────────┘               │  │
│  │                                                                           │  │
│  │  AGRONOMIC: Volcanic red soil │ Harvest: 06:00-10:00 │ Frost risk: Yes   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  RELATED DATA (Read-Only Summary)                                                │
│  ┌───────────────────────────────────┬───────────────────────────────────────┐  │
│  │  FACTORIES IN THIS REGION         │  FARMERS IN THIS REGION               │  │
│  │  ─────────────────────────────────│  ─────────────────────────────────────│  │
│  │  🏭 3 factories                   │  👨‍🌾 342 farmers (by farm GPS)         │  │
│  │  • Nyeri Tea Factory              │                                       │  │
│  │  • Karatina Processing            │  [View Farmers →]                     │  │
│  │  • Othaya Tea Factory             │  (opens Farmers filtered by region)   │  │
│  │                                   │                                       │  │
│  │  [View Factories →]               │                                       │  │
│  │  (opens Factories filtered)       │                                       │  │
│  └───────────────────────────────────┴───────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Region Edit Mode

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌍 Regions › NYERI HIGHLAND (Editing)                    [Save] [Cancel]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  REGION INFORMATION                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name:     [Nyeri Highland                                            ]   │  │
│  │  County:   [Nyeri                                                     ]   │  │
│  │  Country:  [Kenya                                                     ]   │  │
│  │                                                                           │  │
│  │  CENTER GPS                          RADIUS                               │  │
│  │  Latitude:  [-0.4197    ]            [25        ] km                      │  │
│  │  Longitude: [36.9553    ]                                                 │  │
│  │                                                                           │  │
│  │  ALTITUDE BAND                                                            │  │
│  │  [Highland (1800m+) ▼]                                                    │  │
│  │  Min: [1800] m    Max: [2500] m                                           │  │
│  │                                                                           │  │
│  │  STATUS                                                                   │  │
│  │  (●) Active  ( ) Inactive                                                 │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  FLUSH CALENDAR                                                           │  │
│  │  First Flush:   Start [03-15]  End [05-15]  Notes: [Highest quality   ]   │  │
│  │  Monsoon Flush: Start [06-01]  End [09-30]  Notes: [High volume       ]   │  │
│  │  Autumn Flush:  Start [10-01]  End [11-30]  Notes: [Balanced          ]   │  │
│  │  Dormant:       Start [12-01]  End [03-14]  Notes: [Minimal growth    ]   │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  AGRONOMIC FACTORS                                                        │  │
│  │  Soil Type:       [volcanic_red ▼]                                        │  │
│  │  Harvest Hours:   [06:00-10:00                                        ]   │  │
│  │  Frost Risk:      [✓] Yes                                                 │  │
│  │  Typical Diseases: [Blister blight, Red rust                          ]   │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  WEATHER API CONFIG                                                       │  │
│  │  API Location:    Lat [-0.4197]  Lng [36.9553]  Altitude [1850] m        │  │
│  │  Collection Time: [06:00]                                                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- BFF endpoints: `GET/POST /api/admin/regions`, `GET/PUT /api/admin/regions/:id`
- Backend: Plantation Service gRPC `ListRegions`, `CreateRegion`, `UpdateRegion`, `GetRegion`
- Region ID auto-generated: `{county}-{altitude_band}` (e.g., `nyeri-highland`)

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 1.8: Regional Weather Configuration (Plantation Service)

### Story Points: 5

---

## Story 9.3: Factory Management

As a **Platform Administrator**,
I want to view, create, edit, and manage factories,
So that I can onboard tea processing facilities for the pilot.

### Acceptance Criteria

**AC 9.3.1: Factory List View (Top-Level)**

**Given** I navigate to `/factories`
**When** the page loads
**Then** I see a table of all factories with:
  - Factory name and code
  - Region (linked)
  - Collection point count
  - Processing capacity
  - Status indicator (Active/Inactive)
**And** I can filter by region and status
**And** I can search by factory name or code

**AC 9.3.2: Factory Detail View (Hierarchical to CPs)**

**Given** I click on a factory row
**When** the factory detail page loads
**Then** I see the factory information panel (editable)
**And** I see a list of collection points in this factory
**And** I can click any collection point to drill down
**And** I can add a new collection point to this factory
**And** the breadcrumb shows: Factories › {Factory}

**AC 9.3.3: Factory Creation**

**Given** I click "+ Add Factory" from the factory list
**When** I complete the form
**Then** I provide:
  - Name, Code (unique identifier)
  - Region (dropdown selection)
  - Location (GPS coordinates)
  - Contact info (phone, email, address)
  - Processing capacity (kg)
  - Quality thresholds (Premium/Standard/Acceptable percentages)
  - Payment policy configuration
**And** the factory is created linked to the selected region
**And** I'm redirected to the new factory detail page

**AC 9.3.3: Factory Editing**

**Given** I'm on a factory detail page
**When** I click "Edit"
**Then** all factory fields become editable inline
**And** I can modify quality thresholds with live preview of farmer distribution
**And** I can configure payment policy (Split Payment, Weekly Bonus, etc.)
**And** changes are saved when I click "Save"

**AC 9.3.4: Factory Soft Delete**

**Given** I'm on a factory detail page with no active collection points
**When** I click "Deactivate Factory"
**Then** a confirmation dialog appears
**And** the factory status changes to Inactive
**And** the factory remains in the system but hidden from active lists

### Wireframe: Factory List (Top-Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 FACTORIES                                                   [+ Add Factory] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                                                                         │
│  Region: [All ▼]  Status: [All ▼]     Search: [🔍 Search factories...       ]   │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  NAME                │ CODE    │ REGION          │ CPs │ CAPACITY │STATUS│  │
│  │  ────────────────────┼─────────┼─────────────────┼─────┼──────────┼──────│  │
│  │  Nyeri Tea Factory   │ NTF-001 │ Nyeri Highland  │  3  │ 5,000 kg │ ● → │  │
│  │  Karatina Processing │ KTP-001 │ Nyeri Highland  │  2  │ 3,500 kg │ ● → │  │
│  │  Othaya Tea Factory  │ OTF-001 │ Nyeri Highland  │  4  │ 4,200 kg │ ● → │  │
│  │  Kericho Central     │ KCF-001 │ Kericho Highland│  5  │ 8,000 kg │ ● → │  │
│  │  Kisii Processing    │ KSP-001 │ Kisii Midland   │  2  │ 2,500 kg │ ○ → │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 12 factories                                  [← Previous] [Next →]    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Detail (with Collection Points)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NYERI TEA FACTORY                         [Edit] [← Back]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FACTORY INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name: Nyeri Tea Factory           Code: NTF-001       Status: ● Active   │  │
│  │  Region: Nyeri Highland            Capacity: 5,000 kg/day                 │  │
│  │                                                                           │  │
│  │  LOCATION                           CONTACT                               │  │
│  │  GPS: -0.4197, 36.9553             Phone: +254 712 345 678               │  │
│  │  Alt: 1,850m                        Email: admin@nyeritea.co.ke          │  │
│  │                                     Address: Nyeri Town, Kenya            │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  QUALITY THRESHOLDS                  PAYMENT POLICY                       │  │
│  │  🟢 Premium:   ≥85% Primary         Type: Weekly Bonus                   │  │
│  │  🟡 Standard:  ≥70% Primary         Premium: +15%                        │  │
│  │  🟠 Acceptable:≥50% Primary         Standard: Base rate                  │  │
│  │  🔴 Below Std: <50% Primary         Acceptable: -5%                      │  │
│  │                                      Below Std: -10%                      │  │
│  │                                                                           │  │
│  │  Grading Model: TBK-Binary v1.0     [Change Model]                       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  COLLECTION POINTS                                               [+ Add CP]     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  📍 Nyeri Central CP    │ Clerk: Peter K.  │ 52 farmers │ ● Active │ [→] │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │  📍 Karatina Market CP  │ Clerk: Jane M.   │ 48 farmers │ ● Active │ [→] │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │  📍 Othaya Junction CP  │ Clerk: -         │ 42 farmers │ ○ Inactive│ [→] │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  SUMMARY: 3 Collection Points │ 142 Total Farmers │ 2 Active Clerks            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Edit Mode

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NYERI TEA FACTORY (Editing)                [Save] [Cancel]      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FACTORY INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name:     [Nyeri Tea Factory                                         ]   │  │
│  │  Code:     [NTF-001              ] (unique)                               │  │
│  │                                                                           │  │
│  │  LOCATION                           CONTACT                               │  │
│  │  Latitude:  [-0.4197    ]          Phone: [+254 712 345 678          ]   │  │
│  │  Longitude: [36.9553    ]          Email: [admin@nyeritea.co.ke      ]   │  │
│  │  Altitude:  [1850       ] m        Address: [Nyeri Town, Kenya       ]   │  │
│  │                                                                           │  │
│  │  Processing Capacity: [5000       ] kg/day                                │  │
│  │                                                                           │  │
│  │  Status: (●) Active  ( ) Inactive                                         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  QUALITY THRESHOLDS                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  TIER              │  PRIMARY % THRESHOLD  │  CURRENT FARMERS            │  │
│  │  ──────────────────┼───────────────────────┼──────────────────────────   │  │
│  │  🟢 Premium        │  [≥ 85 %        ▲▼]  │  34 farmers (24%)           │  │
│  │  🟡 Standard       │  [≥ 70 %        ▲▼]  │  62 farmers (44%)           │  │
│  │  🟠 Acceptable     │  [≥ 50 %        ▲▼]  │  38 farmers (27%)           │  │
│  │  🔴 Below Standard │  [< 50 %          ]  │   8 farmers (5%)            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  PAYMENT POLICY                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Policy Type: [Weekly Bonus ▼]                                            │  │
│  │                                                                           │  │
│  │  TIER              │  PRICE ADJUSTMENT                                    │  │
│  │  ──────────────────┼────────────────────────────────────────────────────  │  │
│  │  🟢 Premium        │  [+15 %        ▲▼]                                   │  │
│  │  🟡 Standard       │  Base rate (no adjustment)                           │  │
│  │  🟠 Acceptable     │  [-5  %        ▲▼]                                   │  │
│  │  🔴 Below Standard │  [-10 %        ▲▼]                                   │  │
│  │                                                                           │  │
│  │  💰 Projected monthly impact: +KES 45,000 (more bonuses)                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Creation (Top-Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NEW FACTORY                               [Create] [Cancel]     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  BASIC INFORMATION                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Factory Name *     [                                                 ]   │  │
│  │  Factory Code *     [                  ] (e.g., NTF-001)                  │  │
│  │                                                                           │  │
│  │  Region *           [Select region ▼]                                     │  │
│  │                     • Nyeri Highland                                      │  │
│  │                     • Nyeri Midland                                       │  │
│  │                     • Kericho Highland                                    │  │
│  │                                                                           │  │
│  │  LOCATION                                                                 │  │
│  │  Latitude *         [             ]     Longitude * [             ]       │  │
│  │  Altitude           [             ] m                                     │  │
│  │                                                                           │  │
│  │  Processing Capacity * [             ] kg/day                             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  CONTACT INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Phone *            [+254                                             ]   │  │
│  │  Email              [                                                 ]   │  │
│  │  Address            [                                                 ]   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  QUALITY & PAYMENT (Optional - can configure later)                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  [ ] Use default thresholds (85/70/50%)                                   │  │
│  │  [ ] Use default payment policy (Feedback Only)                           │  │
│  │                                                                           │  │
│  │  [Configure custom thresholds ▼]                                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  * Required fields                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- BFF endpoints: `GET/POST /api/admin/factories`, `GET/PUT /api/admin/factories/:id`
- Backend: Plantation Service gRPC `ListFactories`, `CreateFactory`, `UpdateFactory`, `GetFactory`
- Quality threshold preview requires aggregating farmer performance data
- Payment policy impact calculation uses historical delivery data

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 9.2: Region Management
- Story 1.2: Factory and Collection Point Management (Plantation Service)

### Story Points: 5

---

## Story 9.4: Collection Point Management

As a **Platform Administrator**,
I want to view, create, edit, and manage collection points within a factory,
So that I can set up farmer registration and delivery locations for the pilot.

### Acceptance Criteria

**AC 9.4.1: Collection Point Detail View (Child of Factory)**

**Given** I click on a collection point from the factory detail page
**When** the collection point detail page loads
**Then** I see the collection point information panel (editable)
**And** I see a read-only summary of farmers with this CP as primary (count)
**And** the [View Farmers] link opens Farmers screen filtered by this CP
**And** the breadcrumb shows: Factories › {Factory} › {CP}

**AC 9.4.2: Collection Point Creation**

**Given** I click "+ Add CP" from a factory detail page
**When** I complete the form
**Then** I provide:
  - Name
  - Location (GPS coordinates)
  - Clerk assignment (ID, phone)
  - Operating hours (weekdays, weekends)
  - Collection days (checkboxes: Mon-Sun)
  - Capacity (max daily kg, storage type, equipment)
**And** the collection point is created linked to the current factory
**And** ID auto-generated: `{region}-cp-XXX`

**AC 9.4.3: Collection Point Editing**

**Given** I'm on a collection point detail page
**When** I click "Edit"
**Then** all collection point fields become editable inline
**And** I can assign/change the clerk
**And** I can update operating hours and collection days
**And** changes are saved when I click "Save"

**AC 9.4.4: Collection Point Status Management**

**Given** I'm on a collection point detail page
**When** I change the status dropdown
**Then** I can set: Active, Inactive, or Seasonal
**And** status change is logged for audit

### Wireframe: Collection Point Detail (Child of Factory)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › Nyeri Tea Factory › NYERI CENTRAL CP           [Edit] [← Back] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  COLLECTION POINT INFORMATION                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name: Nyeri Central CP              ID: nyeri-highland-cp-001            │  │
│  │  Status: ● Active                    Factory: Nyeri Tea Factory           │  │
│  │                                                                           │  │
│  │  LOCATION                           CLERK                                 │  │
│  │  GPS: -0.4232, 36.9587             Name: Peter Kamau                     │  │
│  │  Region: Nyeri Highland             Phone: +254 722 123 456              │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  OPERATING HOURS                    COLLECTION DAYS                       │  │
│  │  Weekdays: 06:00 - 10:00           [✓] Mon [✓] Tue [✓] Wed [✓] Thu       │  │
│  │  Weekends: 07:00 - 09:00           [✓] Fri [✓] Sat [ ] Sun               │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  CAPACITY & EQUIPMENT                                                     │  │
│  │  Max Daily: 500 kg                  Storage: Covered shed                 │  │
│  │  Weighing Scale: ✓ Yes              QC Device: ✓ Yes                     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  RELATED DATA (Read-Only Summary)                                                │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  👨‍🌾 52 farmers have this as their primary CP                              │  │
│  │                                                                           │  │
│  │  [View Farmers →] (opens Farmers screen filtered by this CP)             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Collection Point Edit Mode

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › Nyeri Tea Factory › NYERI CENTRAL CP (Edit)   [Save] [Cancel]  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  COLLECTION POINT INFORMATION                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name *         [Nyeri Central CP                                     ]   │  │
│  │  Status         [Active ▼]  (Active / Inactive / Seasonal)                │  │
│  │                                                                           │  │
│  │  LOCATION                                                                 │  │
│  │  Latitude *     [-0.4232       ]     Longitude * [36.9587        ]        │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  CLERK ASSIGNMENT                                                         │  │
│  │  Clerk ID       [clerk-peter-001                                      ]   │  │
│  │  Clerk Phone *  [+254 722 123 456                                     ]   │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  OPERATING HOURS                                                          │  │
│  │  Weekdays       Start [06:00]  End [10:00]                                │  │
│  │  Weekends       Start [07:00]  End [09:00]                                │  │
│  │                                                                           │  │
│  │  COLLECTION DAYS                                                          │  │
│  │  [✓] Mon  [✓] Tue  [✓] Wed  [✓] Thu  [✓] Fri  [✓] Sat  [ ] Sun          │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  CAPACITY & EQUIPMENT                                                     │  │
│  │  Max Daily Capacity    [500        ] kg                                   │  │
│  │  Storage Type          [Covered shed ▼]                                   │  │
│  │  Has Weighing Scale    [✓]                                                │  │
│  │  Has QC Device         [✓]                                                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  * Required fields                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- BFF endpoints: `GET/POST /api/admin/collection-points`, `GET/PUT /api/admin/collection-points/:id`
- Backend: Plantation Service gRPC `ListCollectionPoints`, `CreateCollectionPoint`, `UpdateCollectionPoint`
- Collection Point ID auto-generated from region: `{region_id}-cp-{sequence}`
- Farmer list includes 30-day primary percentage from aggregated performance data

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 9.3: Factory Management
- Story 1.2: Factory and Collection Point Management (Plantation Service)

### Story Points: 5

---

## Story 9.5: Farmer Management

As a **Platform Administrator**,
I want to view, create, edit, and manage farmers independently with powerful filtering,
So that I can quickly find and maintain any farmer record regardless of where they deliver.

### Acceptance Criteria

**AC 9.5.1: Farmer List View (Top-Level)**

**Given** I navigate to `/farmers`
**When** the page loads
**Then** I see a table of all farmers with:
  - Farmer ID and name
  - Phone number
  - Region (based on farm GPS)
  - Primary collection point
  - 30-day primary percentage with tier indicator
  - Status (Active/Inactive)
**And** I can filter by region, factory, collection point, and status
**And** I can search by name, phone, or farmer ID
**And** filters can be combined (e.g., Region=Nyeri AND Factory=NTF-001)

**AC 9.5.2: Farmer Detail View**

**Given** I click on a farmer row
**When** the farmer detail page loads
**Then** I see:
  - Personal information (name, phone, national ID)
  - Farm information (location, size, scale)
  - Region (auto-assigned from GPS) - displayed, not editable
  - Primary collection point (editable dropdown)
  - Communication preferences (channel, language, interaction mode)
  - Performance summary (30d/90d/yearly primary %, trend)
  - Delivery history (recent deliveries with grades)
**And** the breadcrumb shows: Farmers › {Farmer Name}

**AC 9.5.3: Farmer Creation**

**Given** I click "+ Add Farmer" from the farmer list
**When** I complete the form
**Then** I provide:
  - First name, Last name
  - Phone number (with duplicate check)
  - National ID (required)
  - Primary collection point (dropdown)
  - Farm location (GPS)
  - Farm size (hectares)
  - Grower number (optional legacy ID)
**And** the farmer is created with the selected primary CP
**And** farmer ID auto-generated: `WM-XXXX`
**And** region auto-assigned based on GPS + altitude (not from CP)

**AC 9.5.4: Farmer Editing**

**Given** I'm on a farmer detail page
**When** I click "Edit"
**Then** all farmer fields become editable inline
**And** I can update communication preferences
**And** I can change collection point assignment
**And** changes are saved when I click "Save"

**AC 9.5.5: Farmer CSV Import**

**Given** I click "Import" on the farmer list
**When** I upload a CSV file
**Then** I select a primary collection point for all imported farmers (or column in CSV)
**And** the system validates:
  - Required columns (first_name, last_name, phone, national_id, farm_lat, farm_lng, farm_size)
  - Phone number uniqueness
  - GPS coordinates validity
**And** shows preview of farmers to import with validation status
**And** imports valid records and reports errors for invalid ones
**And** region is auto-assigned per farmer based on their GPS

**AC 9.5.6: Farmer Deactivation**

**Given** I'm on a farmer detail page
**When** I click "Deactivate"
**Then** a confirmation dialog appears
**And** the farmer status changes to Inactive
**And** the farmer record is preserved for historical data

### Wireframe: Farmer List (Top-Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  👨‍🌾 FARMERS                                          [+ Add Farmer] [Import CSV]│
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                                                                         │
│  Region: [All ▼]  Factory: [All ▼]  Collection Point: [All ▼]  Status: [All ▼] │
│                                                                                  │
│  Search: [🔍 Search by name, phone, or ID...                               ]    │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ID      │ NAME             │ PHONE         │ REGION        │ PRIMARY CP  │  │
│  │  ────────┼──────────────────┼───────────────┼───────────────┼─────────────│  │
│  │  WM-0041 │ Wanjiku Muthoni  │ +254 712 345 6│ Nyeri Highland│ Nyeri Cntrl │  │
│  │          │                  │               │               │ 82% 🟡  ●  →│  │
│  │  ────────┼──────────────────┼───────────────┼───────────────┼─────────────│  │
│  │  WM-0042 │ James Kariuki    │ +254 733 456 7│ Nyeri Midland │ Karatina Mkt│  │
│  │          │                  │               │               │ 91% 🟢  ●  →│  │
│  │  ────────┼──────────────────┼───────────────┼───────────────┼─────────────│  │
│  │  WM-0043 │ Mary Wambui      │ +254 722 567 8│ Nyeri Highland│ Nyeri Cntrl │  │
│  │          │                  │               │               │ 45% 🔴  ●  →│  │
│  │  ────────┼──────────────────┼───────────────┼───────────────┼─────────────│  │
│  │  WM-0044 │ Peter Njoroge    │ +254 711 678 9│ Kericho Hland │ Kericho Cntl│  │
│  │          │                  │               │               │ 76% 🟡  ●  →│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 1,247 farmers                                 [← Previous] [Next →]    │
│                                                                                  │
│  Note: Region is based on farm GPS location, not factory/CP location.           │
│  A farmer in Nyeri Highland may deliver to a CP owned by a Nyeri Midland factory.│
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Farmer Detail View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  👨‍🌾 Farmers › WANJIKU MUTHONI (WM-0041)                       [Edit] [← Back]  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FARMER INFORMATION                                                              │
│  ┌─────────────────────────────────────┬─────────────────────────────────────┐  │
│  │  PERSONAL DETAILS                   │  FARM DETAILS                       │  │
│  │  ─────────────────────────────────  │  ─────────────────────────────────  │  │
│  │  Name: Wanjiku Muthoni              │  Location: -0.4201, 36.9542         │  │
│  │  ID: WM-0041                        │  Size: 1.5 hectares                 │  │
│  │  Phone: +254 712 345 678            │  Scale: 🏠 Medium                    │  │
│  │  National ID: 12345678              │  Region: Nyeri Highland             │  │
│  │  Status: ● Active                   │                                     │  │
│  │                                     │  REGISTRATION                       │  │
│  │  COMMUNICATION                      │  ─────────────────────────────────  │  │
│  │  ─────────────────────────────────  │  Date: 2024-03-15                   │  │
│  │  Channel: 📱 SMS                     │  Collection Point: Nyeri Central    │  │
│  │  Language: 🇰🇪 Swahili               │  Grower #: GRW-1234 (legacy)        │  │
│  │  Mode: 📖 Text (reads SMS)          │                                     │  │
│  └─────────────────────────────────────┴─────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  PERFORMANCE SUMMARY                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │    30 DAYS           90 DAYS           YEAR              TREND            │  │
│  │  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      │  │
│  │  │          │      │          │      │          │      │          │      │  │
│  │  │   82%    │      │   78%    │      │   75%    │      │    📈    │      │  │
│  │  │  Primary │      │  Primary │      │  Primary │      │ Improving│      │  │
│  │  │   🟡     │      │   🟡     │      │   🟡     │      │          │      │  │
│  │  └──────────┘      └──────────┘      └──────────┘      └──────────┘      │  │
│  │                                                                           │  │
│  │  Total Deliveries: 47 (30d) │ 142 (90d) │ 312 (year)                     │  │
│  │  Total Volume: 235 kg (30d) │ 710 kg (90d) │ 1,560 kg (year)             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  RECENT DELIVERIES                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Date       │ Weight │ Grade   │ Primary % │ Notes                        │  │
│  │  ───────────┼────────┼─────────┼───────────┼──────────────────────────────│  │
│  │  2025-01-13 │ 5.2 kg │ 🟢 Primary│ 85%      │ Good plucking               │  │
│  │  2025-01-11 │ 4.8 kg │ 🟡 Secondary│ 68%    │ Some coarse leaf            │  │
│  │  2025-01-09 │ 6.1 kg │ 🟢 Primary│ 91%      │ Excellent quality           │  │
│  │  2025-01-07 │ 5.5 kg │ 🟢 Primary│ 88%      │ -                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  [View Full History →]                                                          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Farmer Edit Mode

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌍 › ... › Nyeri Central CP › WANJIKU MUTHONI (Edit)      [Save] [Cancel]     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PERSONAL INFORMATION                                                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  First Name *      [Wanjiku                                           ]   │  │
│  │  Last Name *       [Muthoni                                           ]   │  │
│  │  Phone *           [+254 712 345 678                                  ]   │  │
│  │  National ID *     [12345678                                          ]   │  │
│  │  Grower Number     [GRW-1234                     ] (optional legacy ID)   │  │
│  │                                                                           │  │
│  │  Status            (●) Active  ( ) Inactive                               │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  FARM DETAILS                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Farm Location                                                            │  │
│  │  Latitude *        [-0.4201       ]     Longitude * [36.9542        ]     │  │
│  │                                                                           │  │
│  │  Farm Size *       [1.5           ] hectares                              │  │
│  │  Scale:            🏠 Medium (auto-calculated from size)                   │  │
│  │                                                                           │  │
│  │  Region:           Nyeri Highland (auto-assigned from GPS)                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  COLLECTION POINT ASSIGNMENT                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Collection Point  [Nyeri Central CP ▼]                                   │  │
│  │                    (Changing this will update farmer's primary CP)        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  COMMUNICATION PREFERENCES                                                       │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Notification Channel    [SMS ▼]                                          │  │
│  │                          • SMS (default)                                  │  │
│  │                          • WhatsApp                                       │  │
│  │                                                                           │  │
│  │  Preferred Language      [Swahili ▼]                                      │  │
│  │                          • Swahili (default)                              │  │
│  │                          • Kikuyu                                         │  │
│  │                          • Luo                                            │  │
│  │                          • English                                        │  │
│  │                                                                           │  │
│  │  Interaction Preference  [Text ▼]                                         │  │
│  │                          • Text (prefers reading)                         │  │
│  │                          • Voice (prefers IVR)                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  * Required fields                                                               │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  [🗑️ Deactivate Farmer]                                                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Farmer CSV Import

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  IMPORT FARMERS                                                    [× Close]    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Import farmers to: NYERI CENTRAL CP                                            │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  STEP 1: UPLOAD CSV                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │                    📁 Drag & drop CSV file here                           │  │
│  │                         or click to browse                                │  │
│  │                                                                           │  │
│  │  Required columns: first_name, last_name, phone, national_id,             │  │
│  │                    farm_lat, farm_lng, farm_size_hectares                 │  │
│  │                                                                           │  │
│  │  [📥 Download template CSV]                                               │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  STEP 2: VALIDATION PREVIEW                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ✅ 45 farmers ready to import                                            │  │
│  │  ⚠️  3 farmers have warnings (will import with defaults)                  │  │
│  │  ❌  2 farmers have errors (will be skipped)                              │  │
│  │                                                                           │  │
│  │  PREVIEW                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ Status │ Name            │ Phone          │ Issue                   │  │  │
│  │  │ ──────┼─────────────────┼────────────────┼─────────────────────────│  │  │
│  │  │ ✅    │ John Kamau      │ +254 711 111 1 │ -                       │  │  │
│  │  │ ✅    │ Jane Wanjiru    │ +254 722 222 2 │ -                       │  │  │
│  │  │ ⚠️    │ Peter Ochieng   │ +254 733 333 3 │ Missing farm size       │  │  │
│  │  │ ❌    │ Mary Akinyi     │ +254 744 444 4 │ Phone already exists    │  │  │
│  │  │ ❌    │ James Mwangi    │ invalid        │ Invalid phone format    │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  [Cancel]                                        [Import 45 Valid Farmers]      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- BFF endpoints: `GET/POST /api/admin/farmers`, `GET/PUT /api/admin/farmers/:id`, `POST /api/admin/farmers/import`
- Backend: Plantation Service gRPC `ListFarmers`, `CreateFarmer`, `UpdateFarmer`, `GetFarmer`, `GetFarmerByPhone`
- Farmer ID auto-generated: `WM-{sequence}` (4-digit padded)
- Farm scale auto-calculated: <1ha = Smallholder, 1-5ha = Medium, >5ha = Estate
- Region auto-assigned from GPS coordinates using Region service
- Phone duplicate check calls `GetFarmerByPhone` before creation
- CSV import uses streaming validation for large files

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 9.4: Collection Point Management
- Story 1.3: Farmer Registration (Plantation Service)

### Story Points: 8

---

## Story 9.6: Grading Model Management

As a **Platform Administrator**,
I want to view, create, edit, and assign grading models to factories,
So that I can configure quality assessment standards for the platform.

### Acceptance Criteria

**AC 9.6.1: Grading Model List View**

**Given** I navigate to `/grading-models`
**When** the page loads
**Then** I see a list of all grading models with:
  - Model ID and version
  - Crops name and market name
  - Grading type (Binary/Ternary/Multi-level)
  - Number of factories using this model
  - Status indicator
**And** I can search by model ID or crops name

**AC 9.6.2: Grading Model Detail View**

**Given** I click on a grading model
**When** the detail page loads
**Then** I see:
  - Model metadata (ID, version, regulatory authority)
  - Grading type and attributes configuration
  - Grade rules (rejection conditions)
  - Grade labels mapping
  - List of factories using this model

**AC 9.6.3: Grading Model Creation**

**Given** I click "+ Add Model"
**When** I complete the form
**Then** I provide:
  - Model ID, version, regulatory authority
  - Crops name, market name
  - Grading type (Binary/Ternary/Multi-level)
  - Attributes with classes
  - Grade rules (reject conditions)
  - Grade labels
**And** the model is created and available for factory assignment

**AC 9.6.4: Factory Assignment**

**Given** I'm on a grading model detail page
**When** I click "Assign to Factory"
**Then** I see a list of factories not using this model
**And** I can select one or more factories
**And** the model is assigned to selected factories

### Wireframe: Grading Model List

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 GRADING MODELS                                              [+ Add Model]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Search: [🔍 Search models...                                              ]    │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  MODEL ID        │ TYPE    │ CROPS    │ MARKET │ FACTORIES │ STATUS │     │  │
│  │  ────────────────┼─────────┼──────────┼────────┼───────────┼────────┼──── │  │
│  │  TBK-Binary-v1.0 │ Binary  │ Tea      │ Kenya  │ 12        │ Active │  →  │  │
│  │  TBK-Ternary-v1.0│ Ternary │ Tea      │ Export │  3        │ Active │  →  │  │
│  │  KTDA-Multi-v2.1 │ Multi   │ Tea      │ Kenya  │  5        │ Active │  →  │  │
│  │  Coffee-Binary   │ Binary  │ Coffee   │ Kenya  │  0        │ Draft  │  →  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 4 grading models                                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Grading Model Detail

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 Grading Models › TBK-BINARY-V1.0                           [Edit] [← Back] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  MODEL INFORMATION                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Model ID: TBK-Binary-v1.0          Version: 1.0                          │  │
│  │  Regulatory Authority: Tea Board of Kenya                                 │  │
│  │  Crops: Tea                          Market: Kenya Domestic               │  │
│  │  Grading Type: Binary (Primary/Secondary)                                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADING ATTRIBUTES                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ATTRIBUTE         │ CLASSES                                              │  │
│  │  ──────────────────┼────────────────────────────────────────────────────  │  │
│  │  leaf_appearance   │ fine_plucking, coarse_plucking, withered, damaged   │  │
│  │  leaf_maturity     │ two_leaves_bud, three_leaves, mature_leaf           │  │
│  │  foreign_matter    │ none, minimal, moderate, excessive                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE RULES                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ALWAYS REJECT:                                                           │  │
│  │  • leaf_appearance = damaged                                              │  │
│  │  • foreign_matter = excessive                                             │  │
│  │                                                                           │  │
│  │  CONDITIONAL REJECT:                                                      │  │
│  │  • IF leaf_maturity = mature_leaf AND leaf_appearance = withered → REJECT│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE LABELS                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  primary   → "Primary Grade" (Premium quality)                            │  │
│  │  secondary → "Secondary Grade" (Standard quality)                         │  │
│  │  reject    → "Rejected" (Below standard)                                  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  FACTORIES USING THIS MODEL                                 [+ Assign Factory]  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  🏭 Nyeri Tea Factory       │ Nyeri Highland    │ Since: 2024-03-15       │  │
│  │  🏭 Karatina Processing     │ Nyeri Highland    │ Since: 2024-04-01       │  │
│  │  🏭 Kericho Central         │ Kericho Highland  │ Since: 2024-03-20       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  12 factories using this model                                                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Grading Model Edit/Create

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 NEW GRADING MODEL                                       [Create] [Cancel]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  MODEL INFORMATION                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Model ID *          [                                                ]   │  │
│  │  Version *           [1.0                                             ]   │  │
│  │  Regulatory Authority [                                               ]   │  │
│  │  Crops Name *        [Tea                                             ]   │  │
│  │  Market Name *       [                                                ]   │  │
│  │                                                                           │  │
│  │  Grading Type *      [Binary ▼]                                           │  │
│  │                      • Binary (Primary/Secondary)                         │  │
│  │                      • Ternary (Premium/Standard/Reject)                  │  │
│  │                      • Multi-level (A/B/C/D or custom)                    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADING ATTRIBUTES                                            [+ Add Attribute]│
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Attribute 1                                                              │  │
│  │  Name:    [leaf_appearance                                            ]   │  │
│  │  Classes: [fine_plucking, coarse_plucking, withered, damaged          ]   │  │
│  │                                                              [🗑️ Remove] │  │
│  │  ───────────────────────────────────────────────────────────────────────  │  │
│  │  Attribute 2                                                              │  │
│  │  Name:    [leaf_maturity                                              ]   │  │
│  │  Classes: [two_leaves_bud, three_leaves, mature_leaf                  ]   │  │
│  │                                                              [🗑️ Remove] │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE RULES                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ALWAYS REJECT (select attribute values that always cause rejection):     │  │
│  │  leaf_appearance:  [ ] fine  [ ] coarse  [ ] withered  [✓] damaged       │  │
│  │  foreign_matter:   [ ] none  [ ] minimal [ ] moderate  [✓] excessive     │  │
│  │                                                                           │  │
│  │  CONDITIONAL RULES                                       [+ Add Rule]    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │ IF [leaf_maturity ▼] = [mature_leaf ▼]                              │ │  │
│  │  │ AND [leaf_appearance ▼] = [withered ▼]                              │ │  │
│  │  │ THEN → REJECT                                         [🗑️ Remove]  │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE LABELS                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  primary   → [Primary Grade                                           ]   │  │
│  │  secondary → [Secondary Grade                                         ]   │  │
│  │  reject    → [Rejected                                                ]   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  * Required fields                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- BFF endpoints: `GET/POST /api/admin/grading-models`, `GET/PUT /api/admin/grading-models/:id`
- Backend: Plantation Service gRPC `CreateGradingModel`, `GetGradingModel`, `AssignGradingModelToFactory`
- Grading model attributes support dynamic configuration per TBK standards
- Factory assignment updates both GradingModel.active_at_factory[] and Factory record

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 1.6: Grading Model Configuration (Plantation Service)

### Story Points: 5

---

## Story 9.7: User Management Dashboard

As a **Platform Administrator**,
I want to view and manage users across all factories,
So that I can support user administration tasks.

### Acceptance Criteria

**AC 9.7.1: User List View**

**Given** I navigate to `/users`
**When** the page loads
**Then** I see a table of all platform users with:
  - Name, email
  - Factory assignment
  - Role (platform_admin, factory_admin, factory_manager, clerk)
  - Last login date
  - Status (Active/Disabled)
**And** I can search by name or email
**And** I can filter by factory, role, status

**AC 9.7.2: User Creation**

**Given** I click "+ Add User"
**When** I complete the form
**Then** I provide: name, email, factory (dropdown), role (dropdown)
**And** user is created in Azure AD B2C
**And** welcome email is sent automatically

**AC 9.7.3: User Editing**

**Given** I click on a user row
**When** the user detail panel opens
**Then** I can edit: role, factory assignment
**And** I can reset password (sends reset email)
**And** I can disable/enable account

### Wireframe: User Management

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  👤 USER MANAGEMENT                                              [+ Add User]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                                                                         │
│  Factory: [All ▼]  Role: [All ▼]  Status: [All ▼]  Search: [🔍            ]    │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  NAME            │ EMAIL                │ FACTORY    │ ROLE      │ STATUS │  │
│  │  ────────────────┼──────────────────────┼────────────┼───────────┼────────│  │
│  │  Joseph Kamau    │ joseph@nyeritea.co.ke│ Nyeri Tea  │ Manager   │ ● Active│  │
│  │  Peter Admin     │ peter@farmerpower.ke │ -          │ Platform  │ ● Active│  │
│  │  Jane Wanjiru    │ jane@karatina.co.ke  │ Karatina   │ Admin     │ ● Active│  │
│  │  Mary Clerk      │ mary@nyeritea.co.ke  │ Nyeri Tea  │ Clerk     │ ○ Disabled│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 24 users                                      [← Previous] [Next →]    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- Users stored in Azure AD B2C (not local DB)
- Microsoft Graph API for user operations
- Audit log to MongoDB for compliance

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 0.5.2: Azure AD B2C Configuration

### Story Points: 5

---

## Story 9.8: Platform Health Dashboard

As a **Platform Administrator**,
I want to see platform-wide health metrics and factory statistics,
So that I can monitor operations and identify issues.

### Acceptance Criteria

**AC 9.8.1: Dashboard Overview**

**Given** I navigate to `/health`
**When** the page loads
**Then** I see:
  - Total factories, total farmers, active users (24h)
  - System health indicators: API latency, error rate, queue depth
  - Map showing factory locations with status indicators

**AC 9.8.2: Factory Drill-down**

**Given** I click on a factory card/pin
**Then** I see: farmer count, daily delivery volume, quality trend
**And** recent activity log for that factory

**AC 9.8.3: Alert Display**

**Given** there are system issues
**When** error rate exceeds threshold
**Then** alert banner shows on dashboard
**And** affected services are highlighted

### Wireframe: Platform Health

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📈 PLATFORM HEALTH                                          [🔄 Refresh]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PLATFORM OVERVIEW                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐               │
│  │  🏭 12           │  │  👨‍🌾 1,247        │  │  👤 45            │               │
│  │  Active Factories│  │  Total Farmers   │  │  Active Users(24h)│               │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘               │
│                                                                                  │
│  SYSTEM HEALTH                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  API Gateway    ✅ 45ms avg      │  Message Queue  ✅ 23 pending          │  │
│  │  Plantation Svc ✅ 32ms avg      │  SMS Gateway    ✅ 99.2% delivered     │  │
│  │  Collection Svc ✅ 28ms avg      │  Voice IVR      ✅ Operational         │  │
│  │  AI Model Svc   ✅ 1.2s avg      │  Weather API    ✅ Connected           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  FACTORY MAP                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           🇰🇪 KENYA                                        │  │
│  │                                                                           │  │
│  │              🟢 Nyeri (3)                                                 │  │
│  │                    🟢 Karatina                                            │  │
│  │                                                                           │  │
│  │                              🟢 Kericho (4)                               │  │
│  │                                   🟡 Kisii (1 issue)                      │  │
│  │                                                                           │  │
│  │  Legend: 🟢 Healthy  🟡 Warning  🔴 Critical                              │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- Aggregated metrics from OpenTelemetry
- Health checks from each service
- Map: Leaflet with Kenya regions

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 0.5.6: BFF Service Setup

### Story Points: 5

---

## Story 9.9: Knowledge Management Interface

As a **Platform Administrator or Agronomist**,
I want to upload and manage expert knowledge documents,
So that AI recommendations are powered by verified expert content.

**Key Insight:** Agronomists shouldn't need to understand PDF extraction methods. The system auto-detects whether a PDF is digital (text-based) or scanned (needs OCR) and handles extraction automatically.

### Acceptance Criteria

**AC 9.9.1: Knowledge Document Library**

**Given** I navigate to `/knowledge`
**When** the page loads
**Then** I see a library of all knowledge documents
**And** I can filter by domain (Plant Diseases, Tea Cultivation, Weather, Quality Standards, Regional)
**And** I can filter by status (Draft, Staged, Active, Archived)
**And** search is available across document titles and content

**AC 9.9.2: Document Upload with Auto-Extraction**

**Given** I click "+ Upload Document"
**When** I upload a PDF, DOCX, MD, or TXT file
**Then** I enter metadata: title, domain, author, source, region
**And** system auto-detects extraction method (text vs OCR vs Vision)
**And** I see extraction progress with confidence score
**And** I can preview and edit extracted content before saving

**AC 9.9.3: Extraction Quality Handling**

**Given** extraction confidence is low (<80%)
**When** the extraction completes
**Then** system shows quality warning with specific issues
**And** offers options: try Vision AI, edit manually, upload clearer scan
**And** I can continue anyway if content is acceptable

**AC 9.9.4: Document Review & Activation**

**Given** I want to review a staged document
**When** I open the document review screen
**Then** I can preview the full content
**And** I can test with AI (ask questions, verify retrieval)
**And** I must check approval boxes before activating
**And** activation moves document to production namespace

**AC 9.9.5: Version Management**

**Given** I need to update an active document
**When** I edit and save
**Then** new version is created (old version archived)
**And** change summary is required
**And** version history shows all versions with rollback option

### Wireframe: Knowledge Document Library

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📚 KNOWLEDGE MANAGEMENT                               [+ Upload Document]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FILTER BY DOMAIN        SEARCH                                              │
│  ┌──────────────────┐   ┌────────────────────────────────────────────────┐  │
│  │ [x] All Domains  │   │  🔍 Search documents...                        │  │
│  │ [ ] Plant Disease│   └────────────────────────────────────────────────┘  │
│  │ [ ] Tea Cultiv.  │                                                       │
│  │ [ ] Weather      │   DOCUMENTS                                           │
│  │ [ ] Quality Std  │   ┌────────────────────────────────────────────────┐  │
│  │ [ ] Regional     │   │  📄 Blister Blight Treatment Guide    v2.1     │  │
│  └──────────────────┘   │     Plant Diseases • Dr. Njeri Kamau • Active  │  │
│                         │     Updated: 2025-12-15                        │  │
│  FILTER BY STATUS       │                                       [View →] │  │
│  ┌──────────────────┐   ├────────────────────────────────────────────────┤  │
│  │ 🟢 Active    (24)│   │  📄 Optimal Plucking Techniques      v1.0     │  │
│  │ 🟡 Staged     (3)│   │     Tea Cultivation • J. Odhiambo • Staged    │  │
│  │ 📝 Draft      (5)│   │     Ready for review since: 2025-12-20        │  │
│  │ 📦 Archived   (8)│   │                             [Review →] [Edit] │  │
│  └──────────────────┘   ├────────────────────────────────────────────────┤  │
│                         │  📄 Weather Pattern Recognition       v3.0     │  │
│                         │     Weather Patterns • TBK • Active            │  │
│                         │     Updated: 2025-11-28                        │  │
│                         │                                       [View →] │  │
│                         └────────────────────────────────────────────────┘  │
│                                                                              │
│  Showing 32 documents • Page 1 of 4              [← Previous] [Next →]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Document Upload - Step 1 (Upload & Metadata)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  UPLOAD NEW DOCUMENT                                         Step 1 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │                    📁 Drag & drop your file here                       │  │
│  │                         or click to browse                             │  │
│  │                                                                        │  │
│  │                   Supported: PDF, DOCX, MD, TXT                        │  │
│  │                   Max size: 50MB                                       │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ─────────────────────────── OR ───────────────────────────────────────     │
│                                                                              │
│  [📝 Write content directly] (opens rich text editor)                       │
│                                                                              │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DOCUMENT DETAILS                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Title:     [                                                      ]  │  │
│  │                                                                        │  │
│  │  Domain:    [Select domain ▼]                                         │  │
│  │             • Plant Diseases                                          │  │
│  │             • Tea Cultivation                                         │  │
│  │             • Weather Patterns                                        │  │
│  │             • Quality Standards                                       │  │
│  │             • Regional Context                                        │  │
│  │                                                                        │  │
│  │  Author:    [Your name                                             ]  │  │
│  │  Source:    [e.g., TBK Research Paper, Field Study, etc.           ]  │  │
│  │  Region:    [Select region (optional) ▼]                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [Cancel]                                                    [Continue →]   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Document Upload - Step 2 (Processing)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PROCESSING DOCUMENT                                         Step 2 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 blister-blight-treatment-guide.pdf                                      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ⏳ Analyzing document...                                              │  │
│  │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%       │  │
│  │                                                                        │  │
│  │  ✅ Detected: Scanned PDF with embedded images                        │  │
│  │  ✅ Using: Azure Document Intelligence (OCR)                          │  │
│  │  ⏳ Extracting text from 12 pages...                                   │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ℹ️ This may take 1-2 minutes for large documents                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Document Upload - Step 2b (Content Preview)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REVIEW EXTRACTED CONTENT                                    Step 2 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 Blister Blight Treatment Guide                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Extraction: ✅ Completed • Confidence: 94% • Pages: 12                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  EXTRACTED CONTENT                                              [Edit ✏️]   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  # Blister Blight (Exobasidium vexans)                                │  │
│  │                                                                        │  │
│  │  ## Identification                                                     │  │
│  │  Blister blight appears as small, circular, translucent spots on      │  │
│  │  young leaves. As the disease progresses, blisters become convex      │  │
│  │  on the upper surface and concave on the lower surface...             │  │
│  │                                                                        │  │
│  │  ## Environmental Conditions                                          │  │
│  │  - High humidity (>85%)                                               │  │
│  │  - Temperature: 18-22°C                                               │  │
│  │  - Rainfall during plucking season                                    │  │
│  │                                                                        │  │
│  │  ## Treatment Recommendations                                         │  │
│  │  1. Remove and destroy infected shoots                                │  │
│  │  2. Apply copper-based fungicide...                                   │  │
│  │                                                                        │  │
│  │  [... scroll for more content ...]                                    │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ⚠️ Please verify the extracted content is accurate. You can edit          │
│     directly or re-upload if extraction quality is poor.                    │
│                                                                              │
│  [← Back]    [🔄 Re-extract with different method]         [Continue →]     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Low Confidence Warning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚠️ EXTRACTION QUALITY WARNING                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  The automatic extraction achieved 62% confidence.                          │
│  Some content may be missing or incorrectly extracted.                      │
│                                                                              │
│  POSSIBLE ISSUES DETECTED:                                                   │
│  • Handwritten notes on pages 3, 7                                          │
│  • Low resolution images/diagrams on pages 5-6                              │
│  • Complex table on page 8                                                  │
│                                                                              │
│  RECOMMENDED ACTIONS:                                                        │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  [🔍 Try Vision AI extraction]                                     │     │
│  │      Best for: diagrams, handwritten notes, complex layouts        │     │
│  │                                                                     │     │
│  │  [✏️ Edit extracted content manually]                              │     │
│  │      Fix specific sections that weren't captured correctly         │     │
│  │                                                                     │     │
│  │  [📄 Upload clearer scan]                                          │     │
│  │      If original document quality is poor                          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  [← Back]                                          [Continue anyway →]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Document Upload - Step 3 (Save)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SAVE DOCUMENT                                               Step 3 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DOCUMENT SUMMARY                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Title:      Blister Blight Treatment Guide                           │  │
│  │  Domain:     Plant Diseases                                           │  │
│  │  Author:     Dr. Njeri Kamau                                          │  │
│  │  Source:     TBK Research Paper 2024                                  │  │
│  │  Region:     All regions                                              │  │
│  │  Pages:      12                                                       │  │
│  │  Word count: ~3,200 words                                             │  │
│  │  Extraction: Azure Document Intelligence (94% confidence)             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  SAVE AS                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ○ 📝 Draft                                                           │  │
│  │       Save for later editing. Not visible to AI agents.               │  │
│  │                                                                        │  │
│  │  ● 🟡 Staged (Recommended)                                            │  │
│  │       Ready for review. Test with AI before going live.               │  │
│  │                                                                        │  │
│  │  ○ 🟢 Active (Requires approval)                                      │  │
│  │       Immediately available to AI agents.                             │  │
│  │       Note: Only Platform Admins can activate directly.               │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [← Back]                                         [Save as Staged ✓]        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Document Review & Activation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REVIEW DOCUMENT                                              [Activate ▼]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 Blister Blight Treatment Guide                           Status: Staged │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DOCUMENT INFO               │  TEST WITH AI                                │
│  ┌─────────────────────────┐ │  ┌───────────────────────────────────────┐   │
│  │ Domain: Plant Diseases  │ │  │ Ask a test question:                  │   │
│  │ Author: Dr. Njeri Kamau │ │  │                                       │   │
│  │ Version: 1.0            │ │  │ [What causes blister blight?      ]   │   │
│  │ Created: 2025-12-22     │ │  │                                       │   │
│  │                         │ │  │ [Test →]                              │   │
│  │ Previous versions: None │ │  │                                       │   │
│  └─────────────────────────┘ │  │ AI Response:                          │   │
│                              │  │ "Blister blight is caused by the      │   │
│  CONTENT PREVIEW             │  │  fungus Exobasidium vexans. It        │   │
│  ┌─────────────────────────┐ │  │  thrives in humid conditions..."      │   │
│  │ # Blister Blight        │ │  │                                       │   │
│  │                         │ │  │ ✅ Document content retrieved         │   │
│  │ ## Identification       │ │  │    successfully                       │   │
│  │ Blister blight appears  │ │  └───────────────────────────────────────┘   │
│  │ as small, circular...   │ │                                              │
│  │                         │ │                                              │
│  │ [View full content →]   │ │                                              │
│  └─────────────────────────┘ │                                              │
│                              │                                              │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  APPROVAL                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ☐ I have reviewed the content for accuracy                          │  │
│  │  ☐ I have tested AI retrieval with sample questions                  │  │
│  │  ☐ I approve this document for production use                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [← Back to Library]    [Edit]    [Reject]    [🟢 Activate for Production]  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Version History

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VERSION HISTORY: Blister Blight Treatment Guide                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ v2.1 (Active)                                      2025-12-15 10:30    │ │
│  │ Updated treatment recommendations per 2025 TBK guidelines              │ │
│  │ Author: Dr. Njeri Kamau                                                │ │
│  │                                                    [View] [Rollback]   │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ v2.0 (Archived)                                    2025-09-01 14:22    │ │
│  │ Added regional variations section                                      │ │
│  │ Author: J. Odhiambo                                                    │ │
│  │                                                    [View] [Compare]    │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ v1.0 (Archived)                                    2025-06-15 09:45    │ │
│  │ Initial version                                                        │ │
│  │ Author: Dr. Njeri Kamau                                                │ │
│  │                                                    [View] [Compare]    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Document Lifecycle States

| State | Icon | Description | Who Can Access |
|-------|------|-------------|----------------|
| **Draft** | 📝 | Work in progress, not indexed | Author only |
| **Staged** | 🟡 | Ready for review, test namespace | Reviewers + Admins |
| **Active** | 🟢 | Live in production, used by AI | All AI agents |
| **Archived** | 📦 | Deprecated, kept for history | Admins only |

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Auto-detect extraction method** | Agronomists shouldn't need to understand OCR vs text extraction |
| **Show confidence score** | Transparency about extraction quality |
| **Preview before save** | Catch extraction errors early |
| **Staged testing** | Verify AI retrieval works before production |
| **Version history** | Maintain audit trail and enable rollback |
| **Test with AI** | Verify document is properly indexed and retrievable |

### Technical Notes
- Location: `web/platform-admin/src/pages/knowledge/`
- API: gRPC RAGDocumentService via BFF
- PDF extraction: PyMuPDF (digital), Azure Document Intelligence (scanned), Vision LLM (diagrams)
- Vector storage: Pinecone with namespace versioning (test vs production)
- Document storage: MongoDB + Azure Blob Storage for original files

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- AI Model RAG Document API

### Story Points: 8

---

## Story 9.10: Platform Cost Dashboard

As a **Platform Administrator**,
I want a comprehensive cost dashboard to monitor all platform spending,
So that I can track total costs, understand cost drivers by service, and configure budget alerts.

### Acceptance Criteria

**AC 9.10.1:** Total Cost Overview
- Display aggregated cost across all services for selected period
- Show cost trend chart (daily/weekly/monthly)
- Display cost breakdown by service category (pie chart)
- Show month-to-date vs. previous month comparison

**AC 9.10.2:** Service Cost List
- List all services with their costs
- Show: Service name, category, cost (period), % of total, trend indicator
- Sortable by cost, name, or trend
- Click service row to drill into service detail

**AC 9.10.3:** Service Detail Views
- **LLM Costs**: Agent breakdown, model breakdown, request counts, top cost drivers
- **SMS Costs**: Message count, cost per region, cost per message type (notification, alert)
- **Voice IVR Costs**: Call minutes, cost per region, cost per farmer segment
- **Weather API Costs**: Request count, cost by endpoint
- **Storage Costs**: MongoDB storage, MinIO storage, backup costs
- **Compute Costs**: Kubernetes node hours, service resource usage
- **External APIs**: Google Elevation API, other third-party services

**AC 9.10.4:** Date Range and Export
- Preset ranges: Last 7 days, Last 30 days, This month, Last month, Custom
- Export to CSV (all services or selected service)
- Export to PDF report with charts

**AC 9.10.5:** Budget Alerts Configuration
- Set budget threshold per service or total
- Configure alert recipients (email)
- Alert levels: Warning (80%), Critical (100%)

### Wireframe: Total Cost Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  💰 PLATFORM COSTS                                      [Export ▼] [⚙ Alerts]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  [Total Overview]  [LLM]  [SMS]  [Voice]  [Weather]  [Storage]  [Compute]       │
│  ═══════════════                                                                 │
│                                                                                  │
│  DATE RANGE: [Last 30 days ▼]  [Custom: _____ to _____]                         │
│                                                                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐            │
│  │  TOTAL COST       │  │  VS LAST PERIOD   │  │  PROJECTED MTD    │            │
│  │  $2,847.50        │  │  ↑ 8.3%           │  │  $3,200.00        │            │
│  │  Last 30 days     │  │  +$218.40         │  │  Budget: $4,000   │            │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  DAILY COST TREND (All Services)                                         │   │
│  │  $150 ─┬─────────────────────────────────────────────────────────────    │   │
│  │        │        ╭──╮    ╭──╮                                              │   │
│  │  $100 ─┼───────╱    ╲──╱    ╲─────╱╲────────────────────────────────     │   │
│  │        │      ╱              ╲───╱  ╲                                     │   │
│  │   $50 ─┼─────╱                                                           │   │
│  │        │                                                                  │   │
│  │    $0 ─┴──────────────────────────────────────────────────────────────   │   │
│  │        1   5   10   15   20   25   30                                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  COST BY SERVICE                │  │  COST BY CATEGORY                    │   │
│  │  ┌─────────────────────────┐    │  │  ┌─────────────────────────────┐    │   │
│  │  │       ████  LLM 42%     │    │  │  │  AI/ML Services    │ 45%   │    │   │
│  │  │    ███      SMS 25%     │    │  │  │  Communications    │ 35%   │    │   │
│  │  │  ██         Voice 10%   │    │  │  │  Infrastructure    │ 15%   │    │   │
│  │  │  █          Other 23%   │    │  │  │  External APIs     │ 5%    │    │   │
│  │  └─────────────────────────┘    │  │  └─────────────────────────────┘    │   │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                                  │
│  SERVICE BREAKDOWN                                                               │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Service            │ Category       │ Cost (30d) │ % Total │ Trend     │   │
│  │  ──────────────────-┼────────────────┼────────────┼─────────┼───────────│   │
│  │  🤖 LLM (OpenRouter) │ AI/ML          │ $1,195.50  │ 42%     │ ↑ 12% [→] │   │
│  │  📱 SMS (AT)         │ Communications │ $712.00    │ 25%     │ → 0%  [→] │   │
│  │  📞 Voice IVR (AT)   │ Communications │ $284.80    │ 10%     │ ↓ 5%  [→] │   │
│  │  🌤 Weather API      │ External APIs  │ $142.40    │ 5%      │ ↑ 3%  [→] │   │
│  │  💾 Storage          │ Infrastructure │ $284.80    │ 10%     │ → 0%  [→] │   │
│  │  ⚙ Compute           │ Infrastructure │ $142.40    │ 5%      │ ↓ 2%  [→] │   │
│  │  🌍 Google Elevation │ External APIs  │ $85.60     │ 3%      │ → 0%  [→] │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                          [→] = Click to view service details    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: LLM Cost Detail (Tab View)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  💰 PLATFORM COSTS                                      [Export ▼] [⚙ Alerts]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  [Total Overview]  [LLM]  [SMS]  [Voice]  [Weather]  [Storage]  [Compute]       │
│                    ═════                                                         │
│                                                                                  │
│  DATE RANGE: [Last 30 days ▼]  [Custom: _____ to _____]                         │
│                                                                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐            │
│  │  LLM TOTAL        │  │  REQUESTS         │  │  AVG COST/REQ     │            │
│  │  $1,195.50        │  │  45,230           │  │  $0.026           │            │
│  │  42% of total     │  │  Last 30 days     │  │  ↓ 5% vs prev     │            │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  DAILY LLM COST TREND                                                    │   │
│  │  $50 ─┬─────────────────────────────────────────────────────────────     │   │
│  │       │     ╭──╮                                                         │   │
│  │  $25 ─┼────╱    ╲────────╱╲──────────────────────────────────────────    │   │
│  │       │   ╱      ╲──────╱  ╲                                             │   │
│  │   $0 ─┴──────────────────────────────────────────────────────────────    │   │
│  │       1   5   10   15   20   25   30                                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  COST BY AGENT TYPE             │  │  COST BY MODEL                       │   │
│  │  Explorer: 45%                  │  │  claude-sonnet: 60%                  │   │
│  │  Generator: 30%                 │  │  gpt-4o-mini: 25%                    │   │
│  │  Vision: 15%                    │  │  gpt-4o: 15%                         │   │
│  │  Other: 10%                     │  │                                      │   │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                                  │
│  TOP COST DRIVERS                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Agent ID              │ Type       │ Requests │ Cost (30d) │ Trend      │   │
│  │  ──────────────────────┼────────────┼──────────┼────────────┼────────────│   │
│  │  disease-diagnosis     │ Explorer   │ 12,340   │ $452.00    │ ↑ 12%      │   │
│  │  weekly-action-plan    │ Generator  │ 8,920    │ $321.00    │ ↓ 5%       │   │
│  │  leaf-image-analyzer   │ Vision     │ 5,670    │ $185.00    │ → 0%       │   │
│  │  rag-query             │ Explorer   │ 4,200    │ $112.50    │ ↑ 8%       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: SMS Cost Detail (Tab View)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  💰 PLATFORM COSTS                                      [Export ▼] [⚙ Alerts]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  [Total Overview]  [LLM]  [SMS]  [Voice]  [Weather]  [Storage]  [Compute]       │
│                          ═════                                                   │
│                                                                                  │
│  DATE RANGE: [Last 30 days ▼]  [Custom: _____ to _____]                         │
│                                                                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐            │
│  │  SMS TOTAL        │  │  MESSAGES SENT    │  │  AVG COST/MSG     │            │
│  │  $712.00          │  │  35,600           │  │  $0.02            │            │
│  │  25% of total     │  │  Last 30 days     │  │  Safaricom rate   │            │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  DAILY SMS COST TREND                                                    │   │
│  │  $35 ─┬─────────────────────────────────────────────────────────────     │   │
│  │       │  ╭╮    ╭╮    ╭╮    ╭╮    ╭╮    ╭╮    ╭╮                         │   │
│  │  $20 ─┼──╯╰────╯╰────╯╰────╯╰────╯╰────╯╰────╯╰──────────────────────    │   │
│  │       │                                                                  │   │
│  │   $0 ─┴──────────────────────────────────────────────────────────────    │   │
│  │       1   5   10   15   20   25   30                                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  Note: Spikes on Mondays = Weekly action plan notifications                     │
│                                                                                  │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  COST BY MESSAGE TYPE           │  │  COST BY REGION                      │   │
│  │  Action Plans: 55%              │  │  Nyeri Highland: 35%                 │   │
│  │  Alerts: 25%                    │  │  Muranga Midland: 28%                │   │
│  │  Reminders: 15%                 │  │  Kiambu Lowland: 22%                 │   │
│  │  Other: 5%                      │  │  Other: 15%                          │   │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                                  │
│  SMS BY RECIPIENT SEGMENT                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Segment             │ Farmers   │ Messages │ Cost (30d) │ Delivery %   │   │
│  │  ────────────────────┼───────────┼──────────┼────────────┼──────────────│   │
│  │  Active Farmers      │ 1,234     │ 28,500   │ $570.00    │ 98.5%        │   │
│  │  At-Risk Farmers     │ 156       │ 4,200    │ $84.00     │ 97.2%        │   │
│  │  New Registrations   │ 89        │ 2,900    │ $58.00     │ 99.1%        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Voice IVR Cost Detail (Tab View)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  💰 PLATFORM COSTS                                      [Export ▼] [⚙ Alerts]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  [Total Overview]  [LLM]  [SMS]  [Voice]  [Weather]  [Storage]  [Compute]       │
│                                  ═══════                                         │
│                                                                                  │
│  DATE RANGE: [Last 30 days ▼]  [Custom: _____ to _____]                         │
│                                                                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐            │
│  │  VOICE TOTAL      │  │  CALL MINUTES     │  │  AVG COST/MIN     │            │
│  │  $284.80          │  │  2,848            │  │  $0.10            │            │
│  │  10% of total     │  │  Last 30 days     │  │  AT Voice rate    │            │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘            │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  DAILY VOICE COST TREND                                                  │   │
│  │  $15 ─┬─────────────────────────────────────────────────────────────     │   │
│  │       │  ╭╮         ╭╮         ╭╮         ╭╮                              │   │
│  │  $10 ─┼──╯╰─────────╯╰─────────╯╰─────────╯╰──────────────────────────    │   │
│  │       │                                                                  │   │
│  │   $0 ─┴──────────────────────────────────────────────────────────────    │   │
│  │       1   5   10   15   20   25   30                                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  Note: Spikes on Mondays = Voice-preference farmers listening to action plans   │
│                                                                                  │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  COST BY CALL TYPE              │  │  COST BY LANGUAGE                    │   │
│  │  Action Plan Listen: 70%        │  │  Swahili: 65%                        │   │
│  │  Alert Callbacks: 20%           │  │  Kikuyu: 20%                         │   │
│  │  Support Calls: 10%             │  │  Luo: 10%                            │   │
│  │                                 │  │  English: 5%                         │   │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                                  │
│  VOICE BY INTERACTION PREFERENCE                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Preference         │ Farmers   │ Calls    │ Minutes   │ Cost (30d)     │   │
│  │  ──────────────────-┼───────────┼──────────┼───────────┼────────────────│   │
│  │  Voice-Preferred    │ 234       │ 1,890    │ 2,268     │ $226.80        │   │
│  │  Text-Preferred     │ 89        │ 320      │ 384       │ $38.40         │   │
│  │  Callbacks          │ 45        │ 163      │ 196       │ $19.60         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Budget Alert Configuration Modal

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚙ BUDGET ALERT CONFIGURATION                                             [X]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  TOTAL PLATFORM BUDGET                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Monthly Budget: [$4,000.00    ]                                         │   │
│  │  Warning at:     [80]% ($3,200)    ☑ Email alert                         │   │
│  │  Critical at:    [100]% ($4,000)   ☑ Email alert                         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  SERVICE-SPECIFIC BUDGETS                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Service          │ Budget    │ Warning % │ Critical % │ Alerts          │   │
│  │  ─────────────────┼───────────┼───────────┼────────────┼─────────────────│   │
│  │  LLM              │ $1,500    │ 80%       │ 100%       │ ☑ Email         │   │
│  │  SMS              │ $800      │ 80%       │ 100%       │ ☑ Email         │   │
│  │  Voice IVR        │ $400      │ 80%       │ 100%       │ ☑ Email         │   │
│  │  Weather API      │ $200      │ 80%       │ 100%       │ ☐ Email         │   │
│  │  Storage          │ $400      │ 90%       │ 100%       │ ☐ Email         │   │
│  │  Compute          │ $500      │ 90%       │ 100%       │ ☐ Email         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ALERT RECIPIENTS                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  admin@farmerpower.io                                            [X]     │   │
│  │  finance@farmerpower.io                                          [X]     │   │
│  │  [+ Add recipient email]                                                 │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│                                                 {Cancel}  {Save Configuration}   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Technical Notes
- Consumes gRPC `UnifiedCostService` API from platform-cost service (Epic 13)
- Cost aggregation spans: LLM (OpenRouter), SMS (Africa's Talking), Voice (Africa's Talking), Weather API, Storage (MongoDB/MinIO), Compute (K8s metrics), External APIs (Google Elevation)
- BFF caches cost summary responses for 5 minutes
- Detail views fetched on-demand (no pre-caching)
- Budget alerts stored in MongoDB, processed by scheduled job

### Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Epic 13: Unified Platform Cost Service (must support all service cost endpoints)

### Story Points: 8

---

## Epic Summary

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| 9.1 | Platform Admin Application Scaffold | 5 | P0 |
| 9.2 | Region Management | 5 | P0 |
| 9.3 | Factory Management | 5 | P0 |
| 9.4 | Collection Point Management | 5 | P0 |
| 9.5 | Farmer Management | 8 | P0 |
| 9.6 | Grading Model Management | 5 | P1 |
| 9.7 | User Management Dashboard | 5 | P1 |
| 9.8 | Platform Health Dashboard | 5 | P2 |
| 9.9 | Knowledge Management Interface | 8 | P2 |
| 9.10 | Platform Cost Dashboard | 8 | P2 |

**Total Story Points:** 59

**Pilot-Critical Stories (P0):** 9.1-9.5 = 28 points
**Important Stories (P1):** 9.6-9.7 = 10 points
**Nice-to-Have Stories (P2):** 9.8-9.10 = 21 points

---

## Navigation Flow Summary (Option C: Hybrid)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          TOP-LEVEL SCREENS (Independent)                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  🌍 REGIONS (List)                                                              │
│       │                                                                          │
│       └──→ 🌍 REGION DETAIL ────────────────────────────────────────────────── │
│                 • Region info (edit)                                             │
│                 • Flush calendar, agronomic factors                              │
│                 • Weather config                                                 │
│                 • Summary: factories count, farmers count (read-only)            │
│                 • [View Factories →] [View Farmers →] (filtered links)          │
│                                                                                  │
│  👨‍🌾 FARMERS (List with powerful filtering)                                     │
│       │  Filter by: Region, Factory, Collection Point, Status                    │
│       │  Search by: Name, Phone, Farmer ID                                       │
│       │                                                                          │
│       └──→ 👨‍🌾 FARMER DETAIL ───────────────────────────────────────────────── │
│                 • Personal info (edit)                                           │
│                 • Farm details (location, size) - Region auto-assigned           │
│                 • Primary CP (editable dropdown)                                 │
│                 • Communication prefs (edit)                                     │
│                 • Performance summary (read-only)                                │
│                 • Delivery history (read-only)                                   │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                          HIERARCHICAL SCREENS (Factory → CP)                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  🏭 FACTORIES (List)                                                            │
│       │  Filter by: Region, Status                                               │
│       │                                                                          │
│       └──→ 🏭 FACTORY DETAIL ───────────────────────────────────────────────── │
│                 │  • Factory info (edit)                                         │
│                 │  • Quality thresholds (edit)                                   │
│                 │  • Payment policy (edit)                                       │
│                 │  • Collection Points list (drill-down)                         │
│                 │                                                                │
│                 └──→ 📍 COLLECTION POINT DETAIL ──────────────────────────────  │
│                           • CP info (edit)                                       │
│                           • Clerk assignment (edit)                              │
│                           • Operating hours, capacity (edit)                     │
│                           • Summary: farmers count (read-only)                   │
│                           • [View Farmers →] (filtered link)                    │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                          STANDALONE SCREENS                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  📊 GRADING MODELS (List → Detail → Edit/Create)                                │
│  👤 USERS (List → Detail/Edit → Create)                                         │
│  📈 HEALTH (Dashboard with map)                                                 │
│  📚 KNOWLEDGE (Library → Upload → Review)                                       │
│  💰 COSTS (Dashboard with charts)                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Design Decision:** Farmers are NOT in the hierarchy because:
1. A farmer's **region** is based on their farm GPS, not the factory they deliver to
2. A farmer can **deliver to multiple CPs** at different factories
3. The **primary CP** is just registration convenience, not ownership

---

## Interaction Patterns

### 1. Inline Editing Pattern

All detail screens support inline editing:
- **View Mode:** Read-only display with [Edit] button
- **Edit Mode:** Fields become editable, [Save] [Cancel] buttons appear
- **Validation:** Real-time validation with error messages
- **Auto-save:** Optional draft saving for complex forms

### 2. Navigation Patterns

**Top-level screens (Regions, Farmers):**
```
🌍 Regions › Nyeri Highland
👨‍🌾 Farmers › Wanjiku Muthoni (WM-0041)
```

**Hierarchical screens (Factories → CPs):**
```
🏭 Factories › Nyeri Tea Factory › Nyeri Central CP
```

Cross-linking: [View Farmers →] on Region/CP opens Farmers list pre-filtered.

### 3. List-to-Detail Pattern

All lists follow consistent pattern:
- Search bar (top)
- Filters (below search)
- Data table/cards (main area)
- Pagination (bottom)
- Click row → navigate to detail

### 4. Create Flow Pattern

All create actions:
- [+ Add {Entity}] button in list or parent detail
- Modal or full-page form
- Required fields marked with *
- [Create] [Cancel] actions
- Success → redirect to new entity detail

### 5. Status Indicator Pattern

Consistent status display:
- ● Active (green)
- ○ Inactive (gray)
- ◐ Seasonal (yellow) - for Collection Points only

### 6. Performance Indicator Pattern

Quality percentages use tier colors:
- 🟢 ≥85% (Premium)
- 🟡 ≥70% (Standard)
- 🟠 ≥50% (Acceptable)
- 🔴 <50% (Below Standard)
