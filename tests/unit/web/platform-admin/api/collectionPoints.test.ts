/**
 * Unit tests for Collection Points API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.4 - Collection Point Management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  getCollectionPoint,
  updateCollectionPoint,
  listCollectionPoints,
} from '../../../../../web/platform-admin/src/api/collectionPoints';
import type {
  CollectionPointDetailFull,
  CollectionPointListResponse,
  CollectionPointUpdateRequest,
} from '../../../../../web/platform-admin/src/api/types';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('Collection Points API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('getCollectionPoint', () => {
    it('should fetch collection point detail successfully', async () => {
      const mockCP: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-001',
        name: 'Nyeri Central Collection Point',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.42, longitude: 36.95, altitude_meters: 1850 },
        clerk_id: 'CLERK-001',
        clerk_phone: '+254712345678',
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'],
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

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCP });

      const result = await getCollectionPoint('nyeri-highland-cp-001');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/collection-points/nyeri-highland-cp-001');
      expect(result).toEqual(mockCP);
      expect(result.operating_hours.weekdays).toBe('06:00-10:00');
      expect(result.capacity.has_qc_device).toBe(true);
    });

    it('should include lead farmer when assigned', async () => {
      const mockCP: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-002',
        name: 'Secondary CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.43, longitude: 36.96 },
        clerk_id: null,
        clerk_phone: null,
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon', 'wed', 'fri'],
        capacity: {
          max_daily_kg: 300,
          storage_type: 'open_air',
          has_weighing_scale: true,
          has_qc_device: false,
        },
        lead_farmer: {
          id: 'FARMER-123',
          name: 'Jane Wanjiku',
          phone: '+254700123456',
        },
        farmer_count: 30,
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCP });

      const result = await getCollectionPoint('nyeri-highland-cp-002');

      expect(result.lead_farmer).not.toBeNull();
      expect(result.lead_farmer?.name).toBe('Jane Wanjiku');
    });
  });

  describe('updateCollectionPoint', () => {
    it('should update collection point successfully', async () => {
      const updateRequest: CollectionPointUpdateRequest = {
        name: 'Updated CP Name',
        operating_hours: {
          weekdays: '05:30-09:30',
          weekends: '06:00-08:00',
        },
      };

      const mockUpdated: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-001',
        name: 'Updated CP Name',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.42, longitude: 36.95 },
        clerk_id: null,
        clerk_phone: null,
        operating_hours: {
          weekdays: '05:30-09:30',
          weekends: '06:00-08:00',
        },
        collection_days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'],
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
        updated_at: '2026-01-02T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateCollectionPoint('nyeri-highland-cp-001', updateRequest);

      expect(apiClient.put).toHaveBeenCalledWith(
        '/admin/collection-points/nyeri-highland-cp-001',
        updateRequest
      );
      expect(result.name).toBe('Updated CP Name');
      expect(result.operating_hours.weekdays).toBe('05:30-09:30');
    });

    it('should update status to inactive', async () => {
      const updateRequest: CollectionPointUpdateRequest = {
        status: 'inactive',
      };

      const mockUpdated: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-001',
        name: 'Test CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.42, longitude: 36.95 },
        clerk_id: null,
        clerk_phone: null,
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon', 'tue', 'wed'],
        capacity: {
          max_daily_kg: 500,
          storage_type: 'covered_shed',
          has_weighing_scale: true,
          has_qc_device: true,
        },
        lead_farmer: null,
        farmer_count: 45,
        status: 'inactive',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateCollectionPoint('nyeri-highland-cp-001', updateRequest);

      expect(result.status).toBe('inactive');
    });

    it('should update capacity and equipment', async () => {
      const updateRequest: CollectionPointUpdateRequest = {
        capacity: {
          max_daily_kg: 1000,
          storage_type: 'refrigerated',
          has_weighing_scale: true,
          has_qc_device: true,
        },
      };

      const mockUpdated: CollectionPointDetailFull = {
        id: 'nyeri-highland-cp-001',
        name: 'Test CP',
        factory_id: 'KEN-FAC-001',
        region_id: 'nyeri-highland',
        location: { latitude: -0.42, longitude: 36.95 },
        clerk_id: null,
        clerk_phone: null,
        operating_hours: {
          weekdays: '06:00-10:00',
          weekends: '07:00-09:00',
        },
        collection_days: ['mon', 'tue', 'wed'],
        capacity: {
          max_daily_kg: 1000,
          storage_type: 'refrigerated',
          has_weighing_scale: true,
          has_qc_device: true,
        },
        lead_farmer: null,
        farmer_count: 45,
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateCollectionPoint('nyeri-highland-cp-001', updateRequest);

      expect(result.capacity.max_daily_kg).toBe(1000);
      expect(result.capacity.storage_type).toBe('refrigerated');
    });
  });

  describe('listCollectionPoints', () => {
    it('should fetch collection points list for factory', async () => {
      const mockResponse: CollectionPointListResponse = {
        data: [
          {
            id: 'nyeri-highland-cp-001',
            name: 'CP 1',
            factory_id: 'KEN-FAC-001',
            region_id: 'nyeri-highland',
            farmer_count: 45,
            status: 'active',
          },
          {
            id: 'nyeri-highland-cp-002',
            name: 'CP 2',
            factory_id: 'KEN-FAC-001',
            region_id: 'nyeri-highland',
            farmer_count: 30,
            status: 'seasonal',
          },
        ],
        pagination: {
          total_count: 2,
          page_size: 50,
          page: 1,
          next_page_token: null,
          has_next: false,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listCollectionPoints({ factory_id: 'KEN-FAC-001' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/collection-points', {
        factory_id: 'KEN-FAC-001',
      });
      expect(result.data).toHaveLength(2);
      expect(result.data[0].status).toBe('active');
      expect(result.data[1].status).toBe('seasonal');
    });

    it('should pass pagination parameters', async () => {
      const mockResponse: CollectionPointListResponse = {
        data: [],
        pagination: {
          total_count: 0,
          page_size: 10,
          page: 1,
          next_page_token: null,
          has_next: false,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listCollectionPoints({
        factory_id: 'KEN-FAC-001',
        page_size: 10,
        active_only: true,
      });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/collection-points', {
        factory_id: 'KEN-FAC-001',
        page_size: 10,
        active_only: true,
      });
    });
  });

  describe('Error handling', () => {
    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(getCollectionPoint('nyeri-highland-cp-001')).rejects.toThrow('Network error');
    });

    it('should throw error on 404 response', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Collection Point not found'));

      await expect(getCollectionPoint('nonexistent-cp-999')).rejects.toThrow(
        'Collection Point not found'
      );
    });

    it('should throw error on update failure', async () => {
      vi.mocked(apiClient.put).mockRejectedValue(new Error('Validation error'));

      await expect(
        updateCollectionPoint('nyeri-highland-cp-001', { status: 'invalid' as any })
      ).rejects.toThrow('Validation error');
    });
  });
});
