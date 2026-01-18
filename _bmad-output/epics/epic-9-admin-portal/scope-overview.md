# Scope Overview

## Data Model Relationships (Important!)

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
│  FARMERS are independent entities (N:M with Collection Points)              │
│  - Farmer creation does NOT require a collection point                      │
│  - Factories ASSIGN farmers to their collection points                      │
│  - Same farmer can be assigned to CPs from DIFFERENT factories              │
│  - Assignment is: manual (admin UI) OR automatic (on quality result)        │
│  - Region based on FARM GPS, not factory location                           │
│                                                                             │
│  Relationship ownership:                                                    │
│    CollectionPoint.farmer_ids[] → list of assigned farmer IDs               │
│    (NOT Farmer.collection_point_id - this is REMOVED)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Navigation Model: Option C (Hybrid)

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
