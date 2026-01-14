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
│  FARMERS are independent entities                                           │
│  - Have a PRIMARY collection point (for registration)                       │
│  - Can DELIVER to ANY collection point (tracked in deliveries)              │
│  - Region based on FARM GPS, not factory location                           │
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
