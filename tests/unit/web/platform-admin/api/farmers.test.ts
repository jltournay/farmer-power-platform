/**
 * Unit tests for Farmers API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.5 - Farmer Management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  listFarmers,
  getFarmer,
  createFarmer,
  updateFarmer,
} from '../../../../../web/platform-admin/src/api/farmers';
import type {
  FarmerDetail,
  FarmerListResponse,
  FarmerCreateRequest,
  FarmerUpdateRequest,
} from '../../../../../web/platform-admin/src/api/types';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('Farmers API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('listFarmers', () => {
    it('should fetch farmers list with pagination', async () => {
      const mockResponse: FarmerListResponse = {
        data: [
          {
            id: 'WM-0001',
            name: 'John Doe',
            phone: '+254712345678',
            collection_point_id: 'nyeri-highland-cp-001',
            region_id: 'nyeri-highland',
            farm_scale: 'smallholder',
            tier: 'premium',
            trend: 'improving',
            is_active: true,
          },
          {
            id: 'WM-0002',
            name: 'Jane Smith',
            phone: '+254712345679',
            collection_point_id: 'nyeri-highland-cp-001',
            region_id: 'nyeri-highland',
            farm_scale: 'medium',
            tier: 'standard',
            trend: 'stable',
            is_active: true,
          },
        ],
        pagination: {
          total_count: 2,
          page_size: 25,
          page: 1,
          next_page_token: null,
          has_next: false,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listFarmers({ page_size: 25 });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/farmers', { page_size: 25 });
      expect(result.data).toHaveLength(2);
      expect(result.data[0].tier).toBe('premium');
    });

    it('should pass filter parameters', async () => {
      const mockResponse: FarmerListResponse = {
        data: [],
        pagination: {
          total_count: 0,
          page_size: 25,
          page: 1,
          next_page_token: null,
          has_next: false,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listFarmers({
        region_id: 'nyeri-highland',
        tier: 'premium',
        farm_scale: 'smallholder',
        active_only: true,
        search: 'John',
      });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/farmers', {
        region_id: 'nyeri-highland',
        tier: 'premium',
        farm_scale: 'smallholder',
        active_only: true,
        search: 'John',
      });
    });
  });

  describe('getFarmer', () => {
    it('should fetch farmer detail successfully', async () => {
      const mockFarmer: FarmerDetail = {
        id: 'WM-0001',
        grower_number: 'GRW001',
        first_name: 'John',
        last_name: 'Doe',
        phone: '+254712345678',
        national_id: '12345678',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
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

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockFarmer });

      const result = await getFarmer('WM-0001');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/farmers/WM-0001');
      expect(result).toEqual(mockFarmer);
      expect(result.performance.tier).toBe('premium');
      expect(result.communication_prefs.pref_lang).toBe('sw');
    });

    it('should handle farmer without grower number', async () => {
      const mockFarmer: FarmerDetail = {
        id: 'WM-0002',
        grower_number: null,
        first_name: 'Jane',
        last_name: 'Smith',
        phone: '+254712345679',
        national_id: '87654321',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
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

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockFarmer });

      const result = await getFarmer('WM-0002');

      expect(result.grower_number).toBeNull();
    });
  });

  describe('createFarmer', () => {
    it('should create farmer successfully', async () => {
      const createRequest: FarmerCreateRequest = {
        first_name: 'New',
        last_name: 'Farmer',
        phone: '+254712345680',
        national_id: '11111111',
        collection_point_id: 'nyeri-highland-cp-001',
        farm_size_hectares: 0.5,
        latitude: -0.44,
        longitude: 36.97,
        notification_channel: 'sms',
        interaction_pref: 'text',
        pref_lang: 'swahili',
      };

      const mockCreated: FarmerDetail = {
        id: 'WM-0003',
        grower_number: null,
        first_name: 'New',
        last_name: 'Farmer',
        phone: '+254712345680',
        national_id: '11111111',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
        farm_location: { latitude: -0.44, longitude: 36.97 },
        farm_size_hectares: 0.5,
        farm_scale: 'smallholder',
        performance: {
          primary_percentage_30d: 0,
          primary_percentage_90d: 0,
          total_kg_30d: 0,
          total_kg_90d: 0,
          tier: 'standard',
          trend: 'stable',
          deliveries_today: 0,
          kg_today: 0,
        },
        communication_prefs: {
          notification_channel: 'sms',
          interaction_pref: 'text',
          pref_lang: 'sw',
        },
        is_active: true,
        registration_date: '2026-01-17T00:00:00Z',
        created_at: '2026-01-17T00:00:00Z',
        updated_at: '2026-01-17T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCreated });

      const result = await createFarmer(createRequest);

      expect(apiClient.post).toHaveBeenCalledWith('/admin/farmers', createRequest);
      expect(result.id).toBe('WM-0003');
      expect(result.farm_scale).toBe('smallholder');
    });

    it('should create farmer with grower number', async () => {
      const createRequest: FarmerCreateRequest = {
        first_name: 'Legacy',
        last_name: 'Farmer',
        phone: '+254712345681',
        national_id: '22222222',
        collection_point_id: 'nyeri-highland-cp-001',
        farm_size_hectares: 3.0,
        latitude: -0.45,
        longitude: 36.98,
        grower_number: 'GRW999',
      };

      const mockCreated: FarmerDetail = {
        id: 'WM-0004',
        grower_number: 'GRW999',
        first_name: 'Legacy',
        last_name: 'Farmer',
        phone: '+254712345681',
        national_id: '22222222',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
        farm_location: { latitude: -0.45, longitude: 36.98 },
        farm_size_hectares: 3.0,
        farm_scale: 'large',
        performance: {
          primary_percentage_30d: 0,
          primary_percentage_90d: 0,
          total_kg_30d: 0,
          total_kg_90d: 0,
          tier: 'standard',
          trend: 'stable',
          deliveries_today: 0,
          kg_today: 0,
        },
        communication_prefs: {
          notification_channel: 'sms',
          interaction_pref: 'text',
          pref_lang: 'sw',
        },
        is_active: true,
        registration_date: '2026-01-17T00:00:00Z',
        created_at: '2026-01-17T00:00:00Z',
        updated_at: '2026-01-17T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCreated });

      const result = await createFarmer(createRequest);

      expect(result.grower_number).toBe('GRW999');
    });
  });

  describe('updateFarmer', () => {
    it('should update farmer successfully', async () => {
      const updateRequest: FarmerUpdateRequest = {
        first_name: 'Updated',
        last_name: 'Name',
        phone: '+254712345690',
      };

      const mockUpdated: FarmerDetail = {
        id: 'WM-0001',
        grower_number: 'GRW001',
        first_name: 'Updated',
        last_name: 'Name',
        phone: '+254712345690',
        national_id: '12345678',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
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
        updated_at: '2026-01-17T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateFarmer('WM-0001', updateRequest);

      expect(apiClient.put).toHaveBeenCalledWith('/admin/farmers/WM-0001', updateRequest);
      expect(result.first_name).toBe('Updated');
      expect(result.phone).toBe('+254712345690');
    });

    it('should deactivate farmer', async () => {
      const updateRequest: FarmerUpdateRequest = {
        is_active: false,
      };

      const mockUpdated: FarmerDetail = {
        id: 'WM-0001',
        grower_number: 'GRW001',
        first_name: 'John',
        last_name: 'Doe',
        phone: '+254712345678',
        national_id: '12345678',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
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
        is_active: false,
        registration_date: '2025-01-15T00:00:00Z',
        created_at: '2025-01-15T00:00:00Z',
        updated_at: '2026-01-17T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateFarmer('WM-0001', updateRequest);

      expect(result.is_active).toBe(false);
    });

    it('should update communication preferences', async () => {
      const updateRequest: FarmerUpdateRequest = {
        notification_channel: 'whatsapp',
        interaction_pref: 'voice',
        pref_lang: 'english',
      };

      const mockUpdated: FarmerDetail = {
        id: 'WM-0001',
        grower_number: 'GRW001',
        first_name: 'John',
        last_name: 'Doe',
        phone: '+254712345678',
        national_id: '12345678',
        region_id: 'nyeri-highland',
        collection_point_id: 'nyeri-highland-cp-001',
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
          notification_channel: 'whatsapp',
          interaction_pref: 'voice',
          pref_lang: 'en',
        },
        is_active: true,
        registration_date: '2025-01-15T00:00:00Z',
        created_at: '2025-01-15T00:00:00Z',
        updated_at: '2026-01-17T00:00:00Z',
      };

      vi.mocked(apiClient.put).mockResolvedValue({ data: mockUpdated });

      const result = await updateFarmer('WM-0001', updateRequest);

      expect(result.communication_prefs.notification_channel).toBe('whatsapp');
      expect(result.communication_prefs.interaction_pref).toBe('voice');
      expect(result.communication_prefs.pref_lang).toBe('en');
    });
  });

  describe('Error handling', () => {
    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(getFarmer('WM-0001')).rejects.toThrow('Network error');
    });

    it('should throw error on 404 response', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Farmer not found'));

      await expect(getFarmer('WM-9999')).rejects.toThrow('Farmer not found');
    });

    it('should throw error on create failure', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(
        new Error('Phone number already registered')
      );

      const createRequest: FarmerCreateRequest = {
        first_name: 'Test',
        last_name: 'User',
        phone: '+254712345678', // Duplicate
        national_id: '99999999',
        collection_point_id: 'nyeri-highland-cp-001',
        farm_size_hectares: 0.5,
        latitude: -0.42,
        longitude: 36.95,
      };

      await expect(createFarmer(createRequest)).rejects.toThrow(
        'Phone number already registered'
      );
    });

    it('should throw error on update failure', async () => {
      vi.mocked(apiClient.put).mockRejectedValue(
        new Error('Invalid phone format')
      );

      await expect(
        updateFarmer('WM-0001', { phone: 'invalid' })
      ).rejects.toThrow('Invalid phone format');
    });
  });
});
