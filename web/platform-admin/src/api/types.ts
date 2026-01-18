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

// ============================================================================
// Weather Observation Types (AC 9.2.5)
// ============================================================================

/** Weather alert type */
export type WeatherAlertType = 'heavy_rain' | 'frost_risk' | 'high_humidity' | 'drought';

/** Weather alert with icon and impact */
export interface WeatherAlert {
  alert_type: WeatherAlertType;
  icon: string;
  impact: string;
}

/** Single day's weather observation */
export interface WeatherObservation {
  date: string; // ISO date string
  temp_min: number;
  temp_max: number;
  precipitation_mm: number;
  humidity_avg: number;
  source: string;
  alerts: WeatherAlert[];
}

/** Region weather response */
export interface RegionWeatherResponse {
  region_id: string;
  observations: WeatherObservation[];
  last_updated: string | null; // ISO datetime string
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

// ============================================================================
// Factory Types
// ============================================================================

/** Payment policy type enum */
export type PaymentPolicyType = 'feedback_only' | 'split_payment' | 'weekly_bonus' | 'delayed_payment';

/** Geographic location (altitude auto-populated from Google Elevation API) */
export interface GeoLocation {
  latitude: number;
  longitude: number;
  altitude_meters?: number; // READ-ONLY: Auto-populated by backend from Google Elevation API
}

/** Contact information */
export interface ContactInfo {
  phone: string;
  email: string;
  address: string;
}

/** Quality tier thresholds */
export interface QualityThresholdsAPI {
  tier_1: number; // Default 85
  tier_2: number; // Default 70
  tier_3: number; // Default 50
}

/** Payment policy configuration */
export interface PaymentPolicyAPI {
  policy_type: PaymentPolicyType;
  tier_1_adjustment: number;
  tier_2_adjustment: number;
  tier_3_adjustment: number;
  below_tier_3_adjustment: number;
}

/** Grading model summary */
export interface GradingModelSummary {
  id: string;
  name: string;
  version: string;
  grade_count: number;
}

/** Factory summary for list views */
export interface FactorySummary {
  id: string;
  name: string;
  code: string;
  region_id: string;
  collection_point_count: number;
  farmer_count: number;
  is_active: boolean;
}

/** Full factory detail */
export interface FactoryDetail extends FactorySummary {
  location: GeoLocation;
  contact: ContactInfo;
  processing_capacity_kg: number;
  quality_thresholds: QualityThresholdsAPI;
  payment_policy: PaymentPolicyAPI;
  grading_model: GradingModelSummary | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/** Factory list API response */
export interface FactoryListResponse {
  data: FactorySummary[];
  pagination: PaginationMeta;
}

/** Factory list query parameters */
export interface FactoryListParams {
  region_id?: string;
  page_size?: number;
  page_token?: string;
  active_only?: boolean;
}

/** Factory create request */
export interface FactoryCreateRequest {
  name: string;
  code: string;
  region_id: string;
  location: GeoLocation;
  contact?: ContactInfo;
  processing_capacity_kg?: number;
  quality_thresholds?: QualityThresholdsAPI;
  payment_policy?: PaymentPolicyAPI;
}

/** Factory update request */
export interface FactoryUpdateRequest {
  name?: string;
  code?: string;
  location?: GeoLocation;
  contact?: ContactInfo;
  processing_capacity_kg?: number;
  quality_thresholds?: QualityThresholdsAPI;
  payment_policy?: PaymentPolicyAPI;
  is_active?: boolean;
}

// ============================================================================
// Collection Point Types
// ============================================================================

/** Operating hours for collection points (HH:MM-HH:MM format) */
export interface OperatingHours {
  weekdays: string; // e.g., "06:00-10:00"
  weekends: string; // e.g., "07:00-09:00"
}

/** Collection point capacity and equipment info */
export interface CollectionPointCapacity {
  max_daily_kg: number;
  storage_type: string; // 'open_air' | 'covered_shed' | 'refrigerated'
  has_weighing_scale: boolean;
  has_qc_device: boolean;
}

/** Lead farmer summary for collection point */
export interface LeadFarmerSummary {
  id: string;
  name: string;
  phone: string;
}

/** Collection point status type */
export type CollectionPointStatus = 'active' | 'inactive' | 'seasonal';

/** Collection point summary for list views */
export interface CollectionPointSummary {
  id: string;
  name: string;
  factory_id: string;
  region_id: string;
  farmer_count: number;
  status: CollectionPointStatus;
}

/** Full collection point detail (for detail/edit pages) */
export interface CollectionPointDetailFull {
  id: string;
  name: string;
  factory_id: string;
  region_id: string;
  location: GeoLocation;
  clerk_id: string | null;
  clerk_phone: string | null;
  operating_hours: OperatingHours;
  collection_days: string[]; // ['mon', 'tue', 'wed', ...]
  capacity: CollectionPointCapacity;
  lead_farmer: LeadFarmerSummary | null;
  farmer_count: number;
  status: CollectionPointStatus;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/** Collection point create request (for quick-add from factory) */
export interface CollectionPointCreateRequest {
  name: string;
  location: GeoLocation;
  region_id: string;
  clerk_id?: string | null;
  clerk_phone?: string | null;
  operating_hours?: OperatingHours;
  collection_days?: string[];
  capacity?: CollectionPointCapacity;
  status?: string;
}

/** Collection point update request */
export interface CollectionPointUpdateRequest {
  name?: string;
  clerk_id?: string | null;
  clerk_phone?: string | null;
  operating_hours?: OperatingHours;
  collection_days?: string[];
  capacity?: CollectionPointCapacity;
  status?: string;
}

/** Collection point list API response */
export interface CollectionPointListResponse {
  data: CollectionPointSummary[];
  pagination: PaginationMeta;
}

/** Collection point list query parameters */
export interface CollectionPointListParams {
  factory_id: string; // Required
  page_size?: number;
  page_token?: string;
  active_only?: boolean;
}

/** Collection point detail (legacy - for backwards compatibility with create response) */
export interface CollectionPointDetail {
  id: string;
  name: string;
  factory_id: string;
  region_id: string;
  location: GeoLocation;
  clerk_id: string | null;
  clerk_phone: string | null;
  farmer_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Factory Form Types
// ============================================================================

/** Form data for factory create/edit (flat structure for react-hook-form) */
export interface FactoryFormData {
  // Basic info
  name: string;
  code: string;
  region_id: string;
  // Location (user inputs lat/lng, altitude is display-only from API response)
  latitude: number;
  longitude: number;
  // NOTE: altitude_meters is NOT in form data - it's auto-populated by backend
  // Contact
  phone: string;
  email: string;
  address: string;
  // Capacity
  processing_capacity_kg: number;
  // Quality thresholds
  tier_1: number;
  tier_2: number;
  tier_3: number;
  // Payment policy
  policy_type: PaymentPolicyType;
  tier_1_adjustment: number;
  tier_2_adjustment: number;
  tier_3_adjustment: number;
  below_tier_3_adjustment: number;
  // Status
  is_active: boolean;
}

/** Default values for factory form */
export const FACTORY_FORM_DEFAULTS: FactoryFormData = {
  name: '',
  code: '',
  region_id: '',
  latitude: -1.0, // Default to Kenya
  longitude: 37.0,
  // altitude_meters NOT included - auto-populated by backend from Google Elevation API
  phone: '',
  email: '',
  address: '',
  processing_capacity_kg: 0,
  tier_1: 85,
  tier_2: 70,
  tier_3: 50,
  policy_type: 'feedback_only',
  tier_1_adjustment: 0,
  tier_2_adjustment: 0,
  tier_3_adjustment: 0,
  below_tier_3_adjustment: 0,
  is_active: true,
};

// ============================================================================
// Factory Conversion Helpers
// ============================================================================

/** Convert FactoryDetail to form data */
export function factoryDetailToFormData(detail: FactoryDetail): FactoryFormData {
  return {
    name: detail.name,
    code: detail.code,
    region_id: detail.region_id,
    latitude: detail.location.latitude,
    longitude: detail.location.longitude,
    phone: detail.contact.phone ?? '',
    email: detail.contact.email ?? '',
    address: detail.contact.address ?? '',
    processing_capacity_kg: detail.processing_capacity_kg,
    tier_1: detail.quality_thresholds.tier_1,
    tier_2: detail.quality_thresholds.tier_2,
    tier_3: detail.quality_thresholds.tier_3,
    policy_type: detail.payment_policy.policy_type,
    tier_1_adjustment: detail.payment_policy.tier_1_adjustment,
    tier_2_adjustment: detail.payment_policy.tier_2_adjustment,
    tier_3_adjustment: detail.payment_policy.tier_3_adjustment,
    below_tier_3_adjustment: detail.payment_policy.below_tier_3_adjustment,
    is_active: detail.is_active,
  };
}

/** Convert form data to FactoryCreateRequest */
export function factoryFormDataToCreateRequest(data: FactoryFormData): FactoryCreateRequest {
  return {
    name: data.name,
    code: data.code,
    region_id: data.region_id,
    location: {
      latitude: data.latitude,
      longitude: data.longitude,
    },
    contact: {
      phone: data.phone,
      email: data.email,
      address: data.address,
    },
    processing_capacity_kg: data.processing_capacity_kg,
    quality_thresholds: {
      tier_1: data.tier_1,
      tier_2: data.tier_2,
      tier_3: data.tier_3,
    },
    payment_policy: {
      policy_type: data.policy_type,
      tier_1_adjustment: data.tier_1_adjustment,
      tier_2_adjustment: data.tier_2_adjustment,
      tier_3_adjustment: data.tier_3_adjustment,
      below_tier_3_adjustment: data.below_tier_3_adjustment,
    },
  };
}

/** Convert form data to FactoryUpdateRequest */
export function factoryFormDataToUpdateRequest(data: Partial<FactoryFormData>): FactoryUpdateRequest {
  const request: FactoryUpdateRequest = {};

  if (data.name !== undefined) {
    request.name = data.name;
  }

  if (data.code !== undefined) {
    request.code = data.code;
  }

  if (data.latitude !== undefined && data.longitude !== undefined) {
    request.location = {
      latitude: data.latitude,
      longitude: data.longitude,
    };
  }

  if (data.phone !== undefined || data.email !== undefined || data.address !== undefined) {
    request.contact = {
      phone: data.phone ?? '',
      email: data.email ?? '',
      address: data.address ?? '',
    };
  }

  if (data.processing_capacity_kg !== undefined) {
    request.processing_capacity_kg = data.processing_capacity_kg;
  }

  if (data.tier_1 !== undefined && data.tier_2 !== undefined && data.tier_3 !== undefined) {
    request.quality_thresholds = {
      tier_1: data.tier_1,
      tier_2: data.tier_2,
      tier_3: data.tier_3,
    };
  }

  if (data.policy_type !== undefined) {
    request.payment_policy = {
      policy_type: data.policy_type,
      tier_1_adjustment: data.tier_1_adjustment ?? 0,
      tier_2_adjustment: data.tier_2_adjustment ?? 0,
      tier_3_adjustment: data.tier_3_adjustment ?? 0,
      below_tier_3_adjustment: data.below_tier_3_adjustment ?? 0,
    };
  }

  if (data.is_active !== undefined) {
    request.is_active = data.is_active;
  }

  return request;
}

// ============================================================================
// Collection Point Form Types and Helpers
// ============================================================================

/** Storage type options for collection point */
export const STORAGE_TYPE_OPTIONS = [
  { value: 'open_air', label: 'Open Air' },
  { value: 'covered_shed', label: 'Covered Shed' },
  { value: 'refrigerated', label: 'Refrigerated' },
] as const;

/** Collection days options */
export const COLLECTION_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type CollectionDay = (typeof COLLECTION_DAYS)[number];

/** Form data for collection point edit (flat structure for react-hook-form) */
export interface CollectionPointFormData {
  name: string;
  status: CollectionPointStatus;
  latitude: number;
  longitude: number;
  clerk_id: string;
  clerk_phone: string;
  weekday_hours: string; // "HH:MM-HH:MM" format
  weekend_hours: string; // "HH:MM-HH:MM" format
  collection_days: CollectionDay[];
  max_daily_kg: number;
  storage_type: string;
  has_weighing_scale: boolean;
  has_qc_device: boolean;
}

/** Default values for collection point form */
export const CP_FORM_DEFAULTS: CollectionPointFormData = {
  name: '',
  status: 'active',
  latitude: -1.0, // Default to Kenya
  longitude: 37.0,
  clerk_id: '',
  clerk_phone: '',
  weekday_hours: '06:00-10:00',
  weekend_hours: '07:00-09:00',
  collection_days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'],
  max_daily_kg: 500,
  storage_type: 'covered_shed',
  has_weighing_scale: true,
  has_qc_device: true,
};

/** Convert CollectionPointDetailFull to form data */
export function cpDetailToFormData(detail: CollectionPointDetailFull): CollectionPointFormData {
  return {
    name: detail.name,
    status: detail.status,
    latitude: detail.location.latitude,
    longitude: detail.location.longitude,
    clerk_id: detail.clerk_id ?? '',
    clerk_phone: detail.clerk_phone ?? '',
    weekday_hours: detail.operating_hours.weekdays,
    weekend_hours: detail.operating_hours.weekends,
    collection_days: detail.collection_days as CollectionDay[],
    max_daily_kg: detail.capacity.max_daily_kg,
    storage_type: detail.capacity.storage_type,
    has_weighing_scale: detail.capacity.has_weighing_scale,
    has_qc_device: detail.capacity.has_qc_device,
  };
}

/** Convert form data to CollectionPointUpdateRequest */
export function cpFormDataToUpdateRequest(data: CollectionPointFormData): CollectionPointUpdateRequest {
  return {
    name: data.name,
    clerk_id: data.clerk_id || null,
    clerk_phone: data.clerk_phone || null,
    operating_hours: {
      weekdays: data.weekday_hours,
      weekends: data.weekend_hours,
    },
    collection_days: data.collection_days,
    capacity: {
      max_daily_kg: data.max_daily_kg,
      storage_type: data.storage_type,
      has_weighing_scale: data.has_weighing_scale,
      has_qc_device: data.has_qc_device,
    },
    status: data.status,
  };
}

/** Parse time range string (HH:MM-HH:MM) into start and end times */
export function parseTimeRange(timeRange: string): { start: string; end: string } {
  const [start, end] = timeRange.split('-');
  return { start: start ?? '06:00', end: end ?? '10:00' };
}

/** Format start and end times into time range string */
export function formatTimeRange(start: string, end: string): string {
  return `${start}-${end}`;
}

// ============================================================================
// Farmer Types (Story 9.5)
// ============================================================================

/** Farm scale classification */
export type FarmScale = 'smallholder' | 'medium' | 'large' | 'estate';

/** Quality tier level */
export type TierLevel = 'premium' | 'standard' | 'acceptable' | 'below';

/** Performance trend indicator */
export type TrendIndicator = 'improving' | 'stable' | 'declining';

/** Notification channel preference */
export type NotificationChannel = 'sms' | 'whatsapp' | 'push' | 'voice';

/** Interaction preference mode */
export type InteractionPreference = 'text' | 'voice' | 'visual';

/** Preferred language */
export type PreferredLanguage = 'sw' | 'en' | 'ki' | 'luo';

/** Farmer summary for admin list views (Story 9.5a: N:M model) */
export interface FarmerSummary {
  id: string;
  name: string;
  phone: string;
  cp_count: number; // Story 9.5a: replaced collection_point_id with cp_count
  region_id: string;
  farm_scale: FarmScale;
  tier: TierLevel;
  trend: TrendIndicator;
  is_active: boolean;
}

/** Communication preferences */
export interface CommunicationPreferences {
  notification_channel: NotificationChannel;
  interaction_pref: InteractionPreference;
  pref_lang: PreferredLanguage;
}

/** Performance metrics for farmer detail view */
export interface FarmerPerformanceMetrics {
  primary_percentage_30d: number;
  primary_percentage_90d: number;
  total_kg_30d: number;
  total_kg_90d: number;
  tier: TierLevel;
  trend: TrendIndicator;
  deliveries_today: number;
  kg_today: number;
}

/** Collection point summary for farmer detail view (Story 9.5a: N:M model) */
export interface CollectionPointSummaryForFarmer {
  id: string;
  name: string;
  factory_id: string;
}

/** Full farmer detail for admin single-entity views (Story 9.5a: N:M model) */
export interface FarmerDetail {
  id: string;
  grower_number: string | null;
  first_name: string;
  last_name: string;
  phone: string;
  national_id: string;
  region_id: string;
  collection_points: CollectionPointSummaryForFarmer[]; // Story 9.5a: N:M model
  farm_location: GeoLocation;
  farm_size_hectares: number;
  farm_scale: FarmScale;
  performance: FarmerPerformanceMetrics;
  communication_prefs: CommunicationPreferences;
  is_active: boolean;
  registration_date: string; // ISO datetime
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/** Farmer list API response */
export interface FarmerListResponse {
  data: FarmerSummary[];
  pagination: PaginationMeta;
}

/** Farmer list query parameters */
export interface FarmerListParams {
  page_size?: number;
  page_token?: string;
  region_id?: string;
  collection_point_id?: string;
  farm_scale?: FarmScale;
  tier?: TierLevel;
  active_only?: boolean;
  search?: string;
}

/** Farmer create request (Story 9.5a: collection_point_id removed - use separate assignment API) */
export interface FarmerCreateRequest {
  first_name: string;
  last_name: string;
  phone: string;
  national_id: string;
  // Story 9.5a: collection_point_id removed - CP assignment via delivery or separate API
  farm_size_hectares: number;
  latitude: number;
  longitude: number;
  grower_number?: string | null;
  notification_channel?: NotificationChannel;
  interaction_pref?: InteractionPreference;
  pref_lang?: PreferredLanguage;
}

/** Farmer update request */
export interface FarmerUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string;
  farm_size_hectares?: number;
  notification_channel?: NotificationChannel;
  interaction_pref?: InteractionPreference;
  pref_lang?: PreferredLanguage;
  is_active?: boolean;
}

/** Import error row */
export interface ImportErrorRow {
  row: number;
  error: string;
  data: Record<string, unknown> | null;
}

/** Farmer import response */
export interface FarmerImportResponse {
  created_count: number;
  error_count: number;
  error_rows: ImportErrorRow[];
  total_rows: number;
}

// ============================================================================
// Farmer Form Types and Helpers
// ============================================================================

/** Form data for farmer create (flat structure for react-hook-form)
 * Story 9.5a: collection_point_id removed - CP assignment via delivery or separate API
 */
export interface FarmerFormData {
  first_name: string;
  last_name: string;
  phone: string;
  national_id: string;
  // Story 9.5a: collection_point_id removed
  farm_size_hectares: number;
  latitude: number;
  longitude: number;
  grower_number: string;
  notification_channel: NotificationChannel;
  interaction_pref: InteractionPreference;
  pref_lang: PreferredLanguage;
}

/** Default values for farmer form */
export const FARMER_FORM_DEFAULTS: FarmerFormData = {
  first_name: '',
  last_name: '',
  phone: '+254',
  national_id: '',
  // Story 9.5a: collection_point_id removed
  farm_size_hectares: 0.5,
  latitude: -1.0, // Default to Kenya
  longitude: 37.0,
  grower_number: '',
  notification_channel: 'sms',
  interaction_pref: 'text',
  pref_lang: 'sw',
};

/** Convert form data to FarmerCreateRequest (Story 9.5a: collection_point_id removed) */
export function farmerFormDataToCreateRequest(data: FarmerFormData): FarmerCreateRequest {
  return {
    first_name: data.first_name,
    last_name: data.last_name,
    phone: data.phone,
    national_id: data.national_id,
    // Story 9.5a: collection_point_id removed
    farm_size_hectares: data.farm_size_hectares,
    latitude: data.latitude,
    longitude: data.longitude,
    grower_number: data.grower_number || null,
    notification_channel: data.notification_channel,
    interaction_pref: data.interaction_pref,
    pref_lang: data.pref_lang,
  };
}

/** Convert FarmerDetail to form data for editing (Story 9.5a: collection_point_id removed) */
export function farmerDetailToFormData(detail: FarmerDetail): FarmerFormData {
  return {
    first_name: detail.first_name,
    last_name: detail.last_name,
    phone: detail.phone,
    national_id: detail.national_id,
    // Story 9.5a: collection_point_id removed - use collection_points array on FarmerDetail
    farm_size_hectares: detail.farm_size_hectares,
    latitude: detail.farm_location.latitude,
    longitude: detail.farm_location.longitude,
    grower_number: detail.grower_number ?? '',
    notification_channel: detail.communication_prefs.notification_channel,
    interaction_pref: detail.communication_prefs.interaction_pref,
    pref_lang: detail.communication_prefs.pref_lang,
  };
}

/** Convert form data to FarmerUpdateRequest */
export function farmerFormDataToUpdateRequest(data: Partial<FarmerFormData>): FarmerUpdateRequest {
  const request: FarmerUpdateRequest = {};

  if (data.first_name !== undefined) {
    request.first_name = data.first_name;
  }

  if (data.last_name !== undefined) {
    request.last_name = data.last_name;
  }

  if (data.phone !== undefined) {
    request.phone = data.phone;
  }

  if (data.farm_size_hectares !== undefined) {
    request.farm_size_hectares = data.farm_size_hectares;
  }

  if (data.notification_channel !== undefined) {
    request.notification_channel = data.notification_channel;
  }

  if (data.interaction_pref !== undefined) {
    request.interaction_pref = data.interaction_pref;
  }

  if (data.pref_lang !== undefined) {
    request.pref_lang = data.pref_lang;
  }

  return request;
}

/** Farm scale display options */
export const FARM_SCALE_OPTIONS = [
  { value: 'smallholder', label: 'Smallholder (<0.5 ha)' },
  { value: 'medium', label: 'Medium (0.5-2 ha)' },
  { value: 'large', label: 'Large (2-5 ha)' },
  { value: 'estate', label: 'Estate (>5 ha)' },
] as const;

/** Tier level display options */
export const TIER_LEVEL_OPTIONS = [
  { value: 'premium', label: 'Premium', color: 'success' as const },
  { value: 'standard', label: 'Standard', color: 'warning' as const },
  { value: 'acceptable', label: 'Acceptable', color: 'info' as const },
  { value: 'below', label: 'Below', color: 'default' as const },
] as const;

/** Notification channel options */
export const NOTIFICATION_CHANNEL_OPTIONS = [
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'push', label: 'Push Notification' },
  { value: 'voice', label: 'Voice Call' },
] as const;

/** Interaction preference options */
export const INTERACTION_PREF_OPTIONS = [
  { value: 'text', label: 'Text Messages' },
  { value: 'voice', label: 'Voice Messages' },
  { value: 'visual', label: 'Visual/Images' },
] as const;

/** Language options */
export const LANGUAGE_OPTIONS = [
  { value: 'sw', label: 'Swahili' },
  { value: 'en', label: 'English' },
  { value: 'ki', label: 'Kikuyu' },
  { value: 'luo', label: 'Luo' },
] as const;

/** Get tier color for Chip display */
export function getTierColor(tier: TierLevel): 'success' | 'warning' | 'info' | 'default' {
  switch (tier) {
    case 'premium':
      return 'success';
    case 'standard':
      return 'warning';
    case 'acceptable':
      return 'info';
    default:
      return 'default';
  }
}

/** Get trend icon name */
export function getTrendIcon(trend: TrendIndicator): string {
  switch (trend) {
    case 'improving':
      return 'TrendingUp';
    case 'declining':
      return 'TrendingDown';
    default:
      return 'TrendingFlat';
  }
}

/** Get trend color */
export function getTrendColor(trend: TrendIndicator): 'success' | 'error' | 'default' {
  switch (trend) {
    case 'improving':
      return 'success';
    case 'declining':
      return 'error';
    default:
      return 'default';
  }
}
