/**
 * MapDisplay Component
 *
 * Read-only Leaflet map with markers.
 * Used for displaying locations on a map.
 *
 * IMPORTANT: Consuming application must import Leaflet CSS:
 * import 'leaflet/dist/leaflet.css';
 *
 * Accessibility:
 * - Interactive map elements keyboard accessible
 * - Markers have accessible labels
 */

import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Box, Typography, useTheme } from '@mui/material';

// Fix for default marker icon issue in webpack/vite
// @ts-expect-error - Leaflet default icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/** Marker definition */
export interface MapMarker {
  /** Unique identifier */
  id: string;
  /** Latitude */
  lat: number;
  /** Longitude */
  lng: number;
  /** Marker title/label */
  title?: string;
  /** Popup content */
  popupContent?: React.ReactNode;
  /** Custom icon URL */
  iconUrl?: string;
}

/** MapDisplay component props */
export interface MapDisplayProps {
  /** Map markers */
  markers?: MapMarker[];
  /** Map center latitude */
  centerLat?: number;
  /** Map center longitude */
  centerLng?: number;
  /** Zoom level (1-18) */
  zoom?: number;
  /** Map height */
  height?: number | string;
  /** Whether to auto-fit bounds to markers */
  fitBounds?: boolean;
  /** Marker click handler */
  onMarkerClick?: (marker: MapMarker) => void;
  /** Tile layer URL (default: OpenStreetMap) */
  tileUrl?: string;
  /** Tile layer attribution */
  attribution?: string;
}

/**
 * Helper component to fit map bounds to markers.
 */
function FitBoundsController({
  markers,
  fitBounds,
}: {
  markers: MapMarker[];
  fitBounds: boolean;
}): null {
  const map = useMap();

  useEffect(() => {
    if (fitBounds && markers.length > 0) {
      const bounds = L.latLngBounds(markers.map((m) => [m.lat, m.lng]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [map, markers, fitBounds]);

  return null;
}

/**
 * MapDisplay renders a read-only map with markers.
 *
 * @example
 * ```tsx
 * // In your app entry point:
 * import 'leaflet/dist/leaflet.css';
 *
 * // Then use the component:
 * <MapDisplay
 *   markers={[
 *     { id: '1', lat: -0.4167, lng: 36.95, title: 'Nyeri Factory' },
 *     { id: '2', lat: -0.5333, lng: 37.15, title: 'Meru Factory' },
 *   ]}
 *   fitBounds
 *   onMarkerClick={(marker) => navigate(`/factories/${marker.id}`)}
 * />
 * ```
 */
export function MapDisplay({
  markers = [],
  centerLat = -1.2921, // Default: Nairobi, Kenya
  centerLng = 36.8219,
  zoom = 10,
  height = 400,
  fitBounds = false,
  onMarkerClick,
  tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}: MapDisplayProps): JSX.Element {
  const theme = useTheme();

  return (
    <Box
      sx={{
        height,
        width: '100%',
        borderRadius: 1,
        overflow: 'hidden',
        border: `1px solid ${theme.palette.divider}`,
        '& .leaflet-container': {
          height: '100%',
          width: '100%',
        },
      }}
    >
      <MapContainer
        center={[centerLat, centerLng]}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer url={tileUrl} attribution={attribution} />

        <FitBoundsController markers={markers} fitBounds={fitBounds} />

        {markers.map((marker) => (
          <Marker
            key={marker.id}
            position={[marker.lat, marker.lng]}
            eventHandlers={{
              click: () => onMarkerClick?.(marker),
            }}
          >
            {(marker.title || marker.popupContent) && (
              <Popup>
                {marker.popupContent ?? (
                  <Box>
                    <Typography variant="subtitle2">{marker.title}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {marker.lat.toFixed(6)}, {marker.lng.toFixed(6)}
                    </Typography>
                  </Box>
                )}
              </Popup>
            )}
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
}

export default MapDisplay;
