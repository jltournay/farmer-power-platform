/**
 * GPSFieldWithMapAssist Component
 *
 * Lat/Lng text fields + collapsible map picker.
 * Used for GPS coordinate input with visual assistance.
 *
 * IMPORTANT: Consuming application must import Leaflet CSS:
 * import 'leaflet/dist/leaflet.css';
 *
 * Accessibility:
 * - Text inputs for precise coordinate entry
 * - Map picker for visual selection
 * - Keyboard accessible expand/collapse
 */

import { useState, useCallback } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Collapse,
  Typography,
  useTheme,
} from '@mui/material';
import MapIcon from '@mui/icons-material/Map';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

// Fix for default marker icon issue
// @ts-expect-error - Leaflet default icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/** GPS coordinates */
export interface GPSCoordinates {
  lat: number | null;
  lng: number | null;
}

/** GPSFieldWithMapAssist component props */
export interface GPSFieldWithMapAssistProps {
  /** Current coordinates */
  value: GPSCoordinates;
  /** Change handler */
  onChange: (coords: GPSCoordinates) => void;
  /** Latitude field label */
  latLabel?: string;
  /** Longitude field label */
  lngLabel?: string;
  /** Default map center if no value */
  defaultCenter?: { lat: number; lng: number };
  /** Whether fields are disabled */
  disabled?: boolean;
  /** Whether fields are required */
  required?: boolean;
  /** Validation error messages */
  errors?: { lat?: string; lng?: string };
  /** Helper text */
  helperText?: string;
  /** Whether to start with map expanded (useful for creation forms) */
  initialExpanded?: boolean;
}

/**
 * Component for clicking on the map to set coordinates.
 */
function MapClickHandler({
  onLocationSelect,
}: {
  onLocationSelect: (lat: number, lng: number) => void;
}): null {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/**
 * GPSFieldWithMapAssist provides coordinate input with map assistance.
 *
 * @example
 * ```tsx
 * // In your app entry point:
 * import 'leaflet/dist/leaflet.css';
 *
 * // Then use the component:
 * <GPSFieldWithMapAssist
 *   value={{ lat: farmer.latitude, lng: farmer.longitude }}
 *   onChange={(coords) => setFarmer({ ...farmer, latitude: coords.lat, longitude: coords.lng })}
 *   required
 * />
 * ```
 */
export function GPSFieldWithMapAssist({
  value,
  onChange,
  latLabel = 'Latitude',
  lngLabel = 'Longitude',
  defaultCenter = { lat: -1.2921, lng: 36.8219 }, // Nairobi
  disabled = false,
  required = false,
  errors,
  helperText,
  initialExpanded = false,
}: GPSFieldWithMapAssistProps): JSX.Element {
  const theme = useTheme();
  const [mapExpanded, setMapExpanded] = useState(initialExpanded);
  const [gettingLocation, setGettingLocation] = useState(false);

  const handleLatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const lat = e.target.value ? parseFloat(e.target.value) : null;
    onChange({ ...value, lat: isNaN(lat as number) ? null : lat });
  };

  const handleLngChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const lng = e.target.value ? parseFloat(e.target.value) : null;
    onChange({ ...value, lng: isNaN(lng as number) ? null : lng });
  };

  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      onChange({
        lat: parseFloat(lat.toFixed(6)),
        lng: parseFloat(lng.toFixed(6)),
      });
    },
    [onChange]
  );

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      return;
    }

    setGettingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onChange({
          lat: parseFloat(position.coords.latitude.toFixed(6)),
          lng: parseFloat(position.coords.longitude.toFixed(6)),
        });
        setGettingLocation(false);
      },
      () => {
        setGettingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const mapCenter =
    value.lat !== null && value.lng !== null
      ? { lat: value.lat, lng: value.lng }
      : defaultCenter;

  return (
    <Box>
      {/* Coordinate inputs */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          label={latLabel}
          type="number"
          value={value.lat ?? ''}
          onChange={handleLatChange}
          disabled={disabled}
          required={required}
          error={!!errors?.lat}
          helperText={errors?.lat}
          size="small"
          slotProps={{
            htmlInput: {
              step: 0.000001,
              min: -90,
              max: 90,
            },
          }}
          sx={{
            flex: 1,
            '& .MuiOutlinedInput-root:focus-within': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        />
        <TextField
          label={lngLabel}
          type="number"
          value={value.lng ?? ''}
          onChange={handleLngChange}
          disabled={disabled}
          required={required}
          error={!!errors?.lng}
          helperText={errors?.lng}
          size="small"
          slotProps={{
            htmlInput: {
              step: 0.000001,
              min: -180,
              max: 180,
            },
          }}
          sx={{
            flex: 1,
            '& .MuiOutlinedInput-root:focus-within': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        />

        {/* Get current location button */}
        <IconButton
          onClick={handleGetCurrentLocation}
          disabled={disabled || gettingLocation}
          title="Get current location"
          aria-label="Get current location"
          sx={{
            mt: 0.5,
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          <MyLocationIcon />
        </IconButton>

        {/* Toggle map button */}
        <IconButton
          onClick={() => setMapExpanded(!mapExpanded)}
          disabled={disabled}
          title={mapExpanded ? 'Hide map' : 'Show map'}
          aria-label={mapExpanded ? 'Hide map' : 'Show map'}
          aria-expanded={mapExpanded}
          sx={{
            mt: 0.5,
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          {mapExpanded ? <ExpandLessIcon /> : <MapIcon />}
        </IconButton>
      </Box>

      {/* Helper text */}
      {helperText && !errors?.lat && !errors?.lng && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          {helperText}
        </Typography>
      )}

      {/* Collapsible map */}
      <Collapse in={mapExpanded}>
        <Box
          sx={{
            mt: 2,
            height: 300,
            borderRadius: 1,
            overflow: 'hidden',
            border: `1px solid ${theme.palette.divider}`,
          }}
        >
          <MapContainer
            center={[mapCenter.lat, mapCenter.lng]}
            zoom={value.lat !== null && value.lng !== null ? 14 : 8}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            <MapClickHandler onLocationSelect={handleMapClick} />
            {value.lat !== null && value.lng !== null && (
              <Marker position={[value.lat, value.lng]} />
            )}
          </MapContainer>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          Click on the map to set coordinates
        </Typography>
      </Collapse>
    </Box>
  );
}

export default GPSFieldWithMapAssist;
