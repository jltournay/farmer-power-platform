# Epic 1: Farmer Registration & Data Foundation

Factory staff can register farmers into the system. Farmers receive their unique ID and are ready to be tracked.

**FRs covered:** FR34, FR35, FR36, FR37, FR38

**Scope:**
- Farmer master data storage (name, phone, national_id, farm_size, location)
- Factory and collection point data management
- Farmer ID generation (e.g., WM-4521)
- Performance history tracking structure
- Communication preferences (pref_channel, pref_lang)

---

## Stories

### Story 1.1: Plantation Model Service Setup

**[📄 Story File](../sprint-artifacts/1-1-plantation-model-service-setup.md)** | Status: Done

As a **platform operator**,
I want the Plantation Model service deployed with Dapr sidecar and MongoDB connection,
So that farmer and factory data can be stored and accessed by other services.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Plantation Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established (verified via connection test)
**And** gRPC server is listening on port 50051
**And** OpenTelemetry traces are emitted for all operations

**Technical Notes:**
- Python FastAPI + grpcio
- Dapr state store component for MongoDB
- Health endpoint: `/health` and `/ready`
- Environment: farmer-power-{env} namespace

---

### Story 1.2: Factory and Collection Point Management

**[📄 Story File](../sprint-artifacts/1-2-factory-and-collection-point-management.md)** | Status: Done

As a **platform administrator**,
I want to create and manage factories and collection points,
So that farmers can be associated with their delivery locations.

**Acceptance Criteria:**

**Given** the Plantation Model service is running
**When** I create a new factory via gRPC API
**Then** the factory is stored with: factory_id, name, location (region, gps), contact info
**And** a unique factory_id is generated (format: KEN-FAC-XXX)

**Given** a factory exists
**When** I create a collection point for that factory
**Then** the collection point is stored with: cp_id, name, factory_id, location, clerk_id, operating_hours, collection_days, capacity
**And** a unique cp_id is generated (format: {region}-cp-XXX)

**Given** a collection point exists
**When** I query collection points by factory_id
**Then** all collection points for that factory are returned

**Given** a collection point exists
**When** I update collection point details (operating_hours, clerk_id)
**Then** the changes are persisted and returned in subsequent queries

---

### Story 1.3: Farmer Registration

**[📄 Story File](../sprint-artifacts/1-3-farmer-registration.md)** | Status: Done

As a **collection point clerk**,
I want to register new farmers with their details,
So that farmers receive a unique ID and can deliver tea to the factory.

**Acceptance Criteria:**

**Given** a collection point exists
**When** I register a new farmer with: name, phone, national_id, farm_size_hectares, gps_location
**Then** a unique farmer_id is generated (format: WM-XXXX where X is numeric)
**And** the farmer is stored with all provided fields
**And** farm_scale is auto-calculated: smallholder (<1 ha), medium (1-5 ha), estate (>5 ha)
**And** created_at timestamp is recorded
**And** the farmer is linked to the collection_point_id

**Given** a farmer with phone number already exists
**When** I attempt to register with the same phone number
**Then** the registration fails with error "Phone number already registered"
**And** the existing farmer_id is returned for reference

**Given** a farmer is registered
**When** I query farmer by farmer_id
**Then** all farmer details are returned including calculated farm_scale

**Given** registration is complete
**When** the farmer record is created
**Then** an event "plantation.farmer.registered" is published to Dapr pub/sub
**And** the event payload includes farmer_id, phone, collection_point_id, factory_id

---

### Story 1.4: Farmer Performance History Structure

**[📄 Story File](../sprint-artifacts/1-4-farmer-performance-history-structure.md)** | Status: Done

As a **factory quality manager**,
I want farmer performance metrics tracked over time,
So that I can identify trends and target improvement efforts.

**Acceptance Criteria:**

**Given** a farmer exists in the system
**When** the farmer_performance subdocument is initialized
**Then** it contains: historical.deliveries_30d, historical.primary_percentage_30d, historical.yield_kg_per_hectare_30d, historical.yield_vs_regional_avg, historical.yield_percentile

**Given** a farmer has performance data
**When** I query get_farmer_summary(farmer_id)
**Then** the response includes: total_deliveries, avg_primary_percentage, trend (improving/stable/declining), last_delivery_date, yield metrics

**Given** new quality data arrives for a farmer
**When** the performance aggregation runs
**Then** 30-day rolling metrics are recalculated
**And** yield_vs_regional_avg is computed against regional averages
**And** the trend direction is determined (3+ deliveries required)

**Technical Notes:**
- Performance aggregation triggered by "collection.quality.received" event
- Regional averages computed per factory region
- Trend calculation: compare last 7 days avg vs previous 7 days

---

### Story 1.5: Farmer Communication Preferences

**[📄 Story File](../sprint-artifacts/1-5-farmer-communication-preferences.md)** | Status: Done

As a **farmer**,
I want to set my preferred communication channel and language,
So that I receive feedback in a way I can understand.

**Acceptance Criteria:**

**Given** a farmer is registered
**When** the farmer record is created
**Then** default preferences are set: pref_channel = "sms", pref_lang = "sw" (Swahili)

**Given** a farmer exists
**When** I update communication preferences via API
**Then** pref_channel can be set to: "sms", "whatsapp", "voice"
**And** pref_lang can be set to: "sw" (Swahili), "ki" (Kikuyu), "luo" (Luo), "en" (English)
**And** changes are persisted immediately

**Given** a farmer's preferences are updated
**When** the Notification Model queries farmer preferences
**Then** the current pref_channel and pref_lang are returned

**Given** an invalid preference value is provided
**When** I attempt to update preferences
**Then** the update fails with validation error listing valid options

---

### Story 1.6: Plantation Model MCP Server

**[📄 Story File](../sprint-artifacts/1-6-plantation-model-mcp-server.md)** | Status: Done

As an **AI agent**,
I want to access farmer and factory data via MCP tools,
So that I can generate personalized recommendations.

**Acceptance Criteria:**

**Given** the Plantation MCP Server is deployed
**When** an AI agent calls `get_farmer(farmer_id)`
**Then** the response includes: name, phone, farm_size_hectares, farm_scale, region, collection_point_id, pref_lang, notification_channel, interaction_pref

**Given** a farmer_id exists
**When** an AI agent calls `get_farmer_summary(farmer_id)`
**Then** the response includes: performance metrics, trend_direction, grading info, historical quality data (avg_grade, total_kg, delivery_count), and communication preferences

**Given** a factory_id exists
**When** an AI agent calls `get_collection_points(factory_id)`
**Then** all collection points for that factory are returned with their details

**Given** a collection_point_id exists
**When** an AI agent calls `get_farmers_by_collection_point(cp_id)`
**Then** all farmers registered at that collection point are returned

**Given** the MCP Server receives a request
**When** processing completes
**Then** OpenTelemetry traces are emitted with tool name and duration
**And** errors are logged with full context

**Given** an AI agent calls a tool with invalid arguments
**When** validation fails
**Then** a ToolCallResponse is returned with success=false and error_code=INVALID_ARGUMENTS

**Given** the Plantation Model service is unavailable
**When** the MCP Server tries to fetch data
**Then** a ToolCallResponse is returned with success=false and error_code=SERVICE_UNAVAILABLE

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment (`mcp-servers/plantation-mcp/`)
- HPA enabled: min 2, max 10 replicas
- gRPC interface following MCP protocol from Story 0-1
- Uses DAPR service invocation to call Plantation Model service
- JSON Schema validation for all tool inputs

**Phase 1 Tools (This Story):**
- `get_farmer` - Farmer profile with preferences
- `get_farmer_summary` - Performance metrics and trends
- `get_collection_points` - Collection points by factory
- `get_farmers_by_collection_point` - Farmers at a collection point

**Deferred Tools (Future Stories):**

| Tool | Needed By | Epic |
|------|-----------|------|
| `get_region`, `list_regions`, `get_region_weather`, `get_current_flush` | Weather Analyzer | Epic 5 |
| `get_regional_yield_benchmark` | Action Plan Generator | Epic 6 |
| `get_buyer_profiles` | Market Analysis Model | Epic 5 |
| `get_farmer_context` | Action Plan Generator | Epic 6 |

**Dependencies:**
- Story 0-1: MCP gRPC Infrastructure (proto, client library)

---

### Story 1.7: Quality Grading Event Subscription

**[📄 Story File](../sprint-artifacts/1-7-quality-grading-event-subscription.md)** | Status: Done

As a **factory quality manager**,
I want farmer performance metrics updated automatically when grading results arrive from the QC Analyzer,
So that I can see real-time quality trends without manual data entry.

**Acceptance Criteria:**

**Given** a `collection.quality_result.received` event is received from Collection Model
**When** the Plantation Model processes the event
**Then** the quality document is retrieved from Collection MCP using the `document_id`
**And** the `GradingModel` is loaded using both `grading_model_id` AND `grading_model_version` from the document
**And** grade counts are extracted for each label in `grading_model.grade_labels`

**Given** quality data contains grade counts and `attribute_distribution`
**When** the farmer's performance is updated
**Then** `FarmerPerformance.today` is updated with:
  - `deliveries` incremented by 1
  - `total_kg` incremented (if `total_weight_kg` available)
  - `grade_counts[label]` incremented by the count for EACH label from the grading model
  - `attribute_counts` updated with attribute distribution
  - `last_delivery` timestamp updated

**Given** the performance update is complete
**When** downstream services need notification
**Then** a `plantation.quality.graded` event is emitted via DAPR Pub/Sub
**And** the event payload includes: `farmer_id`, `document_id`, `grade_counts` (dict), `attribute_distribution` (dict), `timestamp`

**Given** the performance update is complete
**When** the Engagement Model needs historical context
**Then** a `plantation.performance_updated` event is emitted via DAPR Pub/Sub
**And** the event payload includes: `farmer_id`, `factory_id`, `primary_percentage`, `improvement_trend`, `today` summary

**Given** it's the first delivery of a new day
**When** the performance is updated
**Then** `FarmerPerformance.today` is reset before applying the update

**Given** invalid or incomplete quality data is received
**When** processing fails
**Then** the event is logged with error details
**And** the farmer's record is NOT updated
**And** metrics are emitted for monitoring

**Technical Notes:**
- Model-driven design: Grade labels come from `GradingModel`, never hardcoded
- Leaf-level classification: QC Analyzer classifies individual leaves, not bags
- Two domain events emitted: `plantation.quality.graded` and `plantation.performance_updated`
- Atomic MongoDB updates using `$inc` for counters
- `QualityThresholds` value object added to Factory entity (tier_1, tier_2, tier_3)
- `get_factory` MCP tool added with quality_thresholds in response

**Dependencies:**
- Story 2.4: Generic Content Processing Framework (emits the event)
- Story 2.9: Collection Model MCP Server (provides `get_document` tool)

---

### Story 1.8: Region Entity & Weather Configuration

**[📄 Story File](../sprint-artifacts/1-8-region-entity-weather-configuration.md)** | Status: Done

As a **platform operator**,
I want regions defined with weather configuration,
So that weather data can be collected per region for quality correlation.

**Acceptance Criteria:**

**Given** a region configuration is provided
**When** the region is created
**Then** the Region entity is stored with: `region_id`, `county`, `altitude_band`, `altitude_range`, `weather_config`, `flush_calendar`

**Given** a region_id exists
**When** an AI agent calls `get_region(region_id)`
**Then** the response includes region metadata and weather configuration

**Given** the Plantation MCP Server is deployed
**When** an AI agent calls `list_regions(county?, altitude_band?)`
**Then** matching regions are returned with their details

**Given** a region has flush_calendar configured
**When** an AI agent calls `get_current_flush(region_id)`
**Then** the current flush period is returned based on today's date

**Given** Collection Model publishes `collection.weather.updated` event
**When** Plantation Model receives the event
**Then** `RegionalWeather` entity is updated with weather observations
**And** weather data is available via `get_region_weather(region_id, days?)` MCP tool

**Technical Notes:**
- Region entity required for weather correlation (Story 5.5: Weather Impact Analyzer)
- `weather_config` contains API location (lat/lng) for Open-Meteo API
- `flush_calendar` defines seasonal harvest timing per region
- Weather data stored in Plantation Model, fed by Collection Model events
- MCP tools: `get_region`, `list_regions`, `get_current_flush`, `get_region_weather`

**Dependencies:**
- Story 2.7: Scheduled Pull Ingestion Framework (fetches weather data)

---

### Story 1.9: Factory Payment Policy Configuration

**[📄 Story File](../sprint-artifacts/1-9-payment-policy-configuration.md)** | Status: Done ✅

As a **factory administrator**,
I want to configure payment policies for my factory,
So that farmers receive quality-based payment adjustments according to our chosen incentive model.

**Acceptance Criteria:**

**Given** the Plantation Model service is running
**When** I create or update a factory
**Then** the factory can include a `payment_policy` with:
  - `policy_type`: one of "split_payment", "weekly_bonus", "delayed_payment", "feedback_only"
  - `tier_1_adjustment`: percentage adjustment for Premium tier (e.g., +0.15 for +15%)
  - `tier_2_adjustment`: percentage adjustment for Standard tier (typically 0.0 for base rate)
  - `tier_3_adjustment`: percentage adjustment for Acceptable tier (e.g., -0.05 for -5%)
  - `below_tier_3_adjustment`: percentage adjustment for Below Standard (e.g., -0.10 for -10%)

**Given** a factory has no payment_policy configured
**When** the factory is queried
**Then** default values are returned: `policy_type="feedback_only"`, all adjustments = 0.0

**Given** a factory has payment_policy configured
**When** an AI agent calls `get_factory(factory_id)`
**Then** the response includes the full `payment_policy` configuration

**Given** a factory exists
**When** I update only the payment_policy
**Then** the changes are persisted and returned in subsequent queries
**And** `updated_at` timestamp is refreshed

**Given** invalid adjustment values are provided (e.g., > 1.0 or < -1.0)
**When** I attempt to save the configuration
**Then** validation fails with appropriate error message

**Technical Notes:**
- `PaymentPolicy` value object added to Factory entity
- Proto definition: `PaymentPolicy` message with `policy_type` enum and adjustment fields
- `get_factory` MCP tool updated to include payment_policy in response
- Factory Admin UI (Epic 3, Story 3.8) will consume this configuration for display/editing
- Payment calculation is external (factory payroll systems consume this configuration via API)

**Dependencies:**
- Story 1.2: Factory and Collection Point Management (Factory entity exists)

---

### Story 1.10: GPS-Based Region Assignment with Polygon Boundaries

**Story File:** Backlog | Status: Backlog
**Blocks:** Epic 9 (Admin Portal - Region boundary drawing in Story 9.2)
**Related ADR:** [ADR-017: Map Services and GPS-Based Region Assignment](../architecture/adr/ADR-017-map-services-gps-region-assignment.md)

As a **platform operator**,
I want regions defined with polygon boundaries instead of hardcoded bounding boxes,
So that farmers are accurately assigned to regions based on their farm GPS coordinates.

**Problem Statement:**

The current `assign_region_from_altitude()` function uses hardcoded rectangular bounding boxes to determine which county a farmer belongs to:

```python
# Current: Hardcoded boxes that overlap and cannot represent irregular boundaries
if -0.6 <= latitude <= 0.0 and 36.5 <= longitude <= 37.5:
    county = "nyeri"
elif -0.8 <= latitude <= 0.0 and 35.0 <= longitude <= 36.0:
    county = "kericho"
```

This approach:
- Cannot represent irregular administrative boundaries
- Causes incorrect assignments in overlapping areas
- Requires code changes to add new regions
- Provides no visual feedback for administrators

**Acceptance Criteria:**

**AC 1.10.1: RegionBoundary Value Object**

**Given** the `fp_common.models.value_objects` module
**When** the `RegionBoundary` Pydantic model is created
**Then** it supports GeoJSON Polygon format with coordinates validation
**And** it validates that polygons are closed (first point == last point)
**And** it validates coordinate ranges (lng: -180 to 180, lat: -90 to 90)

**AC 1.10.2: Geography Model Extended**

**Given** the existing `Geography` value object
**When** it is extended with boundary support
**Then** it includes an optional `boundary: RegionBoundary | None` field
**And** it includes optional `area_km2` and `perimeter_km` computed fields
**And** existing regions without boundaries continue to work (backward compatible)

**AC 1.10.3: Proto Definitions Updated**

**Given** the `proto/plantation/v1/plantation.proto` file
**When** boundary support is added
**Then** `RegionBoundary` message is defined with type and coordinates
**And** `Coordinate` message is defined with longitude and latitude
**And** `Geography` message includes optional boundary field

**AC 1.10.4: RegionAssignmentService Created**

**Given** a new `RegionAssignmentService` class
**When** `assign_region(latitude, longitude, altitude)` is called
**Then** it loads all active regions from the repository
**And** it checks each region's polygon boundary using point-in-polygon algorithm
**And** it verifies the farm altitude matches the region's altitude band
**And** it returns the matching `region_id` or falls back to nearest center by altitude band

**AC 1.10.5: Point-in-Polygon Algorithm**

**Given** a farm GPS coordinate and a region with polygon boundary
**When** the point-in-polygon check is performed
**Then** the ray casting algorithm correctly determines if the point is inside
**And** edge cases (point on boundary, complex polygons) are handled correctly

**AC 1.10.6: Backward Compatibility**

**Given** existing regions without polygon boundaries
**When** a farmer is registered in an area without boundary-defined regions
**Then** the fallback algorithm matches by altitude band and nearest center
**And** no data migration is required for existing regions

**Technical Notes:**

**Files to Modify:**

| File | Change |
|------|--------|
| `libs/fp-common/fp_common/models/value_objects.py` | ADD `RegionBoundary`, MODIFY `Geography` |
| `proto/plantation/v1/plantation.proto` | ADD `RegionBoundary`, `Coordinate`, MODIFY `Geography` |
| `services/plantation-model/src/plantation_model/domain/region_assignment.py` | NEW file with `RegionAssignmentService` |
| `services/plantation-model/src/plantation_model/infrastructure/google_elevation.py` | REMOVE `assign_region_from_altitude()` function (keep `GoogleElevationClient`) |

**Note:** The `CreateFarmer` gRPC handler does NOT need modification. The map UI is purely for user convenience to click and get GPS coordinates - the service already accepts lat/lng inputs.

**Point-in-Polygon Algorithm:**
- Use ray casting algorithm (standard, well-tested)
- Count intersections of horizontal ray from point to infinity
- Odd count = inside, even count = outside

**Dependencies:**
- Story 1.8: Region Entity & Weather Configuration (Region model exists)
- Google Elevation API integration (unchanged, continues to provide altitude)

**Enables:**
- Epic 9, Story 9.2: Region boundary drawing in Admin Portal UI
- Epic 9, Story 9.5: Farm location picker in Farmer registration UI

---

### Story 1.11: Auto-Assignment of Farmer to Collection Point on Quality Result

**Story File:** Backlog | Status: Backlog
**Depends on:** Story 9.5a (Farmer-CP Data Model Refactor)
**Related:** GitHub Issue #200

As a **platform operator**,
I want farmers to be automatically assigned to a collection point when their first quality result is received there,
So that the farmer-CP relationship is established without manual intervention.

**Problem Statement:**

After Story 9.5a refactors the data model to N:M (farmer_ids on CollectionPoint), we need a mechanism to populate this relationship. While manual assignment is supported via admin UI, most assignments should happen automatically when a farmer delivers tea to a collection point.

**Acceptance Criteria:**

**AC 1.11.1: Auto-Assignment on Quality Result**

**Given** a `collection.quality_result.received` event is received
**And** the event contains `farmer_id` and `collection_point_id`
**When** the quality event processor validates the farmer
**Then** if the farmer is NOT already in the CP's `farmer_ids` list
**And** the system calls `AssignFarmerToCollectionPoint(farmer_id, cp_id)`
**And** the farmer is added to the CP's `farmer_ids` list

**AC 1.11.2: Idempotent Assignment**

**Given** a farmer is already assigned to a collection point
**When** another quality result arrives for the same farmer at the same CP
**Then** no duplicate assignment occurs (idempotent)
**And** no error is raised
**And** quality processing continues normally

**AC 1.11.3: Cross-Factory Assignment**

**Given** a farmer is assigned to CP-A (Factory 1)
**When** a quality result arrives for the same farmer at CP-B (Factory 2)
**Then** the farmer is ALSO assigned to CP-B
**And** the farmer now appears in both CP-A and CP-B's `farmer_ids` lists
**And** the farmer's "factory count" is now 2

**AC 1.11.4: Event Emission**

**Given** a farmer is auto-assigned to a new collection point
**When** the assignment completes
**Then** a `plantation.farmer.assigned` event is emitted
**And** the event payload includes: `farmer_id`, `collection_point_id`, `factory_id`, `assignment_type: "auto"`

**AC 1.11.5: Logging and Metrics**

**Given** auto-assignment occurs
**When** the assignment completes or fails
**Then** structured logs capture: farmer_id, cp_id, success/failure, duration
**And** metrics are emitted for monitoring auto-assignment rate

**Technical Notes:**

**Wiring Point:**

The auto-assignment logic wires into `quality_event_processor.py`:

```python
# services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py
# After farmer validation (around line 191)

async def process_quality_event(self, event: QualityResultEvent) -> None:
    # ... existing validation ...
    farmer = await self._validate_farmer_id(document_id, farmer_id)

    # NEW: Auto-assign farmer to CP if not already assigned
    cp_id = document.collection_point_id
    await self._ensure_farmer_assigned_to_cp(farmer.id, cp_id)

    # ... continue with performance update ...
```

**New Method in QualityEventProcessor:**

```python
async def _ensure_farmer_assigned_to_cp(self, farmer_id: str, cp_id: str) -> None:
    """Auto-assign farmer to CP if not already assigned (idempotent)."""
    cp = await self._cp_repo.get_by_id(cp_id)
    if cp is None:
        # CP validation should have caught this earlier
        return

    if farmer_id not in cp.farmer_ids:
        # Use the gRPC method from Story 9.5a
        await self._cp_repo.add_farmer(cp_id, farmer_id)

        # Emit assignment event
        await self._publish_farmer_assigned_event(farmer_id, cp_id, cp.factory_id)
```

**Files to Modify:**

| File | Change |
|------|--------|
| `services/plantation-model/.../domain/services/quality_event_processor.py` | Add `_ensure_farmer_assigned_to_cp()` method |
| `services/plantation-model/.../infrastructure/repositories/collection_point_repository.py` | Use `add_farmer()` method from Story 9.5a |
| `services/plantation-model/.../events/publisher.py` | Add `plantation.farmer.assigned` event |
| `proto/plantation/v1/events.proto` | Add `FarmerAssignedEvent` message |

**Dependencies:**
- Story 9.5a: Farmer-CP Data Model Refactor (provides `farmer_ids` on CP and `add_farmer()` method)

**Story Points:** 3

---

## Retrospective

**[📋 Epic 1 Retrospective](../sprint-artifacts/epic-1-retrospective.md)** | Status: Done
