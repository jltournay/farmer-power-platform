/**
 * Unit tests for Factory API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.3 - Factory Management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  listFactories,
  getFactory,
  createFactory,
  updateFactory,
  createCollectionPoint,
} from '../../../../../web/platform-admin/src/api/factories';
import type {
  FactoryListResponse,
  FactoryDetail,
  FactoryCreateRequest,
  FactoryUpdateRequest,
  CollectionPointCreateRequest,
  CollectionPointDetail,
} from '../../../../../web/platform-admin/src/api/types';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('Factory API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('listFactories', () => {
    it('should fetch factories list successfully', async () => {
      const mockResponse: FactoryListResponse = {
        data: [
          {
            id: 'KEN-FAC-001',
            name: 'Test Factory',
            code: 'TF-001',
            region_id: 'KEN-REG-001',
            collection_point_count: 3,
            farmer_count: 150,
            is_active: true,
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 25,
          page: 1,
          has_more: false,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listFactories({ page_size: 25 });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/factories', { page_size: 25 });
      expect(result).toEqual(mockResponse);
      expect(result.data).toHaveLength(1);
    });

    it('should pass region filter when provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { data: [], pagination: { total_count: 0, page_size: 25, page: 1, has_more: false } },
      });

      await listFactories({ region_id: 'KEN-REG-001', active_only: true });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/factories', {
        region_id: 'KEN-REG-001',
        active_only: true,
      });
    });
  });

  describe('getFactory', () => {
    it('should fetch factory detail successfully', async () => {
      const mockFactory: FactoryDetail = {
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

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockFactory });

      const result = await getFactory('KEN-FAC-001');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/factories/KEN-FAC-001');
      expect(result).toEqual(mockFactory);
      expect(result.quality_thresholds.tier_1).toBe(85);
    });
  });

  describe('createFactory', () => {
    it('should create factory successfully', async () => {
      const createRequest: FactoryCreateRequest = {
        name: 'New Factory',
        code: 'NF-001',
        region_id: 'KEN-REG-001',
        location: { latitude: -1.0, longitude: 37.0 },
        contact: { phone: '', email: '', address: '' },
        processing_capacity_kg: 3000,
        quality_thresholds: { tier_1: 85, tier_2: 70, tier_3: 50 },
        payment_policy: {
          policy_type: 'feedback_only',
          tier_1_adjustment: 0,
          tier_2_adjustment: 0,
          tier_3_adjustment: 0,
          below_tier_3_adjustment: 0,
        },
      };

      const mockCreated: FactoryDetail = {
        ...createRequest,
        id: 'KEN-FAC-002',
        location: { latitude: -1.0, longitude: 37.0, altitude_meters: 1800 },
        contact: { phone: '', email: '', address: '' },
        quality_thresholds: { tier_1: 85, tier_2: 70, tier_3: 50 },
        payment_policy: {
          policy_type: 'feedback_only',
          tier_1_adjustment: 0,
          tier_2_adjustment: 0,
          tier_3_adjustment: 0,
          below_tier_3_adjustment: 0,
        },
        grading_model: null,
        collection_point_count: 0,
        farmer_count: 0,
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCreated });

      const result = await createFactory(createRequest);

      expect(apiClient.post).toHaveBeenCalledWith('/admin/factories', createRequest);
      expect(result.id).toBe('KEN-FAC-002');
      expect(result.is_active).toBe(true);
    });
  });

  describe('updateFactory', () => {
    it('should update factory successfully', async () => {
      const updateRequest: FactoryUpdateRequest = {
        name: 'Updated Factory Name',
        processing_capacity_kg: 6000,
      };

      const mockUpdated: FactoryDetail = {
        id: 'KEN-FAC-001',
        name: 'Updated Factory Name',
        code: 'TF-001',
        region_id: 'KEN-REG-001',
        location: { latitude: -1.0, longitude: 37.0, altitude_meters: 1850 },
        contact: { phone: '', email: '', address: '' },
        processing_capacity_kg: 6000,
        quality_thresholds: { tier_1: 85, tier_2: 70, tier_3: 50 },
        payment_policy: {
          policy_type: 'feedback_only',
          tier_1_adjustment: 0,
          tier_2_adjustment: 0,
          tier_3_adjustment: 0,
          below_tier_3_adjustment: 0,
        },
        grading_model: null,
        collection_point_count: 3,
        farmer_count: 150,
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateFactory('KEN-FAC-001', updateRequest);

      expect(apiClient.put).toHaveBeenCalledWith('/admin/factories/KEN-FAC-001', updateRequest);
      expect(result.name).toBe('Updated Factory Name');
      expect(result.processing_capacity_kg).toBe(6000);
    });

    it('should update factory status to inactive', async () => {
      const updateRequest: FactoryUpdateRequest = {
        is_active: false,
      };

      const mockUpdated: FactoryDetail = {
        id: 'KEN-FAC-001',
        name: 'Test Factory',
        code: 'TF-001',
        region_id: 'KEN-REG-001',
        location: { latitude: -1.0, longitude: 37.0, altitude_meters: 1850 },
        contact: { phone: '', email: '', address: '' },
        processing_capacity_kg: 5000,
        quality_thresholds: { tier_1: 85, tier_2: 70, tier_3: 50 },
        payment_policy: {
          policy_type: 'feedback_only',
          tier_1_adjustment: 0,
          tier_2_adjustment: 0,
          tier_3_adjustment: 0,
          below_tier_3_adjustment: 0,
        },
        grading_model: null,
        collection_point_count: 3,
        farmer_count: 150,
        is_active: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateFactory('KEN-FAC-001', updateRequest);

      expect(result.is_active).toBe(false);
    });
  });

  describe('createCollectionPoint', () => {
    it('should create collection point under factory', async () => {
      const createRequest: CollectionPointCreateRequest = {
        name: 'New CP',
        location: { latitude: -1.1, longitude: 37.1 },
        region_id: 'KEN-REG-001',
        status: 'active',
      };

      const mockCreated: CollectionPointDetail = {
        id: 'KEN-REG-001-CP-001',
        name: 'New CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'KEN-REG-001',
        location: { latitude: -1.1, longitude: 37.1, altitude_meters: 1750 },
        clerk_id: null,
        clerk_phone: null,
        farmer_count: 0,
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCreated });

      const result = await createCollectionPoint('KEN-FAC-001', createRequest);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/admin/factories/KEN-FAC-001/collection-points',
        createRequest
      );
      expect(result.factory_id).toBe('KEN-FAC-001');
      expect(result.name).toBe('New CP');
    });
  });

  describe('Error handling', () => {
    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(getFactory('KEN-FAC-001')).rejects.toThrow('Network error');
    });

    it('should throw error on 404 response', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Factory not found'));

      await expect(getFactory('KEN-FAC-999')).rejects.toThrow('Factory not found');
    });
  });
});
