# Story 1.10: GPS-Based Region Assignment with Polygon Boundaries

**Status:** in-progress
**GitHub Issue:** #181

## Story

As a **platform operator**,
I want regions defined with polygon boundaries instead of hardcoded bounding boxes,
So that farmers are accurately assigned to regions based on their farm GPS coordinates.

---

## Context

This is the final story of Epic 1: Farmer Registration & Data Foundation. It replaces the hardcoded rectangular bounding box logic in `assign_region_from_altitude()` with a proper polygon-based region assignment service.

### Problem Statement

Current implementation uses hardcoded rectangular bounding boxes:

```python
# CURRENT (services/plantation-model/src/plantation_model/infrastructure/google_elevation.py)
if -0.6 <= latitude <= 0.0 and 36.5 <= longitude <= 37.5:
    county = "nyeri"
elif -0.8 <= latitude <= 0.0 and 35.0 <= longitude <= 36.0:
    county = "kericho"
```

**Issues:**
1. Cannot represent irregular administrative boundaries
2. Causes incorrect assignments in overlapping areas
3. Requires code changes to add new regions
4. Provides no visual feedback for administrators

### Solution

Implement GeoJSON polygon boundaries with point-in-polygon algorithm for accurate farmer-to-region assignment.

**Architecture:** ADR-017 - Map Services and GPS-Based Region Assignment

**Blocks:**
- Epic 9, Story 9.2: Region Management (boundary drawing UI)
- Epic 9, Story 9.5: Farmer Management (location picker UI)

**Depends On:**
- Story 1.8: Region Entity & Weather Configuration (Region model exists)

---

## Acceptance Criteria

### AC 1.10.1: RegionBoundary Value Object

**Given** a region boundary definition in GeoJSON Polygon format
**When** I validate the boundary
**Then** it validates:
- Polygon has at least one ring with >= 4 points
- First point equals last point (closed polygon)
- Coordinate ranges: longitude -180 to 180, latitude -90 to 90
- Uses `[longitude, latitude]` order (GeoJSON standard)

### AC 1.10.2: Geography Model Extended

**Given** the existing Geography value object
**When** I extend it for polygon support
**Then** it includes:
- `boundary: RegionBoundary | None` (optional - backward compatible)
- `area_km2: float | None` (computed from boundary)
- `perimeter_km: float | None` (computed from boundary)

### AC 1.10.3: Proto Definitions Updated

**Given** the plantation.proto file
**When** I add polygon support
**Then** it includes:
- `Coordinate` message with longitude and latitude
- `PolygonRing` message with repeated Coordinate points
- `RegionBoundary` message with type="Polygon" and rings
- `Geography` message updated with boundary, area_km2, perimeter_km

### AC 1.10.4: RegionAssignmentService Created

**Given** a farm GPS coordinate (latitude, longitude) and altitude
**When** I assign the farm to a region
**Then** the service:
1. Loads all active regions with polygon boundaries
2. For each region with boundary: checks point-in-polygon
3. Verifies farm altitude matches region's altitude band
4. Returns matching `region_id` or falls back to nearest center

### AC 1.10.5: Point-in-Polygon Algorithm

**Given** a GPS coordinate and polygon boundary
**When** I check if point is inside polygon
**Then** the ray casting algorithm:
- Correctly handles points inside, outside, and on boundary
- Works with complex polygons (concave, with holes)
- Returns `True` if odd intersection count, `False` if even

### AC 1.10.6: Backward Compatibility

**Given** existing regions without polygon boundaries
**When** I assign a farm to a region
**Then** the fallback algorithm:
- Matches by altitude band first
- Returns nearest region center by Haversine distance
- No data migration required

---

## Tasks / Subtasks

- [ ] **Task 1: Create RegionBoundary Value Object** (AC: #1)
  - [ ] 1.1 Add `Coordinate` class to `value_objects.py` (lng, lat with validation)
  - [ ] 1.2 Add `PolygonRing` class (list of Coordinates, validates closure)
  - [ ] 1.3 Add `RegionBoundary` class (type="Polygon", validates structure)
  - [ ] 1.4 Unit tests: valid polygon, unclosed polygon, invalid coords, empty rings

- [ ] **Task 2: Extend Geography Value Object** (AC: #2)
  - [ ] 2.1 Add `boundary: RegionBoundary | None = None` to Geography
  - [ ] 2.2 Add `area_km2: float | None = None` (computed by Admin UI via Turf.js, stored here)
  - [ ] 2.3 Add `perimeter_km: float | None = None` (computed by Admin UI via Turf.js, stored here)
  - [ ] 2.4 Unit tests: Geography with/without boundary, backward compat

- [ ] **Task 3: Update Proto Definitions** (AC: #3)
  - [ ] 3.1 Add `Coordinate` message to `plantation.proto`
  - [ ] 3.2 Add `PolygonRing` message with repeated Coordinate
  - [ ] 3.3 Add `RegionBoundary` message with type and rings
  - [ ] 3.4 Update `Geography` message with boundary, area_km2, perimeter_km
  - [ ] 3.5 Run `scripts/proto-gen.sh` to regenerate stubs

- [ ] **Task 4: Implement RegionAssignmentService** (AC: #4, #5, #6)
  - [ ] 4.1 Create `domain/services/region_assignment.py` with service class
  - [ ] 4.2 Implement `_point_in_polygon()` using ray casting algorithm
  - [ ] 4.3 Implement `_altitude_in_band()` for altitude verification
  - [ ] 4.4 Implement `_haversine_distance()` for fallback
  - [ ] 4.5 Implement `assign_region()` with two-tier strategy
  - [ ] 4.6 Unit tests: polygon hit, polygon miss, altitude mismatch, fallback

- [ ] **Task 5: Wire Service into CreateFarmer** (AC: #4)
  - [ ] 5.1 Inject RegionAssignmentService into plantation_service.py
  - [ ] 5.2 Load active regions in CreateFarmer handler
  - [ ] 5.3 Call `assign_region(lat, lng, altitude)` for farmer
  - [ ] 5.4 Remove old `assign_region_from_altitude()` from google_elevation.py

- [ ] **Task 6: Add Proto-to-Pydantic Converters** (AC: #3)
  - [ ] 6.1 Add `_proto_to_region_boundary()` converter
  - [ ] 6.2 Add `_region_boundary_to_proto()` converter
  - [ ] 6.3 Update `_geography_to_proto()` with boundary field
  - [ ] 6.4 Update `_proto_to_geography()` with boundary field

- [ ] **Task 7: Update MCP Tool Descriptions** (if needed)
  - [ ] 7.1 Update `get_region` tool description to mention boundary
  - [ ] 7.2 Verify MCP returns boundary in region responses

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 1.10: GPS Region Assignment with Polygon Boundaries"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/1-10-gps-region-assignment
  ```

**Branch name:** `story/1-10-gps-region-assignment`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/1-10-gps-region-assignment`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 1.10: GPS Region Assignment with Polygon Boundaries" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/1-10-gps-region-assignment`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/plantation/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Pre-flight validation
bash scripts/e2e-preflight.sh

# Run tests
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/1-10-gps-region-assignment

# Wait ~30s, then check CI status
gh run list --branch story/1-10-gps-region-assignment --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Service Architecture

All code modifications are in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── domain/
│   │   ├── models/
│   │   │   └── value_objects.py        # MODIFY - add RegionBoundary, Coordinate
│   │   └── services/
│   │       └── region_assignment.py    # NEW - RegionAssignmentService
│   ├── infrastructure/
│   │   └── google_elevation.py         # MODIFY - remove assign_region_from_altitude()
│   └── api/
│       └── plantation_service.py       # MODIFY - wire in RegionAssignmentService
```

### RegionBoundary Value Object Design

```python
# In libs/fp-common/fp_common/models/value_objects.py

class Coordinate(BaseModel):
    """GeoJSON coordinate pair [longitude, latitude]."""
    longitude: float = Field(ge=-180, le=180, description="Longitude in degrees")
    latitude: float = Field(ge=-90, le=90, description="Latitude in degrees")

class PolygonRing(BaseModel):
    """GeoJSON polygon ring (closed sequence of coordinates)."""
    points: list[Coordinate] = Field(min_length=4)

    @field_validator("points")
    @classmethod
    def validate_closed(cls, v: list[Coordinate]) -> list[Coordinate]:
        if len(v) >= 4:
            first, last = v[0], v[-1]
            if first.longitude != last.longitude or first.latitude != last.latitude:
                raise ValueError("Polygon ring must be closed (first == last)")
        return v

class RegionBoundary(BaseModel):
    """GeoJSON Polygon boundary for precise region definition."""
    type: Literal["Polygon"] = "Polygon"
    rings: list[PolygonRing] = Field(min_length=1)

    @property
    def exterior(self) -> PolygonRing:
        """The exterior ring (first ring)."""
        return self.rings[0]

    @property
    def holes(self) -> list[PolygonRing]:
        """Interior rings (holes), if any."""
        return self.rings[1:]
```

### Geography Extension

```python
# MODIFY existing Geography class
class Geography(BaseModel):
    center_gps: GPS
    radius_km: float = Field(gt=0, le=100)
    altitude_band: AltitudeBand

    # NEW: Optional polygon boundary (takes precedence if provided)
    boundary: RegionBoundary | None = None

    # NEW: Computed values (set by service layer)
    area_km2: float | None = None
    perimeter_km: float | None = None
```

### Proto Definitions

```protobuf
// In proto/plantation/v1/plantation.proto

// GeoJSON coordinate pair (Story 1.10)
message Coordinate {
  double longitude = 1;  // -180 to 180
  double latitude = 2;   // -90 to 90
}

// Closed sequence of coordinates forming a ring (Story 1.10)
message PolygonRing {
  repeated Coordinate points = 1;  // Min 4 points, first == last
}

// GeoJSON Polygon boundary for region definition (Story 1.10)
message RegionBoundary {
  string type = 1;                  // "Polygon"
  repeated PolygonRing rings = 2;   // Exterior ring + optional holes
}

// MODIFY existing Geography message
message Geography {
  GPS center_gps = 1;
  double radius_km = 2;
  AltitudeBand altitude_band = 3;
  RegionBoundary boundary = 4;      // NEW: Optional polygon
  optional double area_km2 = 5;     // NEW: Computed
  optional double perimeter_km = 6; // NEW: Computed
}
```

### RegionAssignmentService Implementation

```python
# services/plantation-model/src/plantation_model/domain/services/region_assignment.py

from fp_common.models.value_objects import RegionBoundary, AltitudeBand, GPS
from plantation_model.domain.models.region import Region
import math

class RegionAssignmentService:
    """Assigns farmers to regions based on GPS coordinates and altitude."""

    def __init__(self, regions: list[Region]):
        """Initialize with list of active regions."""
        self._regions = regions

    def assign_region(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> str | None:
        """
        Assign farm to region using two-tier strategy:
        1. Check polygon boundaries (if available) + altitude band
        2. Fallback to nearest center by altitude band

        Returns region_id or None if no suitable region.
        """
        # Priority 1: Polygon boundaries
        for region in self._regions:
            if region.geography.boundary is not None:
                if self._point_in_polygon(longitude, latitude, region.geography.boundary):
                    if self._altitude_in_band(altitude, region.geography.altitude_band):
                        return region.region_id

        # Priority 2: Fallback to altitude band + nearest center
        altitude_label = self._get_altitude_label(altitude)
        candidates = [
            r for r in self._regions
            if r.geography.altitude_band.label == altitude_label
        ]

        if not candidates:
            return None

        # Find nearest by Haversine distance
        nearest = min(
            candidates,
            key=lambda r: self._haversine_distance(
                latitude, longitude,
                r.geography.center_gps.lat, r.geography.center_gps.lng
            )
        )
        return nearest.region_id

    def _point_in_polygon(
        self,
        lng: float,
        lat: float,
        boundary: RegionBoundary
    ) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        ring = boundary.exterior.points
        n = len(ring)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = ring[i].longitude, ring[i].latitude
            xj, yj = ring[j].longitude, ring[j].latitude

            if ((yi > lat) != (yj > lat)) and \
               (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def _altitude_in_band(self, altitude: float, band: AltitudeBand) -> bool:
        """Check if altitude falls within band."""
        return band.min_meters <= altitude <= band.max_meters

    def _get_altitude_label(self, altitude: float) -> str:
        """Classify altitude into band label."""
        if altitude >= 1800:
            return "highland"
        elif altitude >= 1400:
            return "midland"
        else:
            return "lowland"

    def _haversine_distance(
        self,
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """Calculate great-circle distance in km."""
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
```

### Critical Implementation Rules

**From project-context.md:**

1. **GeoJSON coordinate order:** `[longitude, latitude]` NOT `[lat, lng]`
2. **Polygons must be closed:** First point == last point in each ring
3. **All I/O MUST be async** - But RegionAssignmentService logic is pure (no I/O)
4. **Use Pydantic 2.0 syntax** - `model_dump()`, `Field(ge=..., le=...)`
5. **Backward compatibility** - boundary is optional, fallback always works
6. **Altitude bands:** highland (>=1800m), midland (1400-1800m), lowland (<1400m)

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_region_boundary.py` - Coordinate, PolygonRing, RegionBoundary validation
- `test_geography.py` - Geography with/without boundary
- `test_region_assignment.py` - Point-in-polygon, altitude matching, fallback

**Test Cases for RegionAssignmentService:**
| Test Case | Input | Expected |
|-----------|-------|----------|
| Point inside polygon, altitude matches | Farm in Nyeri Highland | `nyeri-highland` |
| Point inside polygon, altitude mismatch | Farm in Nyeri but lowland altitude | Fallback to `nyeri-lowland` |
| Point outside all polygons | Farm in unmapped area | Fallback to nearest by altitude |
| No regions with polygons | All regions use center only | Fallback works |
| Multiple polygon matches | Overlapping regions | First match wins |

**Edge Cases:**
- Point exactly on polygon boundary (should count as inside)
- Complex concave polygon
- Polygon with holes (interior rings)
- Farm at exactly 1800m altitude (highland threshold)

### Previous Story Patterns (from Story 1.9)

1. **Value objects go in `domain/models/value_objects.py`** - single source of truth
2. **Proto regeneration:** Run `scripts/proto-gen.sh` after updating .proto
3. **Field validation:** Use `Field(ge=..., le=...)` for bounds
4. **Default factory:** Use `default_factory=...` for mutable defaults
5. **Unit test naming:** `test_{class_name}.py`

### Files to Modify/Create

| File | Action | Lines |
|------|--------|-------|
| `libs/fp-common/fp_common/models/value_objects.py` | ADD | ~60 (Coordinate, PolygonRing, RegionBoundary) |
| `libs/fp-common/fp_common/models/value_objects.py` | MODIFY | ~10 (Geography extension) |
| `proto/plantation/v1/plantation.proto` | ADD | ~20 (Coordinate, PolygonRing, RegionBoundary) |
| `proto/plantation/v1/plantation.proto` | MODIFY | ~5 (Geography extension) |
| `services/plantation-model/src/plantation_model/domain/services/region_assignment.py` | NEW | ~120 |
| `services/plantation-model/src/plantation_model/api/plantation_service.py` | MODIFY | ~15 |
| `services/plantation-model/src/plantation_model/infrastructure/google_elevation.py` | REMOVE | ~-65 |
| `tests/unit/plantation/test_region_boundary.py` | NEW | ~80 |
| `tests/unit/plantation/test_region_assignment.py` | NEW | ~100 |

### Project Structure Notes

- **fp-common location:** Value objects that are shared across services go in `libs/fp-common/`
- **Proto location:** `proto/plantation/v1/plantation.proto`
- **Generated stubs:** `libs/fp-proto/src/fp_proto/plantation/v1/`

### References

- [Source: _bmad-output/architecture/adr/ADR-017-map-services-gps-region-assignment.md] - Full architecture decision
- [Source: _bmad-output/epics/epic-1-plantation-model.md#Story 1.10] - Epic story definition
- [Source: _bmad-output/project-context.md] - 176 critical rules
- [Source: _bmad-output/sprint-artifacts/1-8-region-entity-weather-configuration.md] - Previous region story patterns
- [Source: _bmad-output/sprint-artifacts/1-9-payment-policy-configuration.md] - Previous value object patterns
- [Source: services/plantation-model/src/plantation_model/infrastructure/google_elevation.py] - Current assign_region_from_altitude()

---

## Production Code Changes (if any)

If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (fill during implementation) | | | |

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
