/**
 * API Types Tests
 *
 * Tests for type conversion helpers between API and UI formats.
 */

import { describe, it, expect } from 'vitest';
import {
  regionBoundaryToGeoJSON,
  geoJSONToRegionBoundary,
  regionDetailToFormData,
  formDataToCreateRequest,
  formDataToUpdateRequest,
  type RegionBoundary,
  type GeoJSONPolygon,
  type RegionDetail,
  type RegionFormData,
} from '@/api/types';

describe('API Types', () => {
  describe('regionBoundaryToGeoJSON', () => {
    it('converts RegionBoundary to GeoJSONPolygon', () => {
      const boundary: RegionBoundary = {
        type: 'Polygon',
        rings: [
          {
            points: [
              { longitude: 37.0, latitude: -1.0 },
              { longitude: 37.1, latitude: -1.0 },
              { longitude: 37.1, latitude: -1.1 },
              { longitude: 37.0, latitude: -1.1 },
              { longitude: 37.0, latitude: -1.0 },
            ],
          },
        ],
      };

      const result = regionBoundaryToGeoJSON(boundary);

      expect(result).toEqual({
        type: 'Polygon',
        coordinates: [
          [
            [37.0, -1.0],
            [37.1, -1.0],
            [37.1, -1.1],
            [37.0, -1.1],
            [37.0, -1.0],
          ],
        ],
      });
    });

    it('returns undefined for undefined boundary', () => {
      const result = regionBoundaryToGeoJSON(undefined);
      expect(result).toBeUndefined();
    });

    it('returns undefined for boundary with no rings', () => {
      const boundary: RegionBoundary = {
        type: 'Polygon',
        rings: [],
      };
      const result = regionBoundaryToGeoJSON(boundary);
      expect(result).toBeUndefined();
    });
  });

  describe('geoJSONToRegionBoundary', () => {
    it('converts GeoJSONPolygon to RegionBoundary', () => {
      const geoJson: GeoJSONPolygon = {
        type: 'Polygon',
        coordinates: [
          [
            [37.0, -1.0],
            [37.1, -1.0],
            [37.1, -1.1],
            [37.0, -1.1],
            [37.0, -1.0],
          ],
        ],
      };

      const result = geoJSONToRegionBoundary(geoJson);

      expect(result).toEqual({
        type: 'Polygon',
        rings: [
          {
            points: [
              { longitude: 37.0, latitude: -1.0 },
              { longitude: 37.1, latitude: -1.0 },
              { longitude: 37.1, latitude: -1.1 },
              { longitude: 37.0, latitude: -1.1 },
              { longitude: 37.0, latitude: -1.0 },
            ],
          },
        ],
      });
    });

    it('returns undefined for null geoJson', () => {
      const result = geoJSONToRegionBoundary(null);
      expect(result).toBeUndefined();
    });

    it('returns undefined for geoJson with no coordinates', () => {
      const geoJson: GeoJSONPolygon = {
        type: 'Polygon',
        coordinates: [],
      };
      const result = geoJSONToRegionBoundary(geoJson);
      expect(result).toBeUndefined();
    });
  });

  describe('regionDetailToFormData', () => {
    it('converts RegionDetail to RegionFormData', () => {
      const detail: RegionDetail = {
        id: 'region-1',
        name: 'Test Region',
        county: 'Test County',
        country: 'Kenya',
        factory_count: 5,
        farmer_count: 100,
        is_active: true,
        geography: {
          center_gps: { lat: -1.0, lng: 37.0 },
          radius_km: 15,
          altitude_band: {
            min_meters: 1800,
            max_meters: 2500,
            label: 'highland',
          },
          area_km2: 500,
          perimeter_km: 80,
        },
        flush_calendar: {
          first_flush: { start: '03-15', end: '06-15', characteristics: 'Spring' },
          monsoon_flush: { start: '06-16', end: '09-30' },
          autumn_flush: { start: '10-01', end: '12-15' },
          dormant: { start: '12-16', end: '03-14' },
        },
        agronomic: {
          soil_type: 'volcanic_red',
          typical_diseases: ['blister_blight', 'red_rust'],
          harvest_peak_hours: '06:00-10:00',
          frost_risk: false,
        },
        weather_config: {
          api_location: { lat: -1.0, lng: 37.0 },
          altitude_for_api: 2000,
          collection_time: '06:00',
        },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      const result = regionDetailToFormData(detail);

      expect(result.name).toBe('Test Region');
      expect(result.county).toBe('Test County');
      expect(result.country).toBe('Kenya');
      expect(result.altitude_band).toBe('highland');
      expect(result.center_lat).toBe(-1.0);
      expect(result.center_lng).toBe(37.0);
      expect(result.radius_km).toBe(15);
      expect(result.altitude_min).toBe(1800);
      expect(result.altitude_max).toBe(2500);
      expect(result.typical_diseases).toBe('blister_blight, red_rust');
      expect(result.frost_risk).toBe(false);
      expect(result.is_active).toBe(true);
    });
  });

  describe('formDataToCreateRequest', () => {
    it('converts RegionFormData to RegionCreateRequest', () => {
      const formData: RegionFormData = {
        name: 'New Region',
        county: 'New County',
        country: 'Kenya',
        altitude_band: 'midland',
        center_lat: -0.5,
        center_lng: 36.5,
        radius_km: 20,
        altitude_min: 1400,
        altitude_max: 1800,
        weather_api_lat: -0.5,
        weather_api_lng: 36.5,
        weather_api_altitude: 1600,
        weather_collection_time: '07:00',
        first_flush_start: '03-15',
        first_flush_end: '06-15',
        monsoon_flush_start: '06-16',
        monsoon_flush_end: '09-30',
        autumn_flush_start: '10-01',
        autumn_flush_end: '12-15',
        dormant_start: '12-16',
        dormant_end: '03-14',
        soil_type: 'clay',
        typical_diseases: 'blister_blight, red_rust',
        harvest_peak_hours: '06:00-10:00',
        frost_risk: true,
      };

      const result = formDataToCreateRequest(formData);

      expect(result.name).toBe('New Region');
      expect(result.county).toBe('New County');
      expect(result.country).toBe('Kenya');
      expect(result.geography.center_gps).toEqual({ lat: -0.5, lng: 36.5 });
      expect(result.geography.altitude_band.label).toBe('midland');
      expect(result.agronomic.typical_diseases).toEqual(['blister_blight', 'red_rust']);
      expect(result.agronomic.frost_risk).toBe(true);
      expect(result.weather_config.collection_time).toBe('07:00');
    });

    it('parses diseases string into array correctly', () => {
      const formData: RegionFormData = {
        name: 'Region',
        county: 'County',
        country: 'Kenya',
        altitude_band: 'highland',
        center_lat: 0,
        center_lng: 0,
        radius_km: 10,
        altitude_min: 1800,
        altitude_max: 2500,
        weather_api_lat: 0,
        weather_api_lng: 0,
        weather_api_altitude: 2000,
        weather_collection_time: '06:00',
        first_flush_start: '03-15',
        first_flush_end: '06-15',
        monsoon_flush_start: '06-16',
        monsoon_flush_end: '09-30',
        autumn_flush_start: '10-01',
        autumn_flush_end: '12-15',
        dormant_start: '12-16',
        dormant_end: '03-14',
        soil_type: 'volcanic',
        typical_diseases: ' disease1 ,  disease2  ,disease3',
        harvest_peak_hours: '06:00-10:00',
        frost_risk: false,
      };

      const result = formDataToCreateRequest(formData);

      expect(result.agronomic.typical_diseases).toEqual(['disease1', 'disease2', 'disease3']);
    });

    it('handles empty diseases string', () => {
      const formData: RegionFormData = {
        name: 'Region',
        county: 'County',
        country: 'Kenya',
        altitude_band: 'highland',
        center_lat: 0,
        center_lng: 0,
        radius_km: 10,
        altitude_min: 1800,
        altitude_max: 2500,
        weather_api_lat: 0,
        weather_api_lng: 0,
        weather_api_altitude: 2000,
        weather_collection_time: '06:00',
        first_flush_start: '03-15',
        first_flush_end: '06-15',
        monsoon_flush_start: '06-16',
        monsoon_flush_end: '09-30',
        autumn_flush_start: '10-01',
        autumn_flush_end: '12-15',
        dormant_start: '12-16',
        dormant_end: '03-14',
        soil_type: 'volcanic',
        typical_diseases: '',
        harvest_peak_hours: '06:00-10:00',
        frost_risk: false,
      };

      const result = formDataToCreateRequest(formData);

      expect(result.agronomic.typical_diseases).toEqual([]);
    });
  });

  describe('formDataToUpdateRequest', () => {
    it('converts partial RegionFormData to RegionUpdateRequest', () => {
      const formData: Partial<RegionFormData> = {
        name: 'Updated Region',
        is_active: false,
        center_lat: -0.5,
        center_lng: 36.5,
        radius_km: 20,
        altitude_band: 'midland',
        altitude_min: 1400,
        altitude_max: 1800,
        first_flush_start: '03-20',
        first_flush_end: '06-20',
        monsoon_flush_start: '06-21',
        monsoon_flush_end: '09-30',
        autumn_flush_start: '10-01',
        autumn_flush_end: '12-15',
        dormant_start: '12-16',
        dormant_end: '03-19',
        soil_type: 'clay',
        typical_diseases: 'blister_blight',
        harvest_peak_hours: '07:00-11:00',
        frost_risk: true,
        weather_api_lat: -0.5,
        weather_api_lng: 36.5,
        weather_api_altitude: 1600,
        weather_collection_time: '08:00',
      };

      const result = formDataToUpdateRequest(formData);

      expect(result.name).toBe('Updated Region');
      expect(result.is_active).toBe(false);
      expect(result.geography?.center_gps).toEqual({ lat: -0.5, lng: 36.5 });
      expect(result.geography?.altitude_band.label).toBe('midland');
      expect(result.flush_calendar?.first_flush.start).toBe('03-20');
      expect(result.agronomic?.soil_type).toBe('clay');
      expect(result.weather_config?.collection_time).toBe('08:00');
    });

    it('handles name-only updates', () => {
      const formData: Partial<RegionFormData> = {
        name: 'New Name Only',
      };

      const result = formDataToUpdateRequest(formData, false);

      expect(result.name).toBe('New Name Only');
      expect(result.geography).toBeUndefined();
      expect(result.flush_calendar).toBeUndefined();
      expect(result.agronomic).toBeUndefined();
      expect(result.weather_config).toBeUndefined();
    });

    it('handles is_active toggle', () => {
      const formData: Partial<RegionFormData> = {
        is_active: false,
      };

      const result = formDataToUpdateRequest(formData, false);

      expect(result.is_active).toBe(false);
    });

    it('parses diseases string correctly', () => {
      const formData: Partial<RegionFormData> = {
        soil_type: 'loam',
        typical_diseases: ' disease1 , disease2 ',
        harvest_peak_hours: '06:00-10:00',
        frost_risk: false,
      };

      const result = formDataToUpdateRequest(formData);

      expect(result.agronomic?.typical_diseases).toEqual(['disease1', 'disease2']);
    });
  });
});
