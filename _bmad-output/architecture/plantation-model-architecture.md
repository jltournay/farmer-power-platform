    # Plantation Model Architecture

## Overview

The Plantation Model is the **master data registry** for the Farmer Power Cloud Platform. It stores core entities (regions, farmers, factories), configuration (payment policies, grading models), and pre-computed performance summaries.

**Core Responsibility:** Manage master data, store grading model definitions, provide pre-computed summaries.

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
│  │ • center_gps│  │   (Google   │  │  ┌─────────────────┐    │         │
│  │ • radius_km │  │    Elevation│  │  │ COLLECTION      │    │         │
│  │ • altitude  │  │    API)     │  │  │ POINT           │    │         │
│  │   _band     │  │ • farm_size │  │  │                 │    │         │
│  │   (min/max) │  │ • region_id │  │  │ • cp_id         │    │         │
│  │             │  │             │  │  │ • name          │    │         │
│  │ FLUSH       │  │ COMMUNICATION:│ │  │ • gps_coords    │    │         │
│  │ CALENDAR:   │  │ • pref_channel│ │  │ • factory_id    │────┘         │
│  │ • first     │  │   (SMS/Voice/ │ │  │ • clerk_id      │              │
│  │   _flush    │  │    WhatsApp)  │ │  │ • operating_hrs │              │
│  │ • monsoon   │  │ • pref_lang   │ │  └─────────────────┘              │
│  │   _flush    │  │ • literacy_lvl│ │                                   │
│  │ • autumn    │  │             │  │  Note: Farmer delivers to         │
│  │   _flush    │  └─────────────┘  │  Collection Points (many-to-many) │
│  │ • dormant   │        │          │  tracked in Collection Model      │
│  │             │        │          └─────────────────────────┘         │
│  │ AGRONOMIC:  │        │                                              │
│  │ • soil_type │        └── assigned by altitude                       │
│  │ • typical   │                                                       │
│  │   _diseases │  ┌─────────────────────────────────────────┐          │
│  │ • weather   │  │  GRADING MODEL (Full Definition)        │          │
│  │   _api_loc  │  │  • model_id, version, grading_type      │          │
│  └─────────────┘  │  • attributes: {name: {classes: [...]}} │          │
│                   │  • grade_rules: reject_conditions, etc  │          │
│                   │  • grade_labels: {internal: display}    │          │
│                   │  • active_at_factory[]                  │          │
│                   └─────────────────────────────────────────┘          │
│                                                                         │
│  COMPUTED DATA (via Scheduler - daily batch):                           │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────┐│
│  │ FARMER PERFORMANCE   │ │ FACTORY PERFORMANCE  │ │ CP PERFORMANCE   ││
│  │                      │ │                      │ │                  ││
│  │ • avg_grade (30/90/yr│ │ • intake_quality_avg │ │ • daily_volume   ││
│  │ • delivery_count     │ │ • farmer_improvement │ │ • quality_avg    ││
│  │ • improvement_trend  │ │ • rejection_rate     │ │ • farmer_count   ││
│  │ • yield_per_hectare  │ │ • premium_percentage │ │ • peak_hours     ││
│  └──────────────────────┘ └──────────────────────┘ └──────────────────┘│
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

## Entity Relationships

```
┌──────────┐         ┌───────────────────┐         ┌──────────┐
│  FARMER  │         │  COLLECTION POINT │         │ FACTORY  │
│          │ delivers│                   │ belongs │          │
│          │────────▶│  (where clerk     │────────▶│          │
│          │ (many)  │   collects bags)  │  (one)  │          │
└──────────┘         └───────────────────┘         └──────────┘
     │                        │
     │                        │ Delivery records in
     │                        │ Collection Model track:
     │                        │ • farmer_id
     │                        │ • collection_point_id
     │                        │ • timestamp, weight, grade
     │
     └── A farmer can deliver to MULTIPLE collection points
         (even from different factories)
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

## Collection Point Entity

A Collection Point is a **physical location where a factory clerk collects tea bags from farmers**. It's the intermediary between farmers and factories.

**Key Design Decision:** Farmers do NOT have a direct `factory_id`. Instead, the farmer-to-factory relationship is established through deliveries at collection points. A farmer can deliver to multiple collection points (even from different factories).

```yaml
# Collection Point Entity Schema
collection_point:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  cp_id: "nyeri-cp-001"              # Unique identifier
  name: "Nyeri Central Collection"
  factory_id: "factory-nyeri-main"   # Parent factory (one factory, many CPs)

  # ═══════════════════════════════════════════════════════════════════
  # LOCATION
  # ═══════════════════════════════════════════════════════════════════
  location:
    gps:
      lat: -0.4232
      lng: 36.9587
    address: "Near Nyeri Town Market"
    region_id: "nyeri-highland"      # For regional context

  # ═══════════════════════════════════════════════════════════════════
  # OPERATIONS
  # ═══════════════════════════════════════════════════════════════════
  operations:
    clerk_id: "clerk-wanjiku-001"    # Assigned clerk (reference to User)
    clerk_phone: "+254..."           # For farmer contact
    operating_hours:
      weekdays: "06:00-10:00"        # Morning collection
      weekends: "07:00-09:00"
    collection_days: ["mon", "wed", "fri", "sat"]  # Not every day

  # ═══════════════════════════════════════════════════════════════════
  # CAPACITY
  # ═══════════════════════════════════════════════════════════════════
  capacity:
    max_daily_kg: 5000               # Maximum daily intake
    storage_type: "covered_shed"     # covered_shed | open_air | refrigerated
    has_weighing_scale: true
    has_qc_device: true              # QC Analyzer present?

  # ═══════════════════════════════════════════════════════════════════
  # STATUS
  # ═══════════════════════════════════════════════════════════════════
  status: "active"                   # active | inactive | seasonal
  created_at: datetime
  updated_at: datetime
```

**Collection Point Performance (Computed Daily):**

```yaml
# MongoDB: collection_point_performance
cp_performance:
  cp_id: string

  # Volume metrics
  daily_volume_kg: number            # Today's total intake
  avg_daily_volume_30d: number       # 30-day average
  peak_hour: string                  # "07:00-08:00" - busiest hour

  # Quality metrics
  quality_avg_30d: number            # Average grade score
  rejection_rate_30d: number         # % rejected deliveries

  # Farmer metrics
  active_farmers_30d: number         # Unique farmers who delivered
  new_farmers_30d: number            # First-time deliverers

  computed_at: datetime
```

**Why Collection Points Matter:**

| Use Case | How Collection Point Helps |
|----------|---------------------------|
| **Logistics** | Know where to send trucks, plan routes |
| **Quality tracking** | Identify if quality issues are location-specific (e.g., storage problem at one CP) |
| **Clerk accountability** | Track performance by clerk assignment |
| **Farmer convenience** | Farmers can see nearby collection points and their hours |
| **Capacity planning** | Prevent overloading a single collection point |

**Farmer → Collection Point Discovery:**

Farmers don't "belong" to a collection point. Instead:
1. Collection Model records which CPs a farmer has delivered to
2. Platform can suggest nearby CPs based on farmer GPS
3. Farmer can deliver to any CP accepting deliveries

```python
def get_farmer_collection_points(farmer_id: str) -> list[CollectionPoint]:
    """
    Returns collection points where this farmer has delivered,
    ordered by frequency (most used first).
    """
    # Query Collection Model for delivery history
    deliveries = collection_model.get_deliveries(farmer_id=farmer_id)

    # Count by CP, return sorted
    cp_counts = Counter(d.collection_point_id for d in deliveries)
    return [get_cp(cp_id) for cp_id, _ in cp_counts.most_common()]

def suggest_nearby_collection_points(farmer_gps: GPS, max_distance_km: float = 10) -> list[CollectionPoint]:
    """
    Returns active collection points within range of farmer,
    useful for new farmers or expanding delivery options.
    """
    return plantation_model.find_cps_near(farmer_gps, max_distance_km, status="active")
```

## Grading Model Entity

The Grading Model is the **complete definition of how quality grades are determined** for a specific crop and market. The Plantation Model stores the full grading model definition (not just a reference) to enable:

- Dynamic UI rendering with correct attribute labels and class values
- Attribute-level performance tracking for root-cause analysis
- Factory-specific grade label display (Primary/Secondary vs Accept/Reject)

**Key Design Decision:** Grading models are fully configurable per regulatory authority and market. The cloud platform stores the complete definition to decouple from the training/inference pipeline and enable rich analytics.

```yaml
# Grading Model Entity Schema
# MongoDB: grading_models
grading_model:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  model_id: "tbk_kenya_tea_v1"            # Unique identifier
  model_version: "1.0.0"                  # Semantic version
  regulatory_authority: "Tea Board of Kenya (TBK)"
  crops_name: "Tea"
  market_name: "Kenya_TBK"
  grading_type: "binary"                  # binary | ternary | multi_level

  # ═══════════════════════════════════════════════════════════════════
  # ATTRIBUTE STRUCTURE
  # Defines what attributes the CV model outputs and their possible values
  # ═══════════════════════════════════════════════════════════════════
  attributes:
    leaf_type:
      num_classes: 7
      classes:
        - "bud"
        - "one_leaf_bud"
        - "two_leaves_bud"
        - "three_plus_leaves_bud"
        - "single_soft_leaf"
        - "coarse_leaf"
        - "banji"
    coarse_subtype:
      num_classes: 4
      classes:
        - "none"
        - "double_luck"
        - "maintenance_leaf"
        - "hard_leaf"
    banji_hardness:
      num_classes: 2
      classes:
        - "soft"
        - "hard"

  # ═══════════════════════════════════════════════════════════════════
  # GRADE CALCULATION RULES
  # Defines how attribute values map to final grades
  # ═══════════════════════════════════════════════════════════════════
  grade_rules:
    # Attribute values that ALWAYS result in rejection
    reject_conditions:
      leaf_type:
        - "three_plus_leaves_bud"
        - "coarse_leaf"

    # Conditional rejection rules
    conditional_reject:
      - if_attribute: "leaf_type"
        if_value: "banji"
        then_attribute: "banji_hardness"
        reject_values: ["hard"]

  # ═══════════════════════════════════════════════════════════════════
  # DISPLAY LABELS
  # Maps internal grade values to factory-specific display labels
  # ═══════════════════════════════════════════════════════════════════
  grade_labels:
    ACCEPT: "Primary"                     # Could be "Grade A", "Premium", etc.
    REJECT: "Secondary"                   # Could be "Grade B", "Standard", etc.

  # ═══════════════════════════════════════════════════════════════════
  # DEPLOYMENT
  # ═══════════════════════════════════════════════════════════════════
  active_at_factory:
    - "factory-nyeri-main"
    - "factory-mombasa-001"

  # ═══════════════════════════════════════════════════════════════════
  # TIMESTAMPS
  # ═══════════════════════════════════════════════════════════════════
  created_at: datetime
  updated_at: datetime
```

**Grading Type Definitions:**

| Grading Type | Final Grades | Example Use Case |
|--------------|--------------|------------------|
| **Binary** | ACCEPT / REJECT | TBK Kenya Tea (Primary/Secondary) |
| **Ternary** | PREMIUM / STANDARD / REJECT | Uganda Coffee |
| **Multi-Level** | A / B / C / D / REJECT | Rwanda Specialty Coffee |

**Why Store Full Definition (Not Just Reference):**

| Need | How Full Definition Helps |
|------|---------------------------|
| **Attribute-level analytics** | Track distribution of `leaf_type`, `banji_hardness` over time |
| **Root-cause analysis** | "Your coarse_leaf count increased from 8% to 15%" |
| **Dynamic UI rendering** | Dropdown options, chart labels from `attributes.classes` |
| **Grade label display** | Show "Primary" vs "ACCEPT" based on factory preference |
| **Offline capability** | QC Analyzer can operate without cloud connection |

**Grading Model → Factory Assignment:**

A factory has exactly ONE active grading model at any time. When the factory's grading model is updated, the `active_at_factory` list is modified and a new version is created (grading models are immutable once deployed).

```python
def get_factory_grading_model(factory_id: str) -> GradingModel:
    """
    Returns the grading model active at the specified factory.
    """
    return grading_model_repo.find_one({"active_at_factory": factory_id})
```

## Data Ownership

| Entity | Writer             | Mechanism | Frequency |
|--------|--------------------|-----------|-----------|
| Region | Admin UI           | REST API (manual) | On region setup |
| Farmer | Admin UI           | REST API (manual) | On registration/update |
| Factory | Admin UI           | REST API (manual) | On setup/config change |
| Collection Point | Admin UI           | REST API (manual) | On CP setup/update |
| Grading Model | Admin UI / Sync    | gRPC API | On model deployment/update |
| Farmer Performance | Scheduler          | Batch job (automated) | Daily |
| Factory Performance | Scheduler          | Batch job (automated) | Daily |
| CP Performance | Scheduler          | Batch job (automated) | Daily |
| Regional Weather | Collection Model   | Scheduled job | Daily per region |
| Buyer Profiles | Market Analysis Model | Internal API (automated) | On market analysis |

## Farmer Power Ecosystem Context

The Plantation Model stores the **complete grading model definition** to enable rich analytics and attribute-level tracking:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FARMER POWER ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  CLOUD PLATFORM │  │  QC ANALYZER    │  │  CV TRAINING    │         │
│  │  (this project) │  │  (edge device)  │  │  (ML pipeline)  │         │
│  │                 │  │                 │  │                 │         │
│  │  Plantation     │  │  Uses grading   │  │  Creates grading│         │
│  │  stores FULL    │◀─│  model for      │◀─│  model (weights,│         │
│  │  grading model  │  │  inference      │  │  thresholds)    │         │
│  │  definition for │  │                 │  │                 │         │
│  │  analytics      │  │  Syncs model    │  │  Exports model  │         │
│  │                 │  │  from cloud     │  │  definition     │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  Grading Model Flow:                                                    │
│  1. Training pipeline creates model with attributes + rules             │
│  2. Model definition synced to Cloud Platform (Plantation Model)        │
│  3. QC Analyzer fetches model from cloud for inference                  │
│  4. Cloud Platform tracks attribute-level performance for analytics     │
│                                                                         │
│  github.com/farmerpower-ai/farmer-power-platform                        │
│  github.com/farmerpower-ai/farmer-power-qc-analyzer                     │
│  github.com/farmerpower-ai/farmer-power-training                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Performance Summary Computation (Hybrid Approach)

> **CQRS Implementation:** This hybrid approach implements the implicit CQRS pattern described in [`cqrs-architecture-pattern.md`](./cqrs-architecture-pattern.md). Raw delivery data is written to the Collection Model (command side), then pre-computed into these summaries for efficient reading (query side). AI agents via MCP never query raw Collection data — they read from these optimized projections.

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
# MongoDB: farmer_performance (separate collection)
farmer_performance:
  farmer_id: string

  # Grading model reference (for interpreting distributions)
  grading_model_id: string       # Reference to grading model definition
  grading_model_version: string  # Semantic version of the grading model

  # Farm context (denormalized for efficient computation)
  farm_size_hectares: number     # Copied from farmer profile for yield calculations
  farm_scale: enum               # "smallholder" (<1ha) | "medium" (1-5ha) | "estate" (>5ha)

  # Historical (updated by batch job)
  historical:
    # Grade-level distributions (enables trend analysis)
    grade_distribution_30d: object   # {"Primary": 120, "Secondary": 30}
    grade_distribution_90d: object
    grade_distribution_year: object

    # Attribute-level distributions (enables root-cause analysis)
    # Structure: {"attribute_name": {"class_name": count, ...}, ...}
    attribute_distributions_30d: object
    # Example: {
    #   "leaf_type": {"bud": 15, "one_leaf_bud": 45, "coarse_leaf": 15, ...},
    #   "coarse_subtype": {"double_luck": 3, "maintenance_leaf": 7, ...},
    #   "banji_hardness": {"soft": 3, "hard": 2}
    # }
    attribute_distributions_90d: object
    attribute_distributions_year: object

    # Derived convenience metrics
    primary_percentage_30d: number   # Computed from grade_distribution
    primary_percentage_90d: number
    primary_percentage_year: number

    # Volume metrics
    total_kg_30d: number
    total_kg_90d: number
    total_kg_year: number

    # Normalized yield metrics
    yield_kg_per_hectare_30d: number    # total_kg_30d / farm_size_hectares
    yield_kg_per_hectare_90d: number
    yield_kg_per_hectare_year: number
    yield_vs_regional_avg: number       # 0.0-2.0 (1.0 = regional average)
    yield_percentile: number            # 0-100 (rank within same farm_scale category)

    improvement_trend: enum      # "improving" | "stable" | "declining"
    computed_at: datetime        # When batch job ran

  # Today (updated by streaming - when Collection Model exists)
  today:
    deliveries: number
    total_kg: number             # Today's total kg delivered
    grade_counts: object         # Dynamic map: {"Primary": 5, "Secondary": 2}
    attribute_counts: object     # Same structure as attribute_distributions
                                 # Tracks today's attribute class counts
    last_delivery: datetime
    date: date                   # Resets when date changes
```

**Attribute-Level Tracking Benefits:**

| Use Case | How Attribute Tracking Helps |
|----------|------------------------------|
| **Root-cause analysis** | "Your coarse_leaf count increased from 8% to 15%" |
| **Targeted coaching** | "Focus on harvesting dormant shoots earlier - hard banji ratio went up" |
| **Trend detection** | Compare 30d vs 90d attribute distributions to spot emerging issues |
| **Quality improvement** | Identify which specific attributes are dragging down grades |

**Farm Scale Classification:**

| Scale | Hectares | Typical Characteristics |
|-------|----------|------------------------|
| **Smallholder** | < 1 ha | Family-operated, manual harvesting, limited inputs |
| **Medium** | 1-5 ha | May employ seasonal labor, some mechanization |
| **Estate** | > 5 ha | Commercial operation, significant labor force, equipment |

**Yield Normalization Benefits:**

- **Fair comparison:** A 0.5ha farm delivering 100kg is performing better than a 5ha farm delivering 500kg
- **Percentile ranking:** Compare within the same farm_scale category to account for operational differences
- **Regional benchmarking:** `yield_vs_regional_avg` shows how a farmer compares to peers in similar conditions

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

# Collection Point Management
POST   /api/v1/collection-points              # Create CP (requires factory_id)
GET    /api/v1/collection-points              # List CPs (filter: factory_id, region_id, status)
GET    /api/v1/collection-points/{id}         # Get CP details
PUT    /api/v1/collection-points/{id}         # Update CP (hours, clerk, capacity)
DELETE /api/v1/collection-points/{id}         # Deactivate CP (soft delete)
GET    /api/v1/collection-points/nearby       # Find CPs near GPS (query: lat, lng, max_km)
```

### Internal Endpoints (service-to-service)

```
PUT    /api/v1/internal/farmer-summary/{id}     # Scheduler writes
PUT    /api/v1/internal/factory-summary/{id}    # Scheduler writes
PUT    /api/v1/internal/cp-summary/{id}         # Scheduler writes CP performance
PUT    /api/v1/internal/buyer-profiles/{id}     # Market Analysis writes
```

## MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer` | Farmer profile (includes farm_size_hectares) | `farmer_id` |
| `get_farmer_summary` | Performance summary (includes yield metrics) | `farmer_id`, `period?` |
| `get_factory` | Factory details + payment_policy | `factory_id` |
| `get_factory_config` | Grading model ref, thresholds | `factory_id` |
| `get_buyer_profiles` | Market preferences | `region?`, `factory_id?` |
| `get_farmer_context` | Combined view with scale + yield context | `farmer_id` |
| `get_region` | Region details + flush calendar | `region_id` |
| `get_region_weather` | Weather data for region (7-day history) | `region_id`, `days?` |
| `get_current_flush` | Current flush period for a region | `region_id` |
| `list_regions` | All regions with summary | `county?`, `altitude_band?` |
| `get_regional_yield_benchmark` | Average yield metrics for region by farm_scale | `region_id`, `farm_scale?` |
| `get_collection_point` | Collection point details + operating hours | `cp_id` |
| `list_collection_points` | Collection points for a factory or near GPS | `factory_id?`, `near_gps?`, `max_km?` |
| `get_farmer_collection_points` | CPs where farmer has delivered (by frequency) | `farmer_id` |
| `get_cp_performance` | Collection point performance metrics | `cp_id`, `period?` |
| `get_grading_model` | Full grading model definition | `model_id`, `version?` |
| `get_factory_grading_model` | Grading model active at factory | `factory_id` |
| `list_grading_models` | All grading models with summary | `market_name?`, `grading_type?` |

**Primary Consumer:** Action Plan Model queries via MCP for complete farmer context when generating recommendations.

**Weather Analyzer:** Uses `get_region`, `get_region_weather`, and `get_current_flush` to correlate weather events with quality issues using the 7-day lookback pattern.

**`get_farmer_context` Response Example:**

```yaml
# Returns combined farmer profile + performance with yield normalization
farmer_context:
  farmer_id: "WM-4521"
  name: "Mama Wanjiku"
  farm_size_hectares: 1.5
  farm_scale: "medium"           # Derived: <1ha=smallholder, 1-5ha=medium, >5ha=estate
  region_id: "nyeri-highland"

  performance:
    # Absolute metrics
    avg_grade_30d: "B+"
    delivery_count_30d: 12
    total_kg_30d: 180

    # Normalized yield metrics (key for fair comparison)
    yield_kg_per_hectare_30d: 120
    yield_vs_regional_avg: 0.85    # 85% of regional average for medium farms
    yield_percentile: 42           # 42nd percentile among medium farms in region
    improvement_trend: "improving"

  communication:
    pref_channel: "sms"
    pref_lang: "sw"
    literacy_lvl: "medium"
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Master data + summaries | Single source of truth for entities |
| **Farmer-Factory Relationship** | Indirect via Collection Points | Farmers can deliver to multiple CPs/factories |
| **Collection Point** | Separate entity, owned by Factory | Enables multi-factory farmers, clerk tracking, logistics |
| **Performance Summaries** | Pre-computed (daily batch) | Fast access, no real-time computation |
| **Yield Normalization** | kg/hectare + percentile ranking | Fair comparison across different farm sizes |
| **Farm Scale Classification** | smallholder/medium/estate | Enables scale-appropriate recommendations |
| **Grading Model** | Full definition stored | Enables attribute-level analytics, root-cause analysis, dynamic UI |
| **Buyer Profiles** | Stored here, written by Market Analysis | Centralized profile storage |
| **MCP Server** | Yes | AI agents need rich farmer/factory context |
| **Data Ownership** | Clear per-entity | Admin UI, Scheduler, Market Analysis |

## Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Admin API** | Input validation, authorization, audit trail |
| **Collection Point API** | GPS queries, factory assignment, clerk management |
| **Scheduler Job** | Reliability, computation accuracy, idempotency |
| **Yield Computation** | Normalization accuracy, percentile calculation |
| **Market Analysis Integration** | API contract, data integrity |
| **MCP Tools** | Correct data retrieval, access control |
| **Performance Summaries** | Aggregation accuracy vs. raw data |

---
