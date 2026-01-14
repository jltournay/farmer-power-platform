# ADR-017: Map Services and GPS-Based Region Assignment

**Status:** Accepted
**Date:** 2026-01-14
**Deciders:** Winston (Architect), Jeanlouistournay
**Related Stories:** Epic 9 (Admin Portal), Story 9.2 (Region Management), Story 9.5 (Farmer Management)

## Context

The Farmer Power Platform requires interactive maps for multiple use cases across the Admin Portal:

| Use Case | Screen | Functionality |
|----------|--------|---------------|
| **Region boundary definition** | Region Create/Edit (9.2) | Draw polygons, circles, import GeoJSON |
| **Region visualization** | Region Detail (9.2) | Display boundary with factory/CP markers |
| **Farm location capture** | Farmer Create (9.5) | Click map to get GPS coordinates |
| **Factory location display** | Health Dashboard (9.8) | Show factory markers with status |

### Current State

The Plantation Model currently assigns farmers to regions using **hardcoded bounding boxes**:

```python
# Current implementation in google_elevation.py (lines 78-141)
def assign_region_from_altitude(latitude, longitude, altitude) -> str:
    # Hardcoded rectangular bounds
    if -0.6 <= latitude <= 0.0 and 36.5 <= longitude <= 37.5:
        county = "nyeri"
    elif -0.8 <= latitude <= 0.0 and 35.0 <= longitude <= 36.0:
        county = "kericho"
    # ... more hardcoded boxes ...
```

**Problems with current approach:**
1. Rectangles cannot represent irregular administrative boundaries
2. Overlapping boxes cause incorrect assignments
3. Adding new regions requires code changes
4. No visual feedback for administrators

### Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Draw polygon boundaries on map | P0 | Admin defines region boundaries visually |
| Click-to-get-coordinates | P0 | Capture farm GPS during farmer registration |
| Display markers (factories, CPs) | P0 | Show existing entities on map |
| Import GeoJSON boundaries | P1 | Load official government boundaries |
| Offline capability | P1 | Rural Kenya has unreliable connectivity |
| Satellite/terrain toggle | P2 | Visual reference for boundary drawing |
| Zero/low cost | P0 | Cost-sensitive agricultural platform |

## Decision

### 1. Map Library: Leaflet.js + OpenStreetMap

**Selected: Leaflet.js with OpenStreetMap tiles**

| Component | Choice | Package |
|-----------|--------|---------|
| Map library | Leaflet.js | `leaflet` |
| React wrapper | react-leaflet | `react-leaflet` |
| Tile provider | OpenStreetMap | Free, no API key |
| Drawing tools | Leaflet.draw | `leaflet-draw` |
| Geometry calculations | Turf.js | `@turf/turf` |

### 2. Region Boundary Storage: GeoJSON Polygons

Store boundaries as GeoJSON in the Region model, enabling:
- Standard format compatible with Leaflet export/import
- Point-in-polygon queries for farmer assignment
- Government boundary file imports

### 3. Region Assignment: Point-in-Polygon Algorithm

Replace hardcoded bounding boxes with database-driven polygon matching.

## Alternatives Considered

### Map Library Comparison

| Library | Cost | Offline | Drawing UX | Bundle Size | Verdict |
|---------|------|---------|------------|-------------|---------|
| **Leaflet + OSM** | Free | Excellent | Good (plugin) | ~190KB | **Selected** |
| Mapbox GL JS | $5/1000 loads after 50K | Limited ($$$) | Excellent | ~300KB | Rejected: offline cost |
| MapLibre GL | Free | Good | Moderate | ~220KB | Backup option |
| Google Maps | $7/1000 loads after $200 | **None** | Basic | External | Rejected: no offline |

### Why Leaflet + OpenStreetMap

1. **Zero cost at any scale** - No API fees, no usage tracking
2. **Offline-first** - Tiles cacheable, works in rural Kenya
3. **Proven ecosystem** - 10+ years production use, extensive plugins
4. **Sufficient for admin use** - Not public-facing, limited concurrent users
5. **No vendor lock-in** - Can swap tile providers without code changes

### Why Not Mapbox

Despite superior drawing UX:
- **Offline requires Mapbox Atlas** ($$$) - incompatible with rural deployment
- **Cost scales with usage** - risk for growing platform
- **API key management** - operational overhead

### Why Not Google Maps

- **No offline support** - deal-breaker for rural Kenya
- **Mandatory branding** - less flexibility
- **Higher cost** - $7/1000 loads

## Technical Implementation

### 1. Pydantic Model Changes

**File:** `libs/fp-common/fp_common/models/value_objects.py`

```python
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class RegionBoundary(BaseModel):
    """GeoJSON polygon boundary for precise region definition.

    Compatible with:
    - Leaflet.draw polygon export
    - Government/GIS boundary imports
    - Turf.js point-in-polygon operations

    GeoJSON coordinate order: [longitude, latitude] (not lat/lng!)
    """

    type: Literal["Polygon"] = Field(
        default="Polygon",
        description="GeoJSON geometry type"
    )
    coordinates: list[list[list[float]]] = Field(
        description="GeoJSON Polygon coordinates [[[lng, lat], [lng, lat], ...]]"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_structure(cls, v: list[list[list[float]]]) -> list[list[list[float]]]:
        """Validate GeoJSON polygon structure."""
        if not v or not v[0]:
            raise ValueError("Polygon must have at least one ring")

        ring = v[0]  # Exterior ring
        if len(ring) < 4:
            raise ValueError("Polygon ring must have at least 4 points (closed)")

        # Validate ring is closed (first == last)
        if ring[0] != ring[-1]:
            raise ValueError("Polygon ring must be closed (first point == last point)")

        # Validate each coordinate is [lng, lat]
        for point in ring:
            if len(point) != 2:
                raise ValueError("Each coordinate must be [longitude, latitude]")
            lng, lat = point
            if not (-180 <= lng <= 180):
                raise ValueError(f"Longitude {lng} out of range [-180, 180]")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} out of range [-90, 90]")

        return v

    def to_geojson_geometry(self) -> dict:
        """Export as GeoJSON geometry object."""
        return {"type": self.type, "coordinates": self.coordinates}


# MODIFY existing Geography class
class Geography(BaseModel):
    """Geographic definition of a region.

    Supports two boundary modes:
    1. Simple circle: center_gps + radius_km (legacy/MVP)
    2. Polygon boundary: GeoJSON polygon for precise boundaries (Epic 9)

    If boundary is provided, it takes precedence for region assignment.
    center_gps and radius_km are always required for backward compatibility
    and serve as fallback/approximate values.
    """

    center_gps: GPS = Field(description="Center point of the region")
    radius_km: float = Field(gt=0, le=100, description="Radius of region coverage in km")
    altitude_band: AltitudeBand = Field(description="Altitude band classification")

    # NEW: Optional polygon boundary (Epic 9)
    boundary: RegionBoundary | None = Field(
        default=None,
        description="GeoJSON polygon boundary (used for precise region assignment)"
    )

    # NEW: Computed fields from boundary (set by service layer)
    area_km2: float | None = Field(
        default=None,
        description="Area in km² (auto-calculated from boundary)"
    )
    perimeter_km: float | None = Field(
        default=None,
        description="Perimeter in km (auto-calculated from boundary)"
    )
```

### 2. Proto Definition Changes

**File:** `proto/plantation/v1/plantation.proto`

```protobuf
// NEW: GeoJSON polygon boundary for regions
message RegionBoundary {
    // GeoJSON type - always "Polygon"
    string type = 1;

    // Polygon rings - exterior ring followed by optional holes
    // Each ring is a list of coordinates, each coordinate is [lng, lat]
    repeated PolygonRing rings = 2;
}

message PolygonRing {
    repeated Coordinate points = 1;
}

message Coordinate {
    double longitude = 1;
    double latitude = 2;
}

// MODIFY: Geography message
message Geography {
    GPS center_gps = 1;
    double radius_km = 2;
    AltitudeBand altitude_band = 3;

    // NEW: Optional polygon boundary
    RegionBoundary boundary = 4;

    // NEW: Computed boundary stats
    optional double area_km2 = 5;
    optional double perimeter_km = 6;
}
```

### 3. Region Assignment Service

**File:** `services/plantation-model/src/plantation_model/domain/region_assignment.py` (NEW)

```python
"""Region assignment service using polygon boundaries.

Replaces hardcoded bounding boxes with database-driven polygon matching.
Google Elevation API remains unchanged - it only provides altitude data.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fp_common.models.region import Region
    from fp_common.models.value_objects import AltitudeBand, RegionBoundary

logger = logging.getLogger(__name__)


class RegionAssignmentService:
    """Assigns farmers to regions based on GPS coordinates and altitude.

    Algorithm:
    1. For each region with a polygon boundary:
       - Check if farm GPS is inside the polygon (point-in-polygon)
       - Verify farm altitude matches region's altitude band
    2. If no polygon match, fall back to nearest region center by altitude band

    Note: Google Elevation API (separate service) provides the altitude.
    This service only handles the region matching logic.
    """

    def __init__(self, regions: list["Region"]) -> None:
        """Initialize with list of active regions.

        Args:
            regions: List of Region entities with boundaries loaded from database.
        """
        self._regions = [r for r in regions if r.is_active]
        self._regions_with_boundary = [r for r in self._regions if r.geography.boundary]
        logger.info(
            "RegionAssignmentService initialized: %d active regions, %d with polygon boundaries",
            len(self._regions),
            len(self._regions_with_boundary)
        )

    def assign_region(
        self,
        latitude: float,
        longitude: float,
        altitude: float
    ) -> str | None:
        """Assign a farm to a region based on location.

        Args:
            latitude: Farm latitude in decimal degrees.
            longitude: Farm longitude in decimal degrees.
            altitude: Farm altitude in meters (from Google Elevation API).

        Returns:
            region_id if matched, None if no suitable region found.
        """
        # Priority 1: Check polygon boundaries
        for region in self._regions_with_boundary:
            if self._point_in_polygon(longitude, latitude, region.geography.boundary):
                if self._altitude_in_band(altitude, region.geography.altitude_band):
                    logger.debug(
                        "Matched region '%s' via polygon boundary for (%.4f, %.4f) at %.0fm",
                        region.region_id, latitude, longitude, altitude
                    )
                    return region.region_id
                else:
                    logger.debug(
                        "Point inside '%s' boundary but altitude %.0fm outside band %s",
                        region.region_id, altitude, region.geography.altitude_band.label.value
                    )

        # Priority 2: Fallback to altitude band + nearest center
        target_band = self._determine_altitude_band(altitude)
        matching_regions = [
            r for r in self._regions
            if r.geography.altitude_band.label.value == target_band
        ]

        if matching_regions:
            nearest = min(
                matching_regions,
                key=lambda r: self._haversine_distance(
                    latitude, longitude,
                    r.geography.center_gps.lat, r.geography.center_gps.lng
                )
            )
            logger.debug(
                "Matched region '%s' via altitude band fallback for (%.4f, %.4f)",
                nearest.region_id, latitude, longitude
            )
            return nearest.region_id

        logger.warning(
            "No region match for coordinates (%.4f, %.4f) at altitude %.0fm",
            latitude, longitude, altitude
        )
        return None

    def _point_in_polygon(
        self,
        lng: float,
        lat: float,
        boundary: "RegionBoundary"
    ) -> bool:
        """Ray casting algorithm for point-in-polygon test.

        Counts intersections of a horizontal ray from the point
        to infinity with polygon edges. Odd count = inside.
        """
        ring = boundary.coordinates[0]  # Exterior ring
        n = len(ring)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]  # lng, lat
            xj, yj = ring[j][0], ring[j][1]

            if ((yi > lat) != (yj > lat)) and \
               (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def _altitude_in_band(self, altitude: float, band: "AltitudeBand") -> bool:
        """Check if altitude falls within the band's range."""
        return band.min_meters <= altitude <= band.max_meters

    def _determine_altitude_band(self, altitude: float) -> str:
        """Determine altitude band label from meters."""
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
        """Calculate distance between two points in km (Haversine formula)."""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in km

        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c
```

### 4. React Implementation

#### 4.1 Package Installation

```bash
npm install leaflet react-leaflet leaflet-draw @turf/turf
npm install -D @types/leaflet @types/leaflet-draw
```

#### 4.2 Display a Map with Point Marker

**Use case:** Show factory/CP location, display farm location

```typescript
// components/MapDisplay.tsx
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default icon issue with bundlers
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

interface MapDisplayProps {
  center: { lat: number; lng: number };
  zoom?: number;
  markers?: Array<{
    position: { lat: number; lng: number };
    label: string;
    type?: 'factory' | 'collection-point' | 'farmer';
  }>;
}

export function MapDisplay({ center, zoom = 13, markers = [] }: MapDisplayProps) {
  return (
    <MapContainer
      center={[center.lat, center.lng]}
      zoom={zoom}
      style={{ height: '400px', width: '100%' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((marker, idx) => (
        <Marker key={idx} position={[marker.position.lat, marker.position.lng]}>
          <Popup>{marker.label}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
```

#### 4.3 Click Map to Get GPS Coordinates

**Use case:** Farmer registration - click to capture farm location

```typescript
// components/LocationPicker.tsx
import { useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface Coordinates {
  latitude: number;
  longitude: number;
}

interface LocationPickerProps {
  initialPosition?: Coordinates;
  onLocationSelect: (coords: Coordinates) => void;
}

// Inner component to handle map click events
function MapClickHandler({
  onLocationSelect
}: {
  onLocationSelect: (coords: Coordinates) => void
}) {
  useMapEvents({
    click: (e) => {
      onLocationSelect({
        latitude: e.latlng.lat,
        longitude: e.latlng.lng,
      });
    },
  });
  return null;
}

export function LocationPicker({
  initialPosition,
  onLocationSelect
}: LocationPickerProps) {
  const [selectedPosition, setSelectedPosition] = useState<Coordinates | null>(
    initialPosition || null
  );

  // Default center: Nyeri, Kenya (tea region)
  const defaultCenter = { lat: -0.4197, lng: 36.9553 };
  const center = selectedPosition
    ? { lat: selectedPosition.latitude, lng: selectedPosition.longitude }
    : defaultCenter;

  const handleLocationSelect = useCallback((coords: Coordinates) => {
    setSelectedPosition(coords);
    onLocationSelect(coords);
  }, [onLocationSelect]);

  return (
    <div>
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={13}
        style={{ height: '300px', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onLocationSelect={handleLocationSelect} />
        {selectedPosition && (
          <Marker position={[selectedPosition.latitude, selectedPosition.longitude]} />
        )}
      </MapContainer>

      {selectedPosition && (
        <div style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
          Selected: {selectedPosition.latitude.toFixed(6)}, {selectedPosition.longitude.toFixed(6)}
        </div>
      )}

      <p style={{ marginTop: '4px', fontSize: '12px', color: '#888' }}>
        Click on the map to set farm location
      </p>
    </div>
  );
}

// Usage in Farmer Create form:
// <LocationPicker
//   onLocationSelect={(coords) => {
//     setValue('farm_location.latitude', coords.latitude);
//     setValue('farm_location.longitude', coords.longitude);
//   }}
// />
```

#### 4.3b GPS Field with Map Assist (Two-Way Binding)

**Use case:** Admin forms (Factory, Collection Point, Farmer) where users can EITHER type GPS manually OR click on map. The map is collapsible and acts as an optional assist.

```typescript
// components/GPSFieldWithMapAssist.tsx
import { useState, useCallback, useEffect } from 'react';
import { TextField, Button, Collapse, Box, IconButton, Typography } from '@mui/material';
import { Map as MapIcon, Close as CloseIcon } from '@mui/icons-material';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface GPSFieldWithMapAssistProps {
  latitude: number | null;
  longitude: number | null;
  onLatitudeChange: (lat: number | null) => void;
  onLongitudeChange: (lng: number | null) => void;
  latitudeError?: string;
  longitudeError?: string;
  disabled?: boolean;
}

// Component to handle map click and center updates
function MapEventHandler({
  onLocationSelect,
  externalPosition,
}: {
  onLocationSelect: (lat: number, lng: number) => void;
  externalPosition: { lat: number; lng: number } | null;
}) {
  const map = useMap();

  // Center map when external position changes (user typed coordinates)
  useEffect(() => {
    if (externalPosition) {
      map.setView([externalPosition.lat, externalPosition.lng], map.getZoom());
    }
  }, [externalPosition, map]);

  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });

  return null;
}

export function GPSFieldWithMapAssist({
  latitude,
  longitude,
  onLatitudeChange,
  onLongitudeChange,
  latitudeError,
  longitudeError,
  disabled = false,
}: GPSFieldWithMapAssistProps) {
  const [mapOpen, setMapOpen] = useState(false);

  // Default center: Nyeri, Kenya
  const defaultCenter = { lat: -0.4197, lng: 36.9553 };

  const currentPosition =
    latitude !== null && longitude !== null
      ? { lat: latitude, lng: longitude }
      : null;

  const mapCenter = currentPosition || defaultCenter;

  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      onLatitudeChange(parseFloat(lat.toFixed(6)));
      onLongitudeChange(parseFloat(lng.toFixed(6)));
    },
    [onLatitudeChange, onLongitudeChange]
  );

  const handleLatitudeInput = (value: string) => {
    const parsed = parseFloat(value);
    if (!isNaN(parsed) && parsed >= -90 && parsed <= 90) {
      onLatitudeChange(parsed);
    } else if (value === '' || value === '-') {
      onLatitudeChange(null);
    }
  };

  const handleLongitudeInput = (value: string) => {
    const parsed = parseFloat(value);
    if (!isNaN(parsed) && parsed >= -180 && parsed <= 180) {
      onLongitudeChange(parsed);
    } else if (value === '' || value === '-') {
      onLongitudeChange(null);
    }
  };

  return (
    <Box>
      {/* GPS Text Fields */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          label="Latitude"
          value={latitude ?? ''}
          onChange={(e) => handleLatitudeInput(e.target.value)}
          error={!!latitudeError}
          helperText={latitudeError}
          disabled={disabled}
          size="small"
          sx={{ flex: 1 }}
          placeholder="-0.4197"
        />
        <TextField
          label="Longitude"
          value={longitude ?? ''}
          onChange={(e) => handleLongitudeInput(e.target.value)}
          error={!!longitudeError}
          helperText={longitudeError}
          disabled={disabled}
          size="small"
          sx={{ flex: 1 }}
          placeholder="36.9553"
        />
        <Button
          variant="outlined"
          size="small"
          startIcon={<MapIcon />}
          onClick={() => setMapOpen(!mapOpen)}
          disabled={disabled}
          sx={{ whiteSpace: 'nowrap' }}
        >
          {mapOpen ? 'Hide Map' : 'Select on Map'}
        </Button>
      </Box>

      {/* Collapsible Map */}
      <Collapse in={mapOpen}>
        <Box sx={{ mt: 2, position: 'relative' }}>
          <IconButton
            size="small"
            onClick={() => setMapOpen(false)}
            sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1000, bgcolor: 'white' }}
          >
            <CloseIcon />
          </IconButton>

          <MapContainer
            center={[mapCenter.lat, mapCenter.lng]}
            zoom={13}
            style={{ height: '250px', width: '100%', borderRadius: '4px' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapEventHandler
              onLocationSelect={handleMapClick}
              externalPosition={currentPosition}
            />
            {currentPosition && (
              <Marker position={[currentPosition.lat, currentPosition.lng]} />
            )}
          </MapContainer>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Click on the map to set location, or type coordinates above. Changes sync both ways.
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
}

// Usage in Factory/Farmer/CP forms:
// <GPSFieldWithMapAssist
//   latitude={watch('location.latitude')}
//   longitude={watch('location.longitude')}
//   onLatitudeChange={(lat) => setValue('location.latitude', lat)}
//   onLongitudeChange={(lng) => setValue('location.longitude', lng)}
//   latitudeError={errors.location?.latitude?.message}
//   longitudeError={errors.location?.longitude?.message}
// />
```

**Key Features:**
- **Two-way sync**: Map ↔ Text fields stay synchronized
- **Collapsible map**: Doesn't clutter the form when not needed
- **Manual entry preserved**: Users can always type coordinates directly
- **Validation-friendly**: Works with form validation (react-hook-form)
- **Accessible**: Keyboard-navigable text fields as primary input

#### 4.4 Draw Polygon for Region Boundary

**Use case:** Region creation - draw boundary polygon

```typescript
// components/BoundaryDrawer.tsx
import { useRef, useEffect, useState } from 'react';
import { MapContainer, TileLayer, FeatureGroup, Marker } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import * as turf from '@turf/turf';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface BoundaryStats {
  area_km2: number;
  perimeter_km: number;
  centroid: { lat: number; lng: number };
}

interface BoundaryDrawerProps {
  existingBoundary?: GeoJSONPolygon;
  existingMarkers?: Array<{
    position: { lat: number; lng: number };
    label: string;
    icon: 'factory' | 'collection-point';
  }>;
  onBoundaryChange: (boundary: GeoJSONPolygon | null, stats: BoundaryStats | null) => void;
}

export function BoundaryDrawer({
  existingBoundary,
  existingMarkers = [],
  onBoundaryChange,
}: BoundaryDrawerProps) {
  const featureGroupRef = useRef<L.FeatureGroup>(null);
  const [stats, setStats] = useState<BoundaryStats | null>(null);

  // Load existing boundary on mount
  useEffect(() => {
    if (existingBoundary && featureGroupRef.current) {
      const layer = L.geoJSON({
        type: 'Feature',
        geometry: existingBoundary,
        properties: {},
      });
      featureGroupRef.current.addLayer(layer);
      calculateStats(existingBoundary);
    }
  }, [existingBoundary]);

  const calculateStats = (geojson: GeoJSONPolygon): BoundaryStats => {
    const polygon = turf.polygon(geojson.coordinates);
    const area = turf.area(polygon) / 1_000_000; // m² to km²
    const perimeter = turf.length(turf.polygonToLine(polygon), { units: 'kilometers' });
    const centroidPoint = turf.centroid(polygon);

    const calculatedStats: BoundaryStats = {
      area_km2: Math.round(area * 100) / 100,
      perimeter_km: Math.round(perimeter * 100) / 100,
      centroid: {
        lng: centroidPoint.geometry.coordinates[0],
        lat: centroidPoint.geometry.coordinates[1],
      },
    };

    setStats(calculatedStats);
    return calculatedStats;
  };

  const handleCreated = (e: L.DrawEvents.Created) => {
    const layer = e.layer as L.Polygon;
    const geojson = layer.toGeoJSON();
    const boundary: GeoJSONPolygon = {
      type: 'Polygon',
      coordinates: geojson.geometry.coordinates as number[][][],
    };

    const newStats = calculateStats(boundary);
    onBoundaryChange(boundary, newStats);
  };

  const handleEdited = (e: L.DrawEvents.Edited) => {
    const layers = e.layers;
    layers.eachLayer((layer) => {
      if (layer instanceof L.Polygon) {
        const geojson = layer.toGeoJSON();
        const boundary: GeoJSONPolygon = {
          type: 'Polygon',
          coordinates: geojson.geometry.coordinates as number[][][],
        };

        const newStats = calculateStats(boundary);
        onBoundaryChange(boundary, newStats);
      }
    });
  };

  const handleDeleted = () => {
    setStats(null);
    onBoundaryChange(null, null);
  };

  // Default center: Nyeri, Kenya
  const defaultCenter: [number, number] = [-0.4197, 36.9553];

  return (
    <div>
      <MapContainer
        center={defaultCenter}
        zoom={10}
        style={{ height: '500px', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Existing factories/CPs as reference markers */}
        {existingMarkers.map((marker, idx) => (
          <Marker
            key={idx}
            position={[marker.position.lat, marker.position.lng]}
            title={marker.label}
          />
        ))}

        <FeatureGroup ref={featureGroupRef}>
          <EditControl
            position="topright"
            onCreated={handleCreated}
            onEdited={handleEdited}
            onDeleted={handleDeleted}
            draw={{
              polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: {
                  color: '#1B4332', // Forest Green (brand color)
                  fillOpacity: 0.2,
                },
              },
              circle: {
                shapeOptions: {
                  color: '#1B4332',
                  fillOpacity: 0.2,
                },
              },
              // Disable other shapes
              rectangle: false,
              polyline: false,
              marker: false,
              circlemarker: false,
            }}
            edit={{
              edit: true,
              remove: true,
            }}
          />
        </FeatureGroup>
      </MapContainer>

      {/* Boundary Stats Display */}
      {stats && (
        <div style={{
          marginTop: '12px',
          padding: '12px',
          backgroundColor: '#f5f5f5',
          borderRadius: '4px',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '16px',
        }}>
          <div>
            <div style={{ fontSize: '12px', color: '#666' }}>Area</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{stats.area_km2} km²</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#666' }}>Perimeter</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{stats.perimeter_km} km</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#666' }}>Centroid</div>
            <div style={{ fontSize: '14px' }}>
              {stats.centroid.lat.toFixed(4)}, {stats.centroid.lng.toFixed(4)}
            </div>
          </div>
        </div>
      )}

      <p style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
        Click points on the map to draw boundary. Double-click to complete.
        Drag vertices to adjust. Use the trash icon to clear.
      </p>
    </div>
  );
}

// Usage in Region Create form:
// <BoundaryDrawer
//   existingMarkers={factories.map(f => ({
//     position: { lat: f.location.latitude, lng: f.location.longitude },
//     label: f.name,
//     icon: 'factory',
//   }))}
//   onBoundaryChange={(boundary, stats) => {
//     if (boundary) {
//       setValue('geography.boundary', boundary);
//       setValue('geography.area_km2', stats.area_km2);
//       setValue('geography.perimeter_km', stats.perimeter_km);
//       setValue('geography.center_gps', stats.centroid);
//     }
//   }}
// />
```

#### 4.5 Import GeoJSON Boundary File

**Use case:** Import official government boundaries

```typescript
// components/GeoJSONImporter.tsx
import { useCallback } from 'react';
import { Button } from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface GeoJSONImporterProps {
  onImport: (boundary: GeoJSONPolygon) => void;
  onError: (message: string) => void;
}

export function GeoJSONImporter({ onImport, onError }: GeoJSONImporterProps) {
  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const geojson = JSON.parse(text);

        // Handle both Feature and Geometry formats
        let geometry = geojson;
        if (geojson.type === 'Feature') {
          geometry = geojson.geometry;
        } else if (geojson.type === 'FeatureCollection') {
          // Take first feature
          if (geojson.features?.length > 0) {
            geometry = geojson.features[0].geometry;
          } else {
            throw new Error('FeatureCollection is empty');
          }
        }

        if (geometry.type !== 'Polygon' && geometry.type !== 'MultiPolygon') {
          throw new Error(`Expected Polygon, got ${geometry.type}`);
        }

        // Convert MultiPolygon to Polygon (take first polygon)
        const polygon: GeoJSONPolygon = {
          type: 'Polygon',
          coordinates:
            geometry.type === 'MultiPolygon'
              ? geometry.coordinates[0]
              : geometry.coordinates,
        };

        // Validate structure
        if (!polygon.coordinates?.[0]?.length) {
          throw new Error('Invalid polygon structure');
        }

        onImport(polygon);
      } catch (err) {
        onError(err instanceof Error ? err.message : 'Failed to parse GeoJSON file');
      }

      // Reset input
      event.target.value = '';
    },
    [onImport, onError]
  );

  return (
    <Button
      component="label"
      variant="outlined"
      startIcon={<UploadIcon />}
      size="small"
    >
      Import GeoJSON
      <input
        type="file"
        accept=".json,.geojson"
        onChange={handleFileChange}
        hidden
      />
    </Button>
  );
}
```

### 5. Service Layer Changes

**File:** `services/plantation-model/src/plantation_model/api/plantation_service.py`

Modify `CreateFarmer` to use the new `RegionAssignmentService`:

```python
# In CreateFarmer RPC handler

async def CreateFarmer(self, request: CreateFarmerRequest, context) -> Farmer:
    # ... existing validation ...

    # Fetch altitude from Google Elevation API (UNCHANGED)
    altitude = await self._elevation_client.get_altitude(
        request.farm_location.latitude,
        request.farm_location.longitude
    )
    if altitude is None:
        altitude = 1500  # Default if API unavailable

    # NEW: Use RegionAssignmentService instead of assign_region_from_altitude()
    regions = await self._region_repo.list_active()
    assignment_service = RegionAssignmentService(regions)
    region_id = assignment_service.assign_region(
        latitude=request.farm_location.latitude,
        longitude=request.farm_location.longitude,
        altitude=altitude
    )

    if not region_id:
        raise ValueError(
            f"No region found for coordinates ({request.farm_location.latitude}, "
            f"{request.farm_location.longitude}) at altitude {altitude}m"
        )

    # ... rest of farmer creation ...
```

## Consequences

### Positive

- **Zero ongoing costs** for map tiles and services
- **Offline capability** critical for rural Kenya deployment
- **Admin-controlled boundaries** no code changes to add regions
- **Standard GeoJSON format** compatible with government data imports
- **Visual feedback** admins see exactly what they're defining
- **Accurate farmer assignment** polygon beats rectangular approximation

### Negative

- **OSM tile appearance** less polished than Mapbox (acceptable for admin tool)
- **Drawing UX** requires Leaflet.draw plugin (proven but not as smooth as Mapbox)
- **Bundle size increase** ~200KB for Leaflet + plugins

### Mitigations

| Risk | Mitigation |
|------|------------|
| OSM tiles too basic | Can swap to Stadia or CartoDB tiles (free, better styling) |
| Drawing complexity | Provide clear instructions, import option for complex boundaries |
| Offline tile caching | Use service worker to cache tiles for common zoom levels |

## File Changes Summary

| File | Change Type | Lines |
|------|-------------|-------|
| `libs/fp-common/fp_common/models/value_objects.py` | ADD `RegionBoundary`, MODIFY `Geography` | ~60 |
| `proto/plantation/v1/plantation.proto` | ADD `RegionBoundary`, `Coordinate`, MODIFY `Geography` | ~20 |
| `services/plantation-model/src/plantation_model/domain/region_assignment.py` | NEW file | ~120 |
| `services/plantation-model/src/plantation_model/api/plantation_service.py` | MODIFY `CreateFarmer` | ~15 |
| `services/plantation-model/src/plantation_model/infrastructure/google_elevation.py` | REMOVE `assign_region_from_altitude()` | -65 |

## Migration Strategy

1. **No data migration required** - `boundary` field is optional
2. **Backward compatible** - existing regions work with fallback algorithm
3. **Gradual adoption** - admins add boundaries via Epic 9 UI over time
4. **Fallback preserved** - altitude-band matching still works for regions without boundaries

## References

- [Leaflet Documentation](https://leafletjs.com/)
- [react-leaflet Documentation](https://react-leaflet.js.org/)
- [Leaflet.draw Plugin](https://leaflet.github.io/Leaflet.draw/docs/leaflet-draw-latest.html)
- [Turf.js Documentation](https://turfjs.org/)
- [GeoJSON Specification (RFC 7946)](https://tools.ietf.org/html/rfc7946)
- Epic 9: Admin Portal
- Story 9.2: Region Management
- Story 9.5: Farmer Management
