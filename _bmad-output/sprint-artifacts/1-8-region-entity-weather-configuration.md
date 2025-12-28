# Story 1.8: Region Entity & Weather Configuration

**Status:** in-progress
**GitHub Issue:** #25

---

## Story

As a **platform operator**,
I want regions defined with weather configuration,
So that weather data can be collected per region for quality correlation.

---

## Context: Completing Epic 1

This story implements the **Region entity** required for:
- Weather correlation analysis (Epic 5: Knowledge Model)
- Seasonal context via flush calendar
- Efficient weather data collection (50 API calls vs 800,000)

**Key Dependencies:**
- Story 2.7 (Scheduled Pull Ingestion Framework) provides `collection.weather.updated` events
- Story 5.5 (Weather Impact Analyzer) will consume region weather data via MCP

---

## Acceptance Criteria

1. **Given** a region configuration is provided
   **When** the region is created via gRPC API
   **Then** the Region entity is stored with: `region_id`, `county`, `altitude_band`, `altitude_range`, `weather_config`, `flush_calendar`
   **And** a unique `region_id` is generated (format: `{county}-{altitude_band}`, e.g., `nyeri-highland`)

2. **Given** a region_id exists
   **When** an AI agent calls `get_region(region_id)` via MCP
   **Then** the response includes: region metadata, geography, agronomic factors, weather_config, flush_calendar

3. **Given** the Plantation MCP Server is deployed
   **When** an AI agent calls `list_regions(county?, altitude_band?)`
   **Then** matching regions are returned with their details
   **And** results can be filtered by county and/or altitude_band

4. **Given** a region has `flush_calendar` configured
   **When** an AI agent calls `get_current_flush(region_id)`
   **Then** the current flush period is returned based on today's date
   **And** the response includes: flush_name, start_date, end_date, characteristics

5. **Given** Collection Model publishes `collection.weather.updated` event
   **When** Plantation Model receives the event
   **Then** `RegionalWeather` entity is updated with weather observations
   **And** observations are stored with: `region_id`, `date`, `temp_min`, `temp_max`, `precipitation_mm`, `humidity_avg`

6. **Given** weather data exists for a region
   **When** an AI agent calls `get_region_weather(region_id, days?)`
   **Then** weather observations for the last N days are returned (default: 7)
   **And** results are ordered by date descending

7. **Given** invalid region data is provided
   **When** I attempt to create a region
   **Then** validation errors are returned with specific field failures
   **And** the region is NOT created

---

## Tasks / Subtasks

- [x] **Task 1: Create Region domain model** (AC: #1, #7)
  - [x] 1.1 Create `domain/models/region.py` with `Region` entity
  - [x] 1.2 Create `Geography` value object: `center_gps`, `radius_km`, `altitude_band` (min/max/label)
  - [x] 1.3 Create `FlushCalendar` value object with flush periods (first_flush, monsoon_flush, autumn_flush, dormant)
  - [x] 1.4 Create `FlushPeriod` value object: `start` (MM-DD), `end` (MM-DD), `characteristics`
  - [x] 1.5 Create `WeatherConfig` value object: `api_location` (lat/lng), `altitude_for_api`, `collection_time`
  - [x] 1.6 Create `Agronomic` value object: `soil_type`, `typical_diseases`, `harvest_peak_hours`, `frost_risk`
  - [x] 1.7 Add validation: `region_id` format must be `{county}-{altitude_band}` (lowercase, hyphenated)
  - [x] 1.8 Add validation: altitude_band.label must be one of: "highland", "midland", "lowland"
  - [x] 1.9 Unit tests for Region entity validation (37 tests)

- [x] **Task 2: Create RegionalWeather domain model** (AC: #5, #6)
  - [x] 2.1 Create `domain/models/regional_weather.py` with `RegionalWeather` entity
  - [x] 2.2 Fields: `region_id`, `date`, `temp_min`, `temp_max`, `precipitation_mm`, `humidity_avg`, `created_at`
  - [x] 2.3 Add `WeatherObservation` value object for daily observations
  - [x] 2.4 Unit tests for RegionalWeather entity (8 tests)

- [x] **Task 3: Create Region repository** (AC: #1, #2, #3)
  - [x] 3.1 Create `infrastructure/repositories/region_repository.py`
  - [x] 3.2 Implement `create(region)` with MongoDB insert
  - [x] 3.3 Implement `get_by_id(region_id)` for single region lookup
  - [x] 3.4 Implement `list(county?, altitude_band?)` with optional filters
  - [x] 3.5 Implement `update(region_id, updates)` for region modifications
  - [x] 3.6 Add MongoDB indexes: `region_id` (unique), `county`, `altitude_band`
  - [x] 3.7 Unit tests for repository (12 tests)

- [x] **Task 4: Create RegionalWeather repository** (AC: #5, #6)
  - [x] 4.1 Create `infrastructure/repositories/regional_weather_repository.py`
  - [x] 4.2 Implement `upsert_observation(region_id, date, observation)` with MongoDB upsert
  - [x] 4.3 Implement `get_weather_history(region_id, days)` for recent observations
  - [x] 4.4 Add MongoDB index: compound `(region_id, date)` for efficient queries
  - [x] 4.5 Add TTL index for automatic data expiration (90 days)
  - [x] 4.6 Unit tests for repository (9 tests)

- [x] **Task 5: Update Proto definitions** (AC: #1, #2)
  - [x] 5.1 Add `Region` message to `proto/plantation/v1/plantation.proto`
  - [x] 5.2 Add `Geography`, `FlushCalendar`, `FlushPeriod`, `WeatherConfig`, `Agronomic` messages
  - [x] 5.3 Add `CreateRegionRequest`, `CreateRegionResponse` messages
  - [x] 5.4 Add `GetRegionRequest`, `GetRegionResponse` messages
  - [x] 5.5 Add `ListRegionsRequest`, `ListRegionsResponse` messages
  - [x] 5.6 Add `region` RPC methods to `PlantationService`
  - [x] 5.7 Regenerate Python stubs via `scripts/proto-gen.sh`

- [x] **Task 6: Implement gRPC Region API** (AC: #1, #2, #3)
  - [x] 6.1 Add `CreateRegion` handler to `api/plantation_service.py`
  - [x] 6.2 Add `GetRegion` handler
  - [x] 6.3 Add `ListRegions` handler with optional county/altitude_band filters
  - [x] 6.4 Add `UpdateRegion` handler for region modifications
  - [x] 6.5 Add `GetRegionWeather` and `GetCurrentFlush` handlers
  - [x] 6.6 OpenTelemetry tracing included in handlers

- [x] **Task 7: Implement weather event subscription** (AC: #5)
  - [x] 7.1 Create `api/event_handlers/weather_updated_handler.py`
  - [x] 7.2 Implement DAPR subscription for `collection.weather.updated` topic
  - [x] 7.3 Parse event payload: `region_id`, `date`, `observations`
  - [x] 7.4 Call RegionalWeather repository to upsert observation
  - [x] 7.5 Add error handling for invalid/incomplete weather data
  - [x] 7.6 Add OpenTelemetry tracing for event processing
  - [x] 7.7 Subscription config returned by `get_weather_subscriptions()`
  - [x] 7.8 Unit tests for event handler (9 tests)

- [ ] **Task 8: Add MCP tools to Plantation MCP Server** (AC: #2, #3, #4, #6)
  - [ ] 8.1 Add `get_region` tool to `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py`
  - [ ] 8.2 Add `list_regions` tool with optional county/altitude_band filters
  - [ ] 8.3 Add `get_current_flush` tool with flush period calculation logic
  - [ ] 8.4 Add `get_region_weather` tool with days parameter (default: 7)
  - [ ] 8.5 Implement handlers in `api/mcp_service.py`
  - [ ] 8.6 Update `infrastructure/plantation_client.py` with region methods
  - [ ] 8.7 Unit tests for MCP tools (8-10 tests)

- [x] **Task 9: Implement flush period calculation** (AC: #4)
  - [x] 9.1 Create `domain/services/flush_calculator.py`
  - [x] 9.2 Implement `get_current_flush(flush_calendar, current_date)` method
  - [x] 9.3 Handle edge cases: date at boundary, dormant period spanning year end
  - [x] 9.4 Return: `flush_name`, `start_date`, `end_date`, `characteristics`, `days_remaining`
  - [x] 9.5 Unit tests for flush calculation (14 tests including edge cases)

- [ ] **Task 10: Integration tests** (AC: #1-6)
  - [ ] 10.1 Create `tests/integration/test_region_flow.py`
  - [ ] 10.2 Test full region CRUD via gRPC
  - [ ] 10.3 Test weather event subscription with mock DAPR
  - [ ] 10.4 Test MCP tool calls via Plantation MCP client
  - [ ] 10.5 Test flush period calculation across different dates
  - [ ] 10.6 Integration tests (8-10 tests)

---

## Dev Notes

### Service Location

All code goes in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── api/
│   │   ├── event_handlers/
│   │   │   ├── quality_result_handler.py    # Existing (Story 1.7)
│   │   │   └── weather_updated_handler.py   # NEW
│   │   └── plantation_service.py            # MODIFY - add region handlers
│   ├── domain/
│   │   ├── models/
│   │   │   ├── region.py                    # NEW
│   │   │   └── regional_weather.py          # NEW
│   │   └── services/
│   │       └── flush_calculator.py          # NEW
│   └── infrastructure/
│       └── repositories/
│           ├── region_repository.py         # NEW
│           └── regional_weather_repository.py # NEW
```

### Region Entity Schema (from Architecture)

```yaml
region:
  # Identity
  region_id: "nyeri-highland"           # Pattern: {county}-{altitude_band}
  name: "Nyeri Highland"
  county: "Nyeri"
  country: "Kenya"

  # Geography
  geography:
    center_gps:
      lat: -0.4197
      lng: 36.9553
    radius_km: 25
    altitude_band:
      min_meters: 1800
      max_meters: 2200
      label: "highland"                 # highland | midland | lowland

  # Flush Calendar (Tea Seasons)
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

  # Agronomic Factors
  agronomic:
    soil_type: "volcanic_red"
    typical_diseases: ["blister_blight", "grey_blight", "red_rust"]
    harvest_peak_hours: "06:00-10:00"
    frost_risk: true

  # Weather Configuration
  weather_config:
    api_location:
      lat: -0.4197
      lng: 36.9553
    altitude_for_api: 1950
    collection_time: "06:00"
```

### Altitude Band Definitions

| Altitude Band | Elevation Range | Characteristics |
|---------------|-----------------|-----------------|
| **Highland** | 1800m+ | Cooler, more rainfall, later flushes, frost risk |
| **Midland** | 1400m - 1800m | Moderate conditions, typical patterns |
| **Lowland** | Below 1400m | Warmer, earlier flushes, different disease profile |

### Weather Event Payload (from Collection Model)

```json
{
  "region_id": "nyeri-highland",
  "date": "2025-12-28",
  "observations": {
    "temp_min": 12.5,
    "temp_max": 24.8,
    "precipitation_mm": 2.3,
    "humidity_avg": 78.5
  },
  "source": "open-meteo",
  "collected_at": "2025-12-28T06:00:00Z"
}
```

### MCP Tools Summary

| Tool | Purpose | Parameters | Response |
|------|---------|------------|----------|
| `get_region` | Region details + flush calendar | `region_id` | Full region entity |
| `list_regions` | All regions with summary | `county?`, `altitude_band?` | List of regions |
| `get_current_flush` | Current flush period | `region_id` | Flush name, dates, days remaining |
| `get_region_weather` | Weather history | `region_id`, `days?` (default: 7) | List of daily observations |

### Flush Period Calculation Logic

```python
def get_current_flush(flush_calendar: FlushCalendar, current_date: date) -> FlushPeriod | None:
    """
    Determine current flush period based on date.

    Handles year-spanning dormant period (Dec 16 - Mar 14).
    Returns None if no flush matches (shouldn't happen with valid calendar).
    """
    month_day = current_date.strftime("%m-%d")

    for flush_name, period in flush_calendar.items():
        start = period.start  # "MM-DD"
        end = period.end      # "MM-DD"

        # Handle year-spanning period (dormant)
        if start > end:  # e.g., "12-16" to "03-14"
            if month_day >= start or month_day <= end:
                return FlushResult(
                    name=flush_name,
                    period=period,
                    days_remaining=calculate_days_remaining(current_date, end),
                )
        else:
            if start <= month_day <= end:
                return FlushResult(
                    name=flush_name,
                    period=period,
                    days_remaining=calculate_days_remaining(current_date, end),
                )

    return None
```

### Weather Cost Optimization

| Approach | API Calls/Day | Annual Cost (at $0.001/call) |
|----------|---------------|------------------------------|
| Per Farm (800,000 farms) | 800,000 | ~$292,000 |
| Per Region (~50 regions) | 50 | ~$18 |

Regions enable 16,000x cost reduction by grouping farms with similar weather conditions.

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Repository operations, event handlers
2. **Use DAPR for inter-service communication** - Weather event subscription
3. **Use DAPR Pub/Sub for events** - Subscribe to `collection.weather.updated`
4. **MCP servers are STATELESS** - No caching in MCP server
5. **Atomic MongoDB operations** - Use upsert for weather observations
6. **Pydantic 2.0 syntax** - Use `model_dump()` not `dict()`

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_region.py` - Region entity validation
- `test_regional_weather.py` - RegionalWeather entity
- `test_region_repository.py` - Repository CRUD operations
- `test_regional_weather_repository.py` - Weather storage
- `test_flush_calculator.py` - Flush period calculation
- `test_weather_updated_handler.py` - Event handler

**Integration Tests (`tests/integration/`):**
- `test_region_flow.py` - Full region lifecycle

**MCP Tests (`tests/unit/plantation_mcp/`):**
- `test_region_tools.py` - MCP tool implementations

### OpenTelemetry Metrics

```python
# Metrics to emit
plantation.region.created{county="...", altitude_band="..."}  # Counter
plantation.weather.updated{region_id="..."}                    # Counter
plantation.weather.update_failed{reason="..."}                 # Counter
plantation.flush.lookup{flush_name="...", region_id="..."}     # Counter
```

### Project Structure Notes

- Region entity aligns with `_bmad-output/architecture/plantation-model-architecture.md`
- Weather config uses Open-Meteo API location format (lat/lng)
- Flush calendar uses MM-DD format for seasonal periods
- RegionalWeather uses separate collection for efficient TTL management

### References

- [Source: _bmad-output/architecture/plantation-model-architecture.md#Region Entity] - Region schema
- [Source: _bmad-output/architecture/plantation-model-architecture.md#Weather Configuration] - Weather cost optimization
- [Source: _bmad-output/project-context.md#Region Definition] - Altitude band definitions
- [Source: _bmad-output/epics/epic-1-plantation-model.md#Story 1.8] - Acceptance criteria
- [Source: _bmad-output/sprint-artifacts/1-7-quality-grading-event-subscription.md] - Event handler pattern

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **89 unit tests passing** covering Region entity (37), RegionalWeather (8), Region repository (12), RegionalWeather repository (9), FlushCalculator (14), and weather event handler (9)
- Tasks 1-7 and 9 completed; Tasks 8 (MCP tools) and 10 (integration tests) deferred for follow-up
- Proto definitions updated and regenerated via `scripts/proto-gen.sh`
- gRPC API handlers added to `plantation_service.py` for Region CRUD, weather history, and current flush
- Weather event subscription handler implemented following existing quality_result_handler pattern
- FlushCalculator correctly handles year-spanning dormant period (Dec 16 - Mar 14)

### File List

**New Files Created:**
- `services/plantation-model/src/plantation_model/domain/models/region.py`
- `services/plantation-model/src/plantation_model/domain/models/regional_weather.py`
- `services/plantation-model/src/plantation_model/infrastructure/repositories/region_repository.py`
- `services/plantation-model/src/plantation_model/infrastructure/repositories/regional_weather_repository.py`
- `services/plantation-model/src/plantation_model/domain/services/flush_calculator.py`
- `services/plantation-model/src/plantation_model/api/event_handlers/weather_updated_handler.py`
- `tests/unit/plantation/test_region.py`
- `tests/unit/plantation/test_regional_weather.py`
- `tests/unit/plantation/test_region_repository.py`
- `tests/unit/plantation/test_regional_weather_repository.py`
- `tests/unit/plantation/test_flush_calculator.py`
- `tests/unit/plantation/test_weather_updated_handler.py`

**Modified Files:**
- `services/plantation-model/src/plantation_model/domain/models/value_objects.py` (added GPS, AltitudeBand, Geography, FlushPeriod, FlushCalendar, WeatherConfig, Agronomic)
- `services/plantation-model/src/plantation_model/domain/models/__init__.py` (exports)
- `services/plantation-model/src/plantation_model/api/plantation_service.py` (Region handlers)
- `services/plantation-model/src/plantation_model/api/event_handlers/__init__.py` (weather handler export)
- `proto/plantation/v1/plantation.proto` (Region, RegionalWeather, flush messages)
- `libs/fp-proto/src/fp_proto/plantation/v1/*.py` (regenerated)
