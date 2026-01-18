/**
 * Unit tests for Farmer type conversion helpers
 *
 * Tests form data conversion functions.
 * Story 9.5 - Farmer Management
 */

import { describe, it, expect } from 'vitest';
import {
  farmerFormDataToCreateRequest,
  farmerDetailToFormData,
  farmerFormDataToUpdateRequest,
  getTierColor,
  getTrendColor,
  getTrendIcon,
  FARMER_FORM_DEFAULTS,
  type FarmerDetail,
  type FarmerFormData,
} from '../../../../../web/platform-admin/src/api/types';

describe('Farmer Type Helpers', () => {
  describe('FARMER_FORM_DEFAULTS', () => {
    it('should have correct default values', () => {
      expect(FARMER_FORM_DEFAULTS.phone).toBe('+254');
      expect(FARMER_FORM_DEFAULTS.notification_channel).toBe('sms');
      expect(FARMER_FORM_DEFAULTS.interaction_pref).toBe('text');
      expect(FARMER_FORM_DEFAULTS.pref_lang).toBe('sw');
      expect(FARMER_FORM_DEFAULTS.farm_size_hectares).toBe(0.5);
    });
  });

  describe('farmerFormDataToCreateRequest', () => {
    it('should convert form data to create request', () => {
      // Story 9.5a: collection_point_id removed from form data (N:M model)
      const formData: FarmerFormData = {
        first_name: 'John',
        last_name: 'Doe',
        phone: '+254712345678',
        national_id: '12345678',
        farm_size_hectares: 1.5,
        latitude: -0.42,
        longitude: 36.95,
        grower_number: 'GRW001',
        notification_channel: 'sms',
        interaction_pref: 'text',
        pref_lang: 'sw',
      };

      const result = farmerFormDataToCreateRequest(formData);

      expect(result.first_name).toBe('John');
      expect(result.last_name).toBe('Doe');
      expect(result.phone).toBe('+254712345678');
      expect(result.national_id).toBe('12345678');
      // Story 9.5a: collection_point_id removed - assigned via delivery or separate API
      expect(result.farm_size_hectares).toBe(1.5);
      expect(result.latitude).toBe(-0.42);
      expect(result.longitude).toBe(36.95);
      expect(result.grower_number).toBe('GRW001');
      expect(result.notification_channel).toBe('sms');
    });

    it('should set grower_number to null when empty string', () => {
      // Story 9.5a: collection_point_id removed from form data (N:M model)
      const formData: FarmerFormData = {
        first_name: 'Jane',
        last_name: 'Smith',
        phone: '+254712345679',
        national_id: '87654321',
        farm_size_hectares: 2.0,
        latitude: -0.43,
        longitude: 36.96,
        grower_number: '',
        notification_channel: 'whatsapp',
        interaction_pref: 'voice',
        pref_lang: 'en',
      };

      const result = farmerFormDataToCreateRequest(formData);

      expect(result.grower_number).toBeNull();
    });
  });

  describe('farmerDetailToFormData', () => {
    it('should convert farmer detail to form data', () => {
      // Story 9.5a: FarmerDetail uses collection_points array instead of collection_point_id
      const detail: FarmerDetail = {
        id: 'WM-0001',
        grower_number: 'GRW001',
        first_name: 'John',
        last_name: 'Doe',
        phone: '+254712345678',
        national_id: '12345678',
        region_id: 'nyeri-highland',
        collection_points: [
          { id: 'nyeri-highland-cp-001', name: 'Nyeri Central CP', factory_id: 'NTF-001' },
        ],
        cp_count: 1,
        farm_location: { latitude: -0.42, longitude: 36.95 },
        farm_size_hectares: 1.5,
        farm_scale: 'smallholder',
        performance: {
          primary_percentage_30d: 87.5,
          primary_percentage_90d: 85.0,
          total_kg_30d: 450,
          total_kg_90d: 1200,
          tier: 'premium',
          trend: 'improving',
          deliveries_today: 2,
          kg_today: 15.5,
        },
        communication_prefs: {
          notification_channel: 'sms',
          interaction_pref: 'text',
          pref_lang: 'sw',
        },
        is_active: true,
        registration_date: '2025-01-15T00:00:00Z',
        created_at: '2025-01-15T00:00:00Z',
        updated_at: '2025-01-15T00:00:00Z',
      };

      const result = farmerDetailToFormData(detail);

      expect(result.first_name).toBe('John');
      expect(result.last_name).toBe('Doe');
      expect(result.phone).toBe('+254712345678');
      expect(result.national_id).toBe('12345678');
      // Story 9.5a: collection_point_id removed from form data - use collection_points on detail
      expect(result.farm_size_hectares).toBe(1.5);
      expect(result.latitude).toBe(-0.42);
      expect(result.longitude).toBe(36.95);
      expect(result.grower_number).toBe('GRW001');
      expect(result.notification_channel).toBe('sms');
      expect(result.interaction_pref).toBe('text');
      expect(result.pref_lang).toBe('sw');
    });

    it('should handle null grower_number', () => {
      // Story 9.5a: FarmerDetail uses collection_points array instead of collection_point_id
      const detail: FarmerDetail = {
        id: 'WM-0002',
        grower_number: null,
        first_name: 'Jane',
        last_name: 'Smith',
        phone: '+254712345679',
        national_id: '87654321',
        region_id: 'nyeri-highland',
        collection_points: [], // No delivery history yet
        cp_count: 0,
        farm_location: { latitude: -0.43, longitude: 36.96 },
        farm_size_hectares: 2.0,
        farm_scale: 'medium',
        performance: {
          primary_percentage_30d: 72.0,
          primary_percentage_90d: 70.5,
          total_kg_30d: 600,
          total_kg_90d: 1800,
          tier: 'standard',
          trend: 'stable',
          deliveries_today: 0,
          kg_today: 0,
        },
        communication_prefs: {
          notification_channel: 'whatsapp',
          interaction_pref: 'voice',
          pref_lang: 'en',
        },
        is_active: true,
        registration_date: '2025-02-01T00:00:00Z',
        created_at: '2025-02-01T00:00:00Z',
        updated_at: '2025-02-01T00:00:00Z',
      };

      const result = farmerDetailToFormData(detail);

      expect(result.grower_number).toBe('');
    });
  });

  describe('farmerFormDataToUpdateRequest', () => {
    it('should convert partial form data to update request', () => {
      const partialData: Partial<FarmerFormData> = {
        first_name: 'Updated',
        last_name: 'Name',
        phone: '+254712345690',
      };

      const result = farmerFormDataToUpdateRequest(partialData);

      expect(result.first_name).toBe('Updated');
      expect(result.last_name).toBe('Name');
      expect(result.phone).toBe('+254712345690');
      expect(result.farm_size_hectares).toBeUndefined();
    });

    it('should include communication prefs when provided', () => {
      const partialData: Partial<FarmerFormData> = {
        notification_channel: 'whatsapp',
        interaction_pref: 'voice',
        pref_lang: 'en',
      };

      const result = farmerFormDataToUpdateRequest(partialData);

      expect(result.notification_channel).toBe('whatsapp');
      expect(result.interaction_pref).toBe('voice');
      expect(result.pref_lang).toBe('en');
    });

    it('should include farm size when provided', () => {
      const partialData: Partial<FarmerFormData> = {
        farm_size_hectares: 2.5,
      };

      const result = farmerFormDataToUpdateRequest(partialData);

      expect(result.farm_size_hectares).toBe(2.5);
    });
  });

  describe('getTierColor', () => {
    it('should return success for premium tier', () => {
      expect(getTierColor('premium')).toBe('success');
    });

    it('should return warning for standard tier', () => {
      expect(getTierColor('standard')).toBe('warning');
    });

    it('should return info for acceptable tier', () => {
      expect(getTierColor('acceptable')).toBe('info');
    });

    it('should return default for below tier', () => {
      expect(getTierColor('below')).toBe('default');
    });
  });

  describe('getTrendColor', () => {
    it('should return success for improving trend', () => {
      expect(getTrendColor('improving')).toBe('success');
    });

    it('should return error for declining trend', () => {
      expect(getTrendColor('declining')).toBe('error');
    });

    it('should return default for stable trend', () => {
      expect(getTrendColor('stable')).toBe('default');
    });
  });

  describe('getTrendIcon', () => {
    it('should return TrendingUp for improving', () => {
      expect(getTrendIcon('improving')).toBe('TrendingUp');
    });

    it('should return TrendingDown for declining', () => {
      expect(getTrendIcon('declining')).toBe('TrendingDown');
    });

    it('should return TrendingFlat for stable', () => {
      expect(getTrendIcon('stable')).toBe('TrendingFlat');
    });
  });
});
