/**
 * Unit tests for Factory type conversion helpers
 *
 * Tests type conversion functions for form data transformation.
 * Story 9.3 - Factory Management
 */

import { describe, it, expect } from 'vitest';
import {
  factoryDetailToFormData,
  factoryFormDataToCreateRequest,
  factoryFormDataToUpdateRequest,
  FACTORY_FORM_DEFAULTS,
  type FactoryDetail,
  type FactoryFormData,
} from '../../../../../web/platform-admin/src/api/types';

describe('Factory Type Conversion Helpers', () => {
  const mockFactoryDetail: FactoryDetail = {
    id: 'KEN-FAC-001',
    name: 'Test Factory',
    code: 'TF-001',
    region_id: 'KEN-REG-001',
    location: { latitude: -1.0, longitude: 37.0, altitude_meters: 1850 },
    contact: { phone: '+254712345678', email: 'test@factory.co.ke', address: 'Test Address' },
    processing_capacity_kg: 5000,
    quality_thresholds: { tier_1: 85, tier_2: 70, tier_3: 50 },
    payment_policy: {
      policy_type: 'weekly_bonus',
      tier_1_adjustment: 0.15,
      tier_2_adjustment: 0,
      tier_3_adjustment: -0.05,
      below_tier_3_adjustment: -0.1,
    },
    grading_model: null,
    collection_point_count: 3,
    farmer_count: 150,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  describe('FACTORY_FORM_DEFAULTS', () => {
    it('should have correct default values', () => {
      expect(FACTORY_FORM_DEFAULTS.name).toBe('');
      expect(FACTORY_FORM_DEFAULTS.code).toBe('');
      expect(FACTORY_FORM_DEFAULTS.tier_1).toBe(85);
      expect(FACTORY_FORM_DEFAULTS.tier_2).toBe(70);
      expect(FACTORY_FORM_DEFAULTS.tier_3).toBe(50);
      expect(FACTORY_FORM_DEFAULTS.policy_type).toBe('feedback_only');
      expect(FACTORY_FORM_DEFAULTS.is_active).toBe(true);
    });
  });

  describe('factoryDetailToFormData', () => {
    it('should convert FactoryDetail to FormData correctly', () => {
      const formData = factoryDetailToFormData(mockFactoryDetail);

      expect(formData.name).toBe('Test Factory');
      expect(formData.code).toBe('TF-001');
      expect(formData.region_id).toBe('KEN-REG-001');
      expect(formData.latitude).toBe(-1.0);
      expect(formData.longitude).toBe(37.0);
      expect(formData.phone).toBe('+254712345678');
      expect(formData.email).toBe('test@factory.co.ke');
      expect(formData.address).toBe('Test Address');
      expect(formData.processing_capacity_kg).toBe(5000);
      expect(formData.tier_1).toBe(85);
      expect(formData.tier_2).toBe(70);
      expect(formData.tier_3).toBe(50);
      expect(formData.policy_type).toBe('weekly_bonus');
      expect(formData.tier_1_adjustment).toBe(0.15);
      expect(formData.tier_2_adjustment).toBe(0);
      expect(formData.tier_3_adjustment).toBe(-0.05);
      expect(formData.below_tier_3_adjustment).toBe(-0.1);
      expect(formData.is_active).toBe(true);
    });

    it('should handle empty contact fields', () => {
      const factoryWithEmptyContact: FactoryDetail = {
        ...mockFactoryDetail,
        contact: { phone: '', email: '', address: '' },
      };

      const formData = factoryDetailToFormData(factoryWithEmptyContact);

      expect(formData.phone).toBe('');
      expect(formData.email).toBe('');
      expect(formData.address).toBe('');
    });
  });

  describe('factoryFormDataToCreateRequest', () => {
    const formData: FactoryFormData = {
      name: 'New Factory',
      code: 'NF-001',
      region_id: 'KEN-REG-002',
      latitude: -0.5,
      longitude: 36.5,
      phone: '+254700000000',
      email: 'new@factory.co.ke',
      address: 'New Address',
      processing_capacity_kg: 3000,
      tier_1: 90,
      tier_2: 75,
      tier_3: 55,
      policy_type: 'split_payment',
      tier_1_adjustment: 0.2,
      tier_2_adjustment: 0.05,
      tier_3_adjustment: -0.03,
      below_tier_3_adjustment: -0.08,
      is_active: true,
    };

    it('should convert FormData to CreateRequest correctly', () => {
      const request = factoryFormDataToCreateRequest(formData);

      expect(request.name).toBe('New Factory');
      expect(request.code).toBe('NF-001');
      expect(request.region_id).toBe('KEN-REG-002');
      expect(request.location.latitude).toBe(-0.5);
      expect(request.location.longitude).toBe(36.5);
      expect(request.contact?.phone).toBe('+254700000000');
      expect(request.contact?.email).toBe('new@factory.co.ke');
      expect(request.contact?.address).toBe('New Address');
      expect(request.processing_capacity_kg).toBe(3000);
      expect(request.quality_thresholds?.tier_1).toBe(90);
      expect(request.quality_thresholds?.tier_2).toBe(75);
      expect(request.quality_thresholds?.tier_3).toBe(55);
      expect(request.payment_policy?.policy_type).toBe('split_payment');
      expect(request.payment_policy?.tier_1_adjustment).toBe(0.2);
    });
  });

  describe('factoryFormDataToUpdateRequest', () => {
    it('should only include provided fields in update request', () => {
      const partialData = {
        name: 'Updated Name',
        processing_capacity_kg: 7000,
      };

      const request = factoryFormDataToUpdateRequest(partialData);

      expect(request.name).toBe('Updated Name');
      expect(request.processing_capacity_kg).toBe(7000);
      expect(request.code).toBeUndefined();
      expect(request.location).toBeUndefined();
      expect(request.contact).toBeUndefined();
    });

    it('should include location when both lat and lng provided', () => {
      const partialData = {
        latitude: -1.5,
        longitude: 37.5,
      };

      const request = factoryFormDataToUpdateRequest(partialData);

      expect(request.location).toBeDefined();
      expect(request.location?.latitude).toBe(-1.5);
      expect(request.location?.longitude).toBe(37.5);
    });

    it('should include contact when any contact field provided', () => {
      const partialData = {
        phone: '+254111111111',
      };

      const request = factoryFormDataToUpdateRequest(partialData);

      expect(request.contact).toBeDefined();
      expect(request.contact?.phone).toBe('+254111111111');
      expect(request.contact?.email).toBe('');
      expect(request.contact?.address).toBe('');
    });

    it('should include thresholds when all tier values provided', () => {
      const partialData = {
        tier_1: 88,
        tier_2: 73,
        tier_3: 53,
      };

      const request = factoryFormDataToUpdateRequest(partialData);

      expect(request.quality_thresholds).toBeDefined();
      expect(request.quality_thresholds?.tier_1).toBe(88);
      expect(request.quality_thresholds?.tier_2).toBe(73);
      expect(request.quality_thresholds?.tier_3).toBe(53);
    });

    it('should include payment policy when policy_type provided', () => {
      const partialData = {
        policy_type: 'weekly_bonus' as const,
        tier_1_adjustment: 0.12,
        tier_2_adjustment: 0.02,
      };

      const request = factoryFormDataToUpdateRequest(partialData);

      expect(request.payment_policy).toBeDefined();
      expect(request.payment_policy?.policy_type).toBe('weekly_bonus');
      expect(request.payment_policy?.tier_1_adjustment).toBe(0.12);
      expect(request.payment_policy?.tier_2_adjustment).toBe(0.02);
    });

    it('should include is_active when explicitly set', () => {
      const request = factoryFormDataToUpdateRequest({ is_active: false });
      expect(request.is_active).toBe(false);

      const request2 = factoryFormDataToUpdateRequest({ is_active: true });
      expect(request2.is_active).toBe(true);
    });
  });
});
