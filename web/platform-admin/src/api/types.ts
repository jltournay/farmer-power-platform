/**
 * API Type Definitions
 *
 * TypeScript types matching BFF API schemas for type-safe API interactions.
 * Based on services/bff/src/bff/api/schemas/admin/region_schemas.py
 */

// ============================================================================
// Common Types
// ============================================================================

/** Pagination metadata from BFF responses */
export interface PaginationMeta {
  total_count: number;
  page_size: number;
  page: number;
  next_page_token: string | null;
  has_next: boolean;
}

// ============================================================================
// Region Types
// ============================================================================

/** Altitude band classification */
export type AltitudeBand = 'highland' | 'midland' | 'lowland';

/** GPS coordinates (lat/lng) */
export interface GPS {
  lat: number;
  lng: number;
}

/** GeoJSON Polygon type for boundary data (UI format for BoundaryDrawer) */
export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

/** Coordinate pair from API (longitude, latitude) */
export interface Coordinate {
  longitude: number;
  latitude: number;
}

/** Polygon ring from API */
export interface PolygonRing {
  points: Coordinate[];
}

/** Region boundary from API (Pydantic format) */
export interface RegionBoundary {
  type: 'Polygon';
  rings: PolygonRing[];
}

/** Altitude band definition */
export interface AltitudeBandDef {
  min_meters: number;
  max_meters: number;
  label: AltitudeBand;
}

/** Geography definition for a region */
export interface Geography {
  center_gps: GPS;
  radius_km: number;
  altitude_band: AltitudeBandDef;
  boundary?: RegionBoundary;
  area_km2?: number;
  perimeter_km?: number;
}

/** Flush period definition */
export interface FlushPeriod {
  start: string; // MM-DD format
  end: string; // MM-DD format
  characteristics?: string;
}

/** Tea flush calendar */
export interface FlushCalendar {
  first_flush: FlushPeriod;
  monsoon_flush: FlushPeriod;
  autumn_flush: FlushPeriod;
  dormant: FlushPeriod;
}

/** Weather API configuration */
export interface WeatherConfig {
  api_location: GPS;
  altitude_for_api: number;
  collection_time: string; // HH:MM format
}

/** Agronomic factors */
export interface Agronomic {
  soil_type: string;
  typical_diseases: string[];
  harvest_peak_hours: string; // HH:MM-HH:MM format
  frost_risk: boolean;
}

/** Region summary for list views */
export interface RegionSummary {
  id: string;
  name: string;
  county: string;
  country: string;
  altitude_band: AltitudeBand;
  factory_count: number;
  farmer_count: number;
  is_active: boolean;
}

/** Full region detail */
export interface RegionDetail extends Omit<RegionSummary, 'altitude_band'> {
  geography: Geography;
  flush_calendar: FlushCalendar;
  agronomic: Agronomic;
  weather_config: WeatherConfig;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/** Region list API response */
export interface RegionListResponse {
  data: RegionSummary[];
  pagination: PaginationMeta;
}

/** Region list query parameters */
export interface RegionListParams {
  page_size?: number;
  page_token?: string;
  active_only?: boolean;
}

/** Region create request payload */
export interface RegionCreateRequest {
  name: string;
  county: string;
  country?: string;
  geography: Geography;
  flush_calendar: FlushCalendar;
  agronomic: Agronomic;
  weather_config: WeatherConfig;
}

/** Region update request payload */
export interface RegionUpdateRequest {
  name?: string;
  geography?: Geography;
  flush_calendar?: FlushCalendar;
  agronomic?: Agronomic;
  weather_config?: WeatherConfig;
  is_active?: boolean;
}

// ============================================================================
// Form Types
// ============================================================================

/** Form data for region create/edit (flat structure for react-hook-form) */
export interface RegionFormData {
  name: string;
  county: string;
  country: string;
  altitude_band: AltitudeBand;
  // Geography
  center_lat: number;
  center_lng: number;
  radius_km: number;
  altitude_min: number;
  altitude_max: number;
  boundary?: GeoJSONPolygon;
  area_km2?: number;
  perimeter_km?: number;
  // Weather config
  weather_api_lat: number;
  weather_api_lng: number;
  weather_api_altitude: number;
  weather_collection_time: string;
  // Flush calendar
  first_flush_start: string;
  first_flush_end: string;
  first_flush_characteristics?: string;
  monsoon_flush_start: string;
  monsoon_flush_end: string;
  monsoon_flush_characteristics?: string;
  autumn_flush_start: string;
  autumn_flush_end: string;
  autumn_flush_characteristics?: string;
  dormant_start: string;
  dormant_end: string;
  dormant_characteristics?: string;
  // Agronomic
  soil_type: string;
  typical_diseases: string;
  harvest_peak_hours: string;
  frost_risk: boolean;
  // Status
  is_active?: boolean;
}

// ============================================================================
// Helpers
// ============================================================================

/** Convert RegionDetail to form data */
export function regionDetailToFormData(detail: RegionDetail): RegionFormData {
  return {
    name: detail.name,
    county: detail.county,
    country: detail.country,
    altitude_band: detail.geography.altitude_band.label,
    center_lat: detail.geography.center_gps.lat,
    center_lng: detail.geography.center_gps.lng,
    radius_km: detail.geography.radius_km,
    altitude_min: detail.geography.altitude_band.min_meters,
    altitude_max: detail.geography.altitude_band.max_meters,
    boundary: regionBoundaryToGeoJSON(detail.geography.boundary),
    area_km2: detail.geography.area_km2 ?? undefined,
    perimeter_km: detail.geography.perimeter_km ?? undefined,
    weather_api_lat: detail.weather_config.api_location.lat,
    weather_api_lng: detail.weather_config.api_location.lng,
    weather_api_altitude: detail.weather_config.altitude_for_api,
    weather_collection_time: detail.weather_config.collection_time,
    first_flush_start: detail.flush_calendar.first_flush.start,
    first_flush_end: detail.flush_calendar.first_flush.end,
    first_flush_characteristics: detail.flush_calendar.first_flush.characteristics ?? '',
    monsoon_flush_start: detail.flush_calendar.monsoon_flush.start,
    monsoon_flush_end: detail.flush_calendar.monsoon_flush.end,
    monsoon_flush_characteristics: detail.flush_calendar.monsoon_flush.characteristics ?? '',
    autumn_flush_start: detail.flush_calendar.autumn_flush.start,
    autumn_flush_end: detail.flush_calendar.autumn_flush.end,
    autumn_flush_characteristics: detail.flush_calendar.autumn_flush.characteristics ?? '',
    dormant_start: detail.flush_calendar.dormant.start,
    dormant_end: detail.flush_calendar.dormant.end,
    dormant_characteristics: detail.flush_calendar.dormant.characteristics ?? '',
    soil_type: detail.agronomic.soil_type,
    typical_diseases: detail.agronomic.typical_diseases.join(', '),
    harvest_peak_hours: detail.agronomic.harvest_peak_hours,
    frost_risk: detail.agronomic.frost_risk,
    is_active: detail.is_active,
  };
}

/** Convert form data to RegionCreateRequest */
export function formDataToCreateRequest(data: RegionFormData): RegionCreateRequest {
  return {
    name: data.name,
    county: data.county,
    country: data.country,
    geography: {
      center_gps: { lat: data.center_lat, lng: data.center_lng },
      radius_km: data.radius_km,
      altitude_band: {
        min_meters: data.altitude_min,
        max_meters: data.altitude_max,
        label: data.altitude_band,
      },
      boundary: geoJSONToRegionBoundary(data.boundary ?? null),
      area_km2: data.area_km2,
      perimeter_km: data.perimeter_km,
    },
    flush_calendar: {
      first_flush: {
        start: data.first_flush_start,
        end: data.first_flush_end,
        characteristics: data.first_flush_characteristics,
      },
      monsoon_flush: {
        start: data.monsoon_flush_start,
        end: data.monsoon_flush_end,
        characteristics: data.monsoon_flush_characteristics,
      },
      autumn_flush: {
        start: data.autumn_flush_start,
        end: data.autumn_flush_end,
        characteristics: data.autumn_flush_characteristics,
      },
      dormant: {
        start: data.dormant_start,
        end: data.dormant_end,
        characteristics: data.dormant_characteristics,
      },
    },
    agronomic: {
      soil_type: data.soil_type,
      typical_diseases: data.typical_diseases.split(',').map((d) => d.trim()).filter(Boolean),
      harvest_peak_hours: data.harvest_peak_hours,
      frost_risk: data.frost_risk,
    },
    weather_config: {
      api_location: { lat: data.weather_api_lat, lng: data.weather_api_lng },
      altitude_for_api: data.weather_api_altitude,
      collection_time: data.weather_collection_time,
    },
  };
}

/** Convert form data to RegionUpdateRequest */
export function formDataToUpdateRequest(
  data: Partial<RegionFormData>,
  hasGeographyChanged: boolean = true
): RegionUpdateRequest {
  const request: RegionUpdateRequest = {};

  if (data.name !== undefined) {
    request.name = data.name;
  }

  if (data.is_active !== undefined) {
    request.is_active = data.is_active;
  }

  if (hasGeographyChanged && data.center_lat !== undefined && data.altitude_band !== undefined) {
    request.geography = {
      center_gps: { lat: data.center_lat!, lng: data.center_lng! },
      radius_km: data.radius_km!,
      altitude_band: {
        min_meters: data.altitude_min!,
        max_meters: data.altitude_max!,
        label: data.altitude_band!,
      },
      boundary: geoJSONToRegionBoundary(data.boundary ?? null),
      area_km2: data.area_km2,
      perimeter_km: data.perimeter_km,
    };
  }

  if (data.first_flush_start !== undefined) {
    request.flush_calendar = {
      first_flush: {
        start: data.first_flush_start!,
        end: data.first_flush_end!,
        characteristics: data.first_flush_characteristics,
      },
      monsoon_flush: {
        start: data.monsoon_flush_start!,
        end: data.monsoon_flush_end!,
        characteristics: data.monsoon_flush_characteristics,
      },
      autumn_flush: {
        start: data.autumn_flush_start!,
        end: data.autumn_flush_end!,
        characteristics: data.autumn_flush_characteristics,
      },
      dormant: {
        start: data.dormant_start!,
        end: data.dormant_end!,
        characteristics: data.dormant_characteristics,
      },
    };
  }

  if (data.soil_type !== undefined) {
    request.agronomic = {
      soil_type: data.soil_type!,
      typical_diseases: data.typical_diseases!.split(',').map((d) => d.trim()).filter(Boolean),
      harvest_peak_hours: data.harvest_peak_hours!,
      frost_risk: data.frost_risk!,
    };
  }

  if (data.weather_api_lat !== undefined) {
    request.weather_config = {
      api_location: { lat: data.weather_api_lat!, lng: data.weather_api_lng! },
      altitude_for_api: data.weather_api_altitude!,
      collection_time: data.weather_collection_time!,
    };
  }

  return request;
}

// ============================================================================
// Boundary Conversion Helpers
// ============================================================================

/**
 * Convert API RegionBoundary to GeoJSON Polygon for BoundaryDrawer.
 */
export function regionBoundaryToGeoJSON(boundary: RegionBoundary | undefined): GeoJSONPolygon | undefined {
  if (!boundary || !boundary.rings || boundary.rings.length === 0) {
    return undefined;
  }

  return {
    type: 'Polygon',
    coordinates: boundary.rings.map((ring) =>
      ring.points.map((coord) => [coord.longitude, coord.latitude])
    ),
  };
}

/**
 * Convert GeoJSON Polygon from BoundaryDrawer to API RegionBoundary.
 */
export function geoJSONToRegionBoundary(geoJson: GeoJSONPolygon | null): RegionBoundary | undefined {
  if (!geoJson || !geoJson.coordinates || geoJson.coordinates.length === 0) {
    return undefined;
  }

  return {
    type: 'Polygon',
    rings: geoJson.coordinates.map((ring) => ({
      points: ring.map((coord) => ({
        longitude: coord[0] ?? 0,
        latitude: coord[1] ?? 0,
      })),
    })),
  };
}
