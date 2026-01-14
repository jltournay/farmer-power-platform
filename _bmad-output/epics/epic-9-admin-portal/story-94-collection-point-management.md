# Story 9.4: Collection Point Management

As a **Platform Administrator**,
I want to view, create, edit, and manage collection points within a factory,
So that I can set up farmer registration and delivery locations for the pilot.

## Acceptance Criteria

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

## Wireframe: Collection Point Detail (Child of Factory)

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

## Wireframe: Collection Point Edit Mode

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
│  │                                                    [📍 Select on Map]     │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │  │
│  │  │  🗺️ (Collapsible map - click to set location, syncs with fields)   │  │  │
│  │  │  Tip: Click on map OR type coordinates manually above              │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘  │  │
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

## Technical Notes
- BFF endpoints: `GET/POST /api/admin/collection-points`, `GET/PUT /api/admin/collection-points/:id`
- Backend: Plantation Service gRPC `ListCollectionPoints`, `CreateCollectionPoint`, `UpdateCollectionPoint`
- Collection Point ID auto-generated from region: `{region_id}-cp-{sequence}`
- Farmer list includes 30-day primary percentage from aggregated performance data
- **CP Location Capture**: See [ADR-017: Map Services](architecture/adr/ADR-017-map-services-gps-region-assignment.md)
  - **Component**: Use `<GPSFieldWithMapAssist>` from ADR-017 Section 4.3b
  - Map assist is optional (collapsible) - users can type coordinates manually OR click on map
  - Two-way sync: clicking map updates text fields, editing text fields updates marker

## Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 9.3: Factory Management
- Story 1.2: Factory and Collection Point Management (Plantation Service)
- ADR-017: Map Services and GPS-Based Region Assignment

## Story Points: 5

## Human Validation Gate

**⚠️ MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
| --------------- | ----------- |
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | CP detail view, edit form, farmer summary, map location picker |
| **Approval** | Story cannot be marked "done" until human signs off |

---
