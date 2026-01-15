/**
 * BoundaryDrawer Component
 *
 * Leaflet.draw polygon/circle drawing with area/perimeter stats.
 * Used for region boundary management (per ADR-017).
 *
 * IMPORTANT: Consuming application must import Leaflet CSS:
 * import 'leaflet/dist/leaflet.css';
 * import 'leaflet-draw/dist/leaflet.draw.css';
 *
 * Accessibility:
 * - Keyboard accessible drawing controls
 * - Clear visual feedback for drawn shapes
 * - Stats displayed with accessible formatting
 */

import { useRef, useEffect, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  FeatureGroup,
  useMap,
  Marker,
  Popup,
} from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import * as turf from '@turf/turf';
import { Box, Typography, Paper, useTheme, Divider } from '@mui/material';

// Fix for default marker icon issue in webpack/vite
// @ts-expect-error - Leaflet default icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/** GeoJSON Polygon type for boundary data */
export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

/** Marker for display on the map */
export interface BoundaryMapMarker {
  id: string;
  lat: number;
  lng: number;
  title?: string;
}

/** Boundary statistics */
export interface BoundaryStats {
  /** Area in square kilometers */
  areaKm2: number;
  /** Perimeter in kilometers */
  perimeterKm: number;
  /** Centroid coordinates */
  centroid: { lat: number; lng: number };
}

/** BoundaryDrawer component props */
export interface BoundaryDrawerProps {
  /** Existing boundary to display and edit */
  existingBoundary?: GeoJSONPolygon;
  /** Existing markers to display (e.g., collection points) */
  existingMarkers?: BoundaryMapMarker[];
  /** Callback when boundary changes */
  onBoundaryChange: (
    boundary: GeoJSONPolygon | null,
    stats: BoundaryStats | null
  ) => void;
  /** Map height */
  height?: number | string;
  /** Default map center (used when no boundary exists) */
  defaultCenter?: { lat: number; lng: number };
  /** Default zoom level */
  defaultZoom?: number;
  /** Whether editing is disabled */
  disabled?: boolean;
}

/**
 * Helper to convert Leaflet polygon layer to GeoJSON.
 */
function layerToGeoJSON(layer: L.Polygon): GeoJSONPolygon {
  const geoJson = layer.toGeoJSON();
  return {
    type: 'Polygon',
    coordinates: geoJson.geometry.coordinates as number[][][],
  };
}

/**
 * Calculate statistics for a polygon.
 */
function calculateStats(polygon: GeoJSONPolygon): BoundaryStats {
  const turfPolygon = turf.polygon(polygon.coordinates);
  const area = turf.area(turfPolygon) / 1_000_000; // m² to km²
  const length = turf.length(turfPolygon, { units: 'kilometers' });
  const centroid = turf.centroid(turfPolygon);
  const centroidCoords = centroid.geometry.coordinates;

  return {
    areaKm2: parseFloat(area.toFixed(4)),
    perimeterKm: parseFloat(length.toFixed(4)),
    centroid: {
      lat: centroidCoords[1] ?? 0,
      lng: centroidCoords[0] ?? 0,
    },
  };
}

/**
 * Helper component to fit map to boundary.
 */
function FitToBoundary({
  boundary,
  defaultCenter,
  defaultZoom,
}: {
  boundary?: GeoJSONPolygon;
  defaultCenter: { lat: number; lng: number };
  defaultZoom: number;
}): null {
  const map = useMap();

  useEffect(() => {
    const firstRing = boundary?.coordinates[0];
    if (boundary && firstRing && firstRing.length > 0) {
      const coords = firstRing.map(
        (coord) => [coord[1], coord[0]] as [number, number]
      );
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    } else {
      map.setView([defaultCenter.lat, defaultCenter.lng], defaultZoom);
    }
  }, [map, boundary, defaultCenter, defaultZoom]);

  return null;
}

/**
 * Helper component to load existing boundary into FeatureGroup.
 */
function LoadExistingBoundary({
  boundary,
  featureGroupRef,
}: {
  boundary?: GeoJSONPolygon;
  featureGroupRef: React.RefObject<L.FeatureGroup | null>;
}): null {
  const map = useMap();

  useEffect(() => {
    const fg = featureGroupRef.current;
    if (!fg) return;

    // Clear existing layers
    fg.clearLayers();

    // Add existing boundary if present
    const firstRing = boundary?.coordinates[0];
    if (boundary && firstRing && firstRing.length > 0) {
      const coords = firstRing.map(
        (coord) => [coord[1], coord[0]] as [number, number]
      );
      const polygon = L.polygon(coords, {
        color: '#1B4332',
        fillColor: '#1B4332',
        fillOpacity: 0.2,
        weight: 2,
      });
      fg.addLayer(polygon);
    }
  }, [boundary, featureGroupRef, map]);

  return null;
}

/**
 * BoundaryDrawer provides polygon drawing for region boundaries.
 *
 * @example
 * ```tsx
 * // In your app entry point:
 * import 'leaflet/dist/leaflet.css';
 * import 'leaflet-draw/dist/leaflet.draw.css';
 *
 * // Then use the component:
 * <BoundaryDrawer
 *   existingBoundary={region.boundary}
 *   existingMarkers={collectionPoints}
 *   onBoundaryChange={(boundary, stats) => {
 *     setRegion({ ...region, boundary, area_km2: stats?.areaKm2 });
 *   }}
 * />
 * ```
 */
export function BoundaryDrawer({
  existingBoundary,
  existingMarkers = [],
  onBoundaryChange,
  height = 500,
  defaultCenter = { lat: -1.2921, lng: 36.8219 }, // Nairobi
  defaultZoom = 8,
  disabled = false,
}: BoundaryDrawerProps): JSX.Element {
  const theme = useTheme();
  const featureGroupRef = useRef<L.FeatureGroup | null>(null);

  // Calculate current stats
  const currentStats = existingBoundary ? calculateStats(existingBoundary) : null;

  const handleCreated = useCallback(
    (e: L.DrawEvents.Created) => {
      const layer = e.layer as L.Polygon;
      const fg = featureGroupRef.current;

      if (fg) {
        // Clear any existing shapes (only allow one boundary)
        fg.clearLayers();
        fg.addLayer(layer);
      }

      const geoJson = layerToGeoJSON(layer);
      const stats = calculateStats(geoJson);
      onBoundaryChange(geoJson, stats);
    },
    [onBoundaryChange]
  );

  const handleEdited = useCallback(
    (e: L.DrawEvents.Edited) => {
      const layers = e.layers;
      layers.eachLayer((layer) => {
        if (layer instanceof L.Polygon) {
          const geoJson = layerToGeoJSON(layer);
          const stats = calculateStats(geoJson);
          onBoundaryChange(geoJson, stats);
        }
      });
    },
    [onBoundaryChange]
  );

  const handleDeleted = useCallback(() => {
    onBoundaryChange(null, null);
  }, [onBoundaryChange]);

  return (
    <Box>
      <Box
        sx={{
          height,
          width: '100%',
          borderRadius: 1,
          overflow: 'hidden',
          border: `1px solid ${theme.palette.divider}`,
          opacity: disabled ? 0.6 : 1,
          pointerEvents: disabled ? 'none' : 'auto',
        }}
      >
        <MapContainer
          center={[defaultCenter.lat, defaultCenter.lng]}
          zoom={defaultZoom}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />

          <FitToBoundary
            boundary={existingBoundary}
            defaultCenter={defaultCenter}
            defaultZoom={defaultZoom}
          />

          <FeatureGroup
            ref={featureGroupRef as React.RefObject<L.FeatureGroup>}
          >
            {!disabled && (
              <EditControl
                position="topright"
                onCreated={handleCreated}
                onEdited={handleEdited}
                onDeleted={handleDeleted}
                draw={{
                  polygon: {
                    allowIntersection: false,
                    shapeOptions: {
                      color: '#1B4332',
                      fillColor: '#1B4332',
                      fillOpacity: 0.2,
                      weight: 2,
                    },
                  },
                  circle: false,
                  circlemarker: false,
                  marker: false,
                  polyline: false,
                  rectangle: false,
                }}
                edit={{
                  remove: true,
                }}
              />
            )}
            <LoadExistingBoundary
              boundary={existingBoundary}
              featureGroupRef={featureGroupRef}
            />
          </FeatureGroup>

          {/* Existing markers */}
          {existingMarkers.map((marker) => (
            <Marker key={marker.id} position={[marker.lat, marker.lng]}>
              {marker.title && (
                <Popup>
                  <Typography variant="subtitle2">{marker.title}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {marker.lat.toFixed(6)}, {marker.lng.toFixed(6)}
                  </Typography>
                </Popup>
              )}
            </Marker>
          ))}
        </MapContainer>
      </Box>

      {/* Stats display */}
      {currentStats && (
        <Paper
          variant="outlined"
          sx={{
            mt: 2,
            p: 2,
            display: 'flex',
            gap: 3,
            flexWrap: 'wrap',
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary">
              Area
            </Typography>
            <Typography variant="h6" component="div" aria-label="Boundary area">
              {currentStats.areaKm2} km²
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box>
            <Typography variant="caption" color="text.secondary">
              Perimeter
            </Typography>
            <Typography
              variant="h6"
              component="div"
              aria-label="Boundary perimeter"
            >
              {currentStats.perimeterKm} km
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box>
            <Typography variant="caption" color="text.secondary">
              Centroid
            </Typography>
            <Typography
              variant="body2"
              component="div"
              aria-label="Boundary centroid"
            >
              {currentStats.centroid.lat.toFixed(6)},{' '}
              {currentStats.centroid.lng.toFixed(6)}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* Help text */}
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
        {disabled
          ? 'Editing is disabled'
          : 'Use the polygon tool in the top-right to draw a region boundary'}
      </Typography>
    </Box>
  );
}

export default BoundaryDrawer;
