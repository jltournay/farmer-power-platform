/**
 * Collection Point Types Tests
 *
 * Tests for type conversion helpers between API and UI formats.
 * Story 9.4 - Collection Point Management
 */

import { describe, it, expect } from 'vitest';
import {
  cpDetailToFormData,
  cpFormDataToUpdateRequest,
  parseTimeRange,
  formatTimeRange,
  CP_FORM_DEFAULTS,
  COLLECTION_DAYS,
  STORAGE_TYPE_OPTIONS,
  type CollectionPointDetailFull,
  type CollectionPointFormData,
} from '../../../../../web/platform-admin/src/api/types';

describe('Collection Point Types', () => {
  describe('cpDetailToFormData', () => {
    it('converts CollectionPointDetailFull to CollectionPointFormData', () => {
      const detail: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-001',
        name: 'Nyeri Central CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.42, longitude: 36.95 },
        clerk_id: 'CLERK-001',
        clerk_phone: '+254712345678',
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon', 'tue', 'wed', 'thu', 'fri'],
        capacity: {
          max_daily_kg: 500,
          storage_type: 'covered_shed',
          has_weighing_scale: true,
          has_qc_device: true,
        },
        lead_farmer: null,
        farmer_count: 45,
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      const result = cpDetailToFormData(detail);

      expect(result.name).toBe('Nyeri Central CP');
      expect(result.status).toBe('active');
      expect(result.latitude).toBe(-0.42);
      expect(result.longitude).toBe(36.95);
      expect(result.clerk_id).toBe('CLERK-001');
      expect(result.clerk_phone).toBe('+254712345678');
      expect(result.weekday_hours).toBe('06:00-10:00');
      expect(result.weekend_hours).toBe('07:00-09:00');
      expect(result.collection_days).toEqual(['mon', 'tue', 'wed', 'thu', 'fri']);
      expect(result.max_daily_kg).toBe(500);
      expect(result.storage_type).toBe('covered_shed');
      expect(result.has_weighing_scale).toBe(true);
      expect(result.has_qc_device).toBe(true);
    });

    it('handles null clerk fields', () => {
      const detail: CollectionPointDetailFull = {
        id: 'test-cp-001',
        name: 'Test CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'test-region',
        location: { latitude: -1.0, longitude: 37.0 },
        clerk_id: null,
        clerk_phone: null,
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon'],
        capacity: {
          max_daily_kg: 100,
          storage_type: 'open_air',
          has_weighing_scale: false,
          has_qc_device: false,
        },
        lead_farmer: null,
        farmer_count: 0,
        status: 'inactive',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      const result = cpDetailToFormData(detail);

      expect(result.clerk_id).toBe('');
      expect(result.clerk_phone).toBe('');
      expect(result.status).toBe('inactive');
    });
  });

  describe('cpFormDataToUpdateRequest', () => {
    it('converts CollectionPointFormData to CollectionPointUpdateRequest', () => {
      const formData: CollectionPointFormData = {
        name: 'Updated CP Name',
        status: 'seasonal',
        latitude: -0.42,
        longitude: 36.95,
        clerk_id: 'NEW-CLERK',
        clerk_phone: '+254700000000',
        weekday_hours: '05:30-09:30',
        weekend_hours: '06:00-08:00',
        collection_days: ['mon', 'wed', 'fri'],
        max_daily_kg: 750,
        storage_type: 'refrigerated',
        has_weighing_scale: true,
        has_qc_device: false,
      };

      const result = cpFormDataToUpdateRequest(formData);

      expect(result.name).toBe('Updated CP Name');
      expect(result.status).toBe('seasonal');
      expect(result.clerk_id).toBe('NEW-CLERK');
      expect(result.clerk_phone).toBe('+254700000000');
      expect(result.operating_hours?.weekdays).toBe('05:30-09:30');
      expect(result.operating_hours?.weekends).toBe('06:00-08:00');
      expect(result.collection_days).toEqual(['mon', 'wed', 'fri']);
      expect(result.capacity?.max_daily_kg).toBe(750);
      expect(result.capacity?.storage_type).toBe('refrigerated');
      expect(result.capacity?.has_weighing_scale).toBe(true);
      expect(result.capacity?.has_qc_device).toBe(false);
    });

    it('converts empty clerk fields to null', () => {
      const formData: CollectionPointFormData = {
        name: 'Test CP',
        status: 'active',
        latitude: -1.0,
        longitude: 37.0,
        clerk_id: '',
        clerk_phone: '',
        weekday_hours: '06:00-10:00',
        weekend_hours: '07:00-09:00',
        collection_days: ['mon'],
        max_daily_kg: 100,
        storage_type: 'open_air',
        has_weighing_scale: false,
        has_qc_device: false,
      };

      const result = cpFormDataToUpdateRequest(formData);

      expect(result.clerk_id).toBeNull();
      expect(result.clerk_phone).toBeNull();
    });
  });

  describe('parseTimeRange', () => {
    it('parses standard time range', () => {
      const result = parseTimeRange('06:00-10:00');
      expect(result.start).toBe('06:00');
      expect(result.end).toBe('10:00');
    });

    it('parses time range with different hours', () => {
      const result = parseTimeRange('14:30-18:00');
      expect(result.start).toBe('14:30');
      expect(result.end).toBe('18:00');
    });

    it('handles malformed input with defaults', () => {
      const result = parseTimeRange('invalid');
      expect(result.start).toBe('invalid');
      expect(result.end).toBe('10:00'); // Uses default when split produces undefined
    });

    it('handles empty string', () => {
      const result = parseTimeRange('');
      // Empty string splits to [''], so start is '' and end is undefined -> falls back
      expect(result.start).toBe('');
      expect(result.end).toBe('10:00');
    });
  });

  describe('formatTimeRange', () => {
    it('formats start and end times into range string', () => {
      const result = formatTimeRange('06:00', '10:00');
      expect(result).toBe('06:00-10:00');
    });

    it('formats different times correctly', () => {
      const result = formatTimeRange('14:30', '18:00');
      expect(result).toBe('14:30-18:00');
    });
  });

  describe('CP_FORM_DEFAULTS', () => {
    it('has correct default values', () => {
      expect(CP_FORM_DEFAULTS.name).toBe('');
      expect(CP_FORM_DEFAULTS.status).toBe('active');
      expect(CP_FORM_DEFAULTS.weekday_hours).toBe('06:00-10:00');
      expect(CP_FORM_DEFAULTS.weekend_hours).toBe('07:00-09:00');
      expect(CP_FORM_DEFAULTS.max_daily_kg).toBe(500);
      expect(CP_FORM_DEFAULTS.storage_type).toBe('covered_shed');
      expect(CP_FORM_DEFAULTS.has_weighing_scale).toBe(true);
      expect(CP_FORM_DEFAULTS.has_qc_device).toBe(true);
    });

    it('has 6 default collection days (Mon-Sat)', () => {
      expect(CP_FORM_DEFAULTS.collection_days).toHaveLength(6);
      expect(CP_FORM_DEFAULTS.collection_days).toContain('mon');
      expect(CP_FORM_DEFAULTS.collection_days).toContain('sat');
      expect(CP_FORM_DEFAULTS.collection_days).not.toContain('sun');
    });
  });

  describe('COLLECTION_DAYS constant', () => {
    it('contains all 7 days', () => {
      expect(COLLECTION_DAYS).toHaveLength(7);
      expect(COLLECTION_DAYS).toContain('mon');
      expect(COLLECTION_DAYS).toContain('tue');
      expect(COLLECTION_DAYS).toContain('wed');
      expect(COLLECTION_DAYS).toContain('thu');
      expect(COLLECTION_DAYS).toContain('fri');
      expect(COLLECTION_DAYS).toContain('sat');
      expect(COLLECTION_DAYS).toContain('sun');
    });

    it('days are in correct order', () => {
      expect(COLLECTION_DAYS[0]).toBe('mon');
      expect(COLLECTION_DAYS[6]).toBe('sun');
    });
  });

  describe('STORAGE_TYPE_OPTIONS constant', () => {
    it('contains all storage types', () => {
      expect(STORAGE_TYPE_OPTIONS).toHaveLength(3);
      const values = STORAGE_TYPE_OPTIONS.map((opt) => opt.value);
      expect(values).toContain('open_air');
      expect(values).toContain('covered_shed');
      expect(values).toContain('refrigerated');
    });

    it('has human-readable labels', () => {
      const labels = STORAGE_TYPE_OPTIONS.map((opt) => opt.label);
      expect(labels).toContain('Open Air');
      expect(labels).toContain('Covered Shed');
      expect(labels).toContain('Refrigerated');
    });
  });
});
