# Plantation Model Architecture

## Overview

The Plantation Model is the **master data registry** for the Farmer Power Cloud Platform. It stores core entities (regions, farmers, factories), configuration (payment policies, grading model references), and pre-computed performance summaries.

**Core Responsibility:** Manage master data, store configuration, provide pre-computed summaries.

**Does NOT:** Collect raw data, perform analysis, or generate action plans.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PLANTATION MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STATIC DATA (via Admin UI):                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐         │
│  │   REGION    │  │   FARMER    │  │   FACTORY               │         │
│  │             │  │             │  │                         │         │
│  │ • region_id │  │ • farmer_id │  │ • factory_id            │         │
│  │ • name      │  │ • name      │  │ • name                  │         │
│  │ • county    │  │ • phone     │  │ • location              │         │
│  │ • country   │  │ • national_id│ │ • payment_policy        │         │
│  │             │  │ • gps_coords│  │                         │         │
│  │ GEOGRAPHY:  │  │ • altitude  │  │                         │         │
│  │ • center_gps│  │   (Google   │  │                         │         │
│  │ • radius_km │  │    Elevation│  │                         │         │
│  │ • altitude  │  │    API)     │  │                         │         │
│  │   _band     │  │ • farm_size │  │                         │         │
│  │   (min/max) │  │ • region_id │◀─┼── assigned by altitude  │         │
│  │             │  │ • factory_id│  │                         │         │
│  │ FLUSH       │  │             │  │                         │         │
│  │ CALENDAR:   │  │ COMMUNICATION:│ │                         │         │
│  │ • first     │  │ • pref_channel│ │                         │         │
│  │   _flush    │  │   (SMS/Voice/ │ │                         │         │
│  │ • monsoon   │  │    WhatsApp)  │ │                         │         │
│  │   _flush    │  │ • pref_lang   │ │                         │         │
│  │ • autumn    │  │ • literacy_lvl│ │                         │         │
│  │   _flush    │  │             │  │                         │         │
│  │ • dormant   │  └─────────────┘  │                         │         │
│  │             │                   │                         │         │
│  │ AGRONOMIC:  │  ┌─────────────────────────────────────────┐│         │
│  │ • soil_type │  │  GRADING MODEL REF                      ││         │
│  │ • typical   │  │  • model_id, version                    ││         │
│  │   _diseases │  │  • active_at_factory[]                  ││         │
│  │ • weather   │  │  (Definition in farmer-power-training)  ││         │
│  │   _api_loc  │  └─────────────────────────────────────────┘│         │
│  └─────────────┘                                             │         │
│                                                                         │
│  COMPUTED DATA (via Scheduler - daily batch):                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐      │
│  │  FARMER PERFORMANCE         │  │  FACTORY PERFORMANCE        │      │
│  │                             │  │                             │      │
│  │  • avg_grade (30/90/yr)     │  │  • intake_quality_avg       │      │
│  │  • delivery_count           │  │  • farmer_improvement_rate  │      │
│  │  • improvement_trend        │  │  • rejection_rate           │      │
│  │  • last_delivery            │  │  • premium_percentage       │      │
│  └─────────────────────────────┘  └─────────────────────────────┘      │
│                                                                         │
│  EXTERNAL DATA (via Market Analysis Model):                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  BUYER PROFILES                                                  │   │
│  │  • buyer_id, preferences, quality_requirements                   │   │
│  │  • Created/updated by Market Analysis Model                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         APIs + MCP                                │  │
│  │  REST API (Admin UI)  │  Internal API (Services)  │  MCP Server  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Region Entity

The Region entity enables efficient weather collection and seasonal context management by grouping farms with similar agronomic conditions.

**Key Design Decision:** Regions are defined by **county + altitude band**, not just geographic proximity. Two farms 5 km apart at the same altitude have similar weather; two farms 500m apart with 400m altitude difference have significantly different conditions.

```yaml
# Region Entity Schema
region:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  region_id: "nyeri-highland"           # Pattern: {county}-{altitude_band}
  name: "Nyeri Highland"
  county: "Nyeri"
  country: "Kenya"

  # ═══════════════════════════════════════════════════════════════════
  # GEOGRAPHY
  # ═══════════════════════════════════════════════════════════════════
  geography:
    center_gps:
      lat: -0.4197
      lng: 36.9553
    radius_km: 25                       # Approximate coverage
    altitude_band:
      min_meters: 1800
      max_meters: 2200
      label: "highland"                 # highland | midland | lowland

  # ═══════════════════════════════════════════════════════════════════
  # FLUSH CALENDAR (Tea Seasons)
  # ═══════════════════════════════════════════════════════════════════
  flush_calendar:
    first_flush:
      start: "03-15"
      end: "05-15"
      characteristics: "Highest quality, delicate flavor"
    monsoon_flush:
      start: "06-15"
      end: "09-30"
      characteristics: "High volume, robust flavor"
    autumn_flush:
      start: "10-15"
      end: "12-15"
      characteristics: "Balanced quality"
    dormant:
      start: "12-16"
      end: "03-14"
      characteristics: "Minimal growth"

  # ═══════════════════════════════════════════════════════════════════
  # AGRONOMIC FACTORS
  # ═══════════════════════════════════════════════════════════════════
  agronomic:
    soil_type: "volcanic_red"
    typical_diseases:
      - "blister_blight"
      - "grey_blight"
      - "red_rust"
    harvest_peak_hours: "06:00-10:00"
    frost_risk: true                    # Highland regions

  # ═══════════════════════════════════════════════════════════════════
  # WEATHER CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  weather_config:
    api_location:
      lat: -0.4197
      lng: 36.9553
    altitude_for_api: 1950              # Representative altitude
    collection_time: "06:00"            # Daily weather fetch time
```

**Altitude Band Definitions (Kenya Tea Regions):**

| Altitude Band | Elevation Range | Characteristics |
|---------------|-----------------|-----------------|
| **Highland** | 1800m+ | Cooler, more rainfall, later flushes, frost risk |
| **Midland** | 1400m - 1800m | Moderate conditions, typical patterns |
| **Lowland** | Below 1400m | Warmer, earlier flushes, different disease profile |

**Farm-to-Region Assignment:**

When a farmer is registered, their GPS coordinates and altitude (via Google Elevation API) determine their region:

```python
def assign_farm_to_region(farm_gps: GPS, farm_altitude: int) -> str:
    """
    Assigns a farm to the appropriate region based on location and altitude.
    Returns region_id in format: {county}-{altitude_band}
    """
    county = geocode_to_county(farm_gps)  # e.g., "nyeri"

    if farm_altitude >= 1800:
        band = "highland"
    elif farm_altitude >= 1400:
        band = "midland"
    else:
        band = "lowland"

    return f"{county}-{band}"  # e.g., "nyeri-highland"
```

**Weather Collection Optimization:**

| Approach | API Calls/Day | Annual Cost (at $0.001/call) |
|----------|---------------|------------------------------|
| Per Farm (800,000 farms) | 800,000 | ~$292,000 |
| Per Region (~50 regions) | 50 | ~$18 |

## Data Ownership

| Entity | Writer | Mechanism | Frequency |
|--------|--------|-----------|-----------|
| Region | Admin UI | REST API (manual) | On region setup |
| Farmer | Admin UI | REST API (manual) | On registration/update |
| Factory | Admin UI | REST API (manual) | On setup/config change |
| Grading Model Ref | Admin UI | REST API (manual) | On model deployment |
| Farmer Performance | Scheduler | Batch job (automated) | Daily |
| Factory Performance | Scheduler | Batch job (automated) | Daily |
| Regional Weather | Collection Model | Scheduled job | Daily per region |
| Buyer Profiles | Market Analysis Model | Internal API (automated) | On market analysis |

## Farmer Power Ecosystem Context

The Plantation Model references grading models but does NOT store their definitions:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FARMER POWER ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  CLOUD PLATFORM │  │  QC ANALYZER    │  │  CV TRAINING    │         │
│  │  (this project) │  │  (edge device)  │  │  (ML pipeline)  │         │
│  │                 │  │                 │  │                 │         │
│  │  Plantation     │  │  Uses grading   │  │  Defines grading│         │
│  │  stores REF to  │  │  model for      │  │  model (weights,│         │
│  │  grading model  │  │  inference      │  │  thresholds)    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  github.com/farmerpower-ai/farmer-power-platform                        │
│  github.com/farmerpower-ai/farmer-power-qc-analyzer                     │
│  github.com/farmerpower-ai/farmer-power-training                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Performance Summary Computation (Hybrid Approach)

The system uses a **hybrid approach** combining batch processing for historical aggregates with real-time streaming for same-day visibility.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID PERFORMANCE SUMMARIES                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  BATCH JOB (Daily 2 AM via Dapr Jobs)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Source: Collection Model (raw quality events)                   │   │
│  │                                                                  │   │
│  │  Computes historical aggregates:                                 │   │
│  │  • avg_grade_30d, avg_grade_90d, avg_grade_year                 │   │
│  │  • delivery_count_30d, delivery_count_90d                       │   │
│  │  • improvement_trend (stable, improving, declining)             │   │
│  │  • computed_at: timestamp                                        │   │
│  │                                                                  │   │
│  │  Updates: Plantation Model (farmer_performance, factory_performance)│
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  STREAMING (Real-time via Dapr Pub/Sub)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Event: collection.document_stored                               │   │
│  │                                                                  │   │
│  │  Updates "today" counters (per farmer):                          │   │
│  │  • today_deliveries: number                                      │   │
│  │  • today_grades: object (dynamic, keyed by Grading Model labels) │   │
│  │    Example A/B/C/D model: { "A": 2, "B": 1, "C": 0, "D": 0 }     │   │
│  │    Example ternary model: { "premium": 3, "standard": 2, "rejected": 0 } │
│  │  • today_avg_score: number (0.0-1.0, normalized)                 │   │
│  │  • last_delivery: timestamp                                      │   │
│  │                                                                  │   │
│  │  Note: Grade labels are dynamic - fetched from factory's Grading Model │
│  │  Behavior: Resets at midnight (batch job incorporates into history) │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Farmer Performance Schema:**

```yaml
# MongoDB: farmer_performance (embedded in farmer document or separate collection)
farmer_performance:
  farmer_id: string

  # Historical (updated by batch job)
  historical:
    avg_grade_30d: number
    avg_grade_90d: number
    avg_grade_year: number
    delivery_count_30d: number
    delivery_count_90d: number
    improvement_trend: enum      # "improving" | "stable" | "declining"
    computed_at: datetime        # When batch job ran

  # Today (updated by streaming)
  today:
    deliveries: number
    grades: object               # Dynamic map keyed by Grading Model labels
                                 # Example A/B/C/D: { "A": 2, "B": 1, "C": 0, "D": 0 }
                                 # Example ternary: { "premium": 3, "standard": 2, "rejected": 0 }
    avg_score: number            # Normalized 0.0-1.0 (not grade label)
    last_delivery: datetime
    date: date                   # Resets when date changes
    grading_model_id: string     # Reference to Grading Model for label lookup
```

**Dashboard Display Example:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Farmer WM-4521 Performance                                              │
│  ─────────────────────────────────────────────────────────────────────   │
│                                                                          │
│  TODAY: 3 deliveries (A, A, B) - avg: A-        Last: 8:15 AM           │
│                                                                          │
│  HISTORICAL (as of Dec 16, 2:00 AM):                                     │
│  • 30-day avg: B+        • 90-day avg: B        • Year avg: B-          │
│  • Trend: Improving ↑    • Total deliveries (30d): 12                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Real-time visibility into same-day activity
- Clear "as of" timestamps prevent confusion
- Historical trends remain accurate (complex aggregations done in batch)
- Minimal additional complexity (reuses existing Dapr pub/sub)

## API Structure

### Admin UI Endpoints (authenticated, role-based)

```
# Region Management
POST   /api/v1/regions              # Create region
GET    /api/v1/regions              # List regions (filter: county, altitude_band)
GET    /api/v1/regions/{id}         # Get region details
PUT    /api/v1/regions/{id}         # Update region (flush calendar, agronomic)
DELETE /api/v1/regions/{id}         # Deactivate region (soft delete)

# Farmer Management
POST   /api/v1/farmers              # Create farmer (auto-assigns region)
GET    /api/v1/farmers/{id}         # Get farmer
PUT    /api/v1/farmers/{id}         # Update farmer
DELETE /api/v1/farmers/{id}         # Deactivate farmer

# Factory Management
POST   /api/v1/factories            # Create factory
GET    /api/v1/factories/{id}       # Get factory
PUT    /api/v1/factories/{id}       # Update factory config
```

### Internal Endpoints (service-to-service)

```
PUT    /api/v1/internal/farmer-summary/{id}     # Scheduler writes
PUT    /api/v1/internal/factory-summary/{id}    # Scheduler writes
PUT    /api/v1/internal/buyer-profiles/{id}     # Market Analysis writes
```

## MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer` | Farmer profile | `farmer_id` |
| `get_farmer_summary` | Performance summary | `farmer_id`, `period?` |
| `get_factory` | Factory details + payment_policy | `factory_id` |
| `get_factory_config` | Grading model ref, thresholds | `factory_id` |
| `get_buyer_profiles` | Market preferences | `region?`, `factory_id?` |
| `get_farmer_context` | Combined view (convenience) | `farmer_id` |
| `get_region` | Region details + flush calendar | `region_id` |
| `get_region_weather` | Weather data for region (7-day history) | `region_id`, `days?` |
| `get_current_flush` | Current flush period for a region | `region_id` |
| `list_regions` | All regions with summary | `county?`, `altitude_band?` |

**Primary Consumer:** Action Plan Model queries via MCP for complete farmer context when generating recommendations.

**Weather Analyzer:** Uses `get_region`, `get_region_weather`, and `get_current_flush` to correlate weather events with quality issues using the 7-day lookback pattern.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Master data + summaries | Single source of truth for entities |
| **Performance Summaries** | Pre-computed (daily batch) | Fast access, no real-time computation |
| **Grading Model** | Reference only | Definition in separate training project |
| **Buyer Profiles** | Stored here, written by Market Analysis | Centralized profile storage |
| **MCP Server** | Yes | AI agents need rich farmer/factory context |
| **Data Ownership** | Clear per-entity | Admin UI, Scheduler, Market Analysis |

## Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Admin API** | Input validation, authorization, audit trail |
| **Scheduler Job** | Reliability, computation accuracy, idempotency |
| **Market Analysis Integration** | API contract, data integrity |
| **MCP Tools** | Correct data retrieval, access control |
| **Performance Summaries** | Aggregation accuracy vs. raw data |

---
