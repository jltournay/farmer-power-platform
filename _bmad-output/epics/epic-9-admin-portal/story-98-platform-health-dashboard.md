# Story 9.8: Platform Health Dashboard

As a **Platform Administrator**,
I want to see platform-wide health metrics and factory statistics,
So that I can monitor operations and identify issues.

## Acceptance Criteria

**AC 9.8.1: Dashboard Overview**

**Given** I navigate to `/health`
**When** the page loads
**Then** I see:

- Total factories, total farmers
- System health indicators: service latency, delivery success rates
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

## Wireframe: Platform Health

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📈 PLATFORM HEALTH                                          [🔄 Refresh]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PLATFORM OVERVIEW                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                                     │
│  │  🏭 12           │  │  👨‍🌾 1,247        │                                     │
│  │  Active Factories│  │  Total Farmers   │                                     │
│  └──────────────────┘  └──────────────────┘                                     │
│                                                                                  │
│  SYSTEM HEALTH                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  SERVICES                         │  EXTERNAL & MCP                       │  │
│  │  API Gateway    ✅ 45ms avg       │  SMS Gateway     ✅ 99.2% delivered   │  │
│  │  Plantation Svc ✅ 32ms avg       │  Voice IVR       ✅ Operational       │  │
│  │  Collection Svc ✅ 28ms avg       │  Plantation MCP  ✅ 12ms avg          │  │
│  │  AI Model Svc   ✅ 1.2s avg       │  Collection MCP  ✅ 15ms avg          │  │
│  │  Platform Cost  ✅ Operational    │  Knowledge MCP   ✅ 18ms avg          │  │
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

## Technical Notes
- Aggregated metrics from OpenTelemetry
- Health checks from each service
- **Factory Map Display**: See [ADR-017: Map Services](architecture/adr/ADR-017-map-services-gps-region-assignment.md)
  - **Component**: Use `<MapDisplay>` from ADR-017 Section 4.2
  - Display factory markers with status-based colors (healthy/warning/critical)
  - Leaflet.js + OpenStreetMap tiles (zero cost)

## Dependencies
- Story 9.1: Platform Admin Application Scaffold
- Story 0.5.6: BFF Service Setup
- ADR-017: Map Services and GPS-Based Region Assignment

## Story Points: 5

## Human Validation Gate

**⚠️ MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
| --------------- | ----------- |
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | Platform overview metrics, system health indicators, factory map display, alert banners |
| **Approval** | Story cannot be marked "done" until human signs off |

---
