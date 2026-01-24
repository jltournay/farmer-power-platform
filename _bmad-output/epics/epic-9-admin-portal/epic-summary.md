# Epic Summary

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| 9.1a | Platform Admin Application Scaffold | 5 | P0 |
| 9.1b | Shared Admin UI Components | 8 | P0 |
| 9.1c | Admin Portal BFF Endpoints | 8 | P0 |
| 9.2 | Region Management | 5 | P0 |
| 9.3 | Factory Management | 5 | P0 |
| 9.4 | Collection Point Management | 5 | P0 |
| 9.5 | Farmer Management | 8 | P0 |
| 9.6a | Grading Model gRPC + BFF API (ListGradingModels, GetGradingModel, Assign) | 5 | P1 |
| 9.6b | Grading Model Management UI (Read-Only + Assignment) | 3 | P1 |
| 9.7 | User Management Dashboard | 5 | Deferred (blocked by 0.5.8) |
| 9.8 | Platform Health Dashboard | 5 | P2 |
| 9.9a | Knowledge Management BFF REST API | 3 | P2 |
| 9.9b | Knowledge Management UI | 5 | P2 |
| 9.10a | Platform Cost BFF REST API | 3 | P2 |
| 9.10b | Platform Cost Dashboard UI | 3 | P2 |
| 9.11a | SourceConfigService gRPC in Collection Model | 3 | P2 |
| 9.11b | Source Config gRPC Client + REST API in BFF | 3 | P2 |
| 9.11c | Source Configuration Viewer UI | 3 | P2 |
| 9.12a | AgentConfigService gRPC in AI Model | 5 | P2 |
| 9.12b | Agent Config gRPC Client + REST API in BFF | 3 | P2 |
| 9.12c | AI Agent & Prompt Viewer UI | 5 | P2 |

**Use Cases:** [UC9.0-UC9.3](./use-cases.md)

**Total Story Points:** 98

**Pilot-Critical Stories (P0):** 9.1a-9.5 = 44 points
**Important Stories (P1):** 9.6a-9.6b = 8 points
**Nice-to-Have Stories (P2):** 9.8-9.12c = 41 points (includes ADR-019 config visibility)
**Deferred Stories:** 9.7 = 5 points (blocked by 0.5.8 Azure AD B2C)

---

## Story 9.1b: Shared Admin UI Components

**As a** platform developer,
**I want** a library of reusable UI components for the Admin Portal,
**So that** all Epic 9 screens are built consistently and efficiently.

### Components to Build (14 total)

| Category | Components | Est. Points |
|----------|------------|-------------|
| **Shell** | `AdminShell`, `Sidebar`, `Breadcrumb`, `PageHeader` | 2 |
| **Data Display** | `DataTable`, `EntityCard`, `FilterBar`, `MetricCard` | 2 |
| **Forms** | `InlineEditForm`, `ConfirmationDialog`, `FileDropzone` | 2 |
| **Maps** | `MapDisplay`, `GPSFieldWithMapAssist`, `BoundaryDrawer` | 2 |

### Dependencies
- Story 9.1a: Platform Admin Application Scaffold
- Story 1.10: GPS-Based Region Assignment (for map component contracts)
- ADR-017: Map Services and GPS-Based Region Assignment

---
