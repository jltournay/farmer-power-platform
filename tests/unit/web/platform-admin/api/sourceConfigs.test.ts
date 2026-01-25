/**
 * Unit tests for Source Configs API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.11c - Source Configuration Viewer UI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import { listSourceConfigs, getSourceConfig } from '../../../../../web/platform-admin/src/api/sourceConfigs';
import type {
  SourceConfigListResponse,
  SourceConfigDetailResponse,
} from '../../../../../web/platform-admin/src/types/source-config';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('Source Configs API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('listSourceConfigs', () => {
    it('should fetch source configs list with pagination', async () => {
      const mockResponse: SourceConfigListResponse = {
        data: [
          {
            source_id: 'qc-bag-result',
            display_name: 'QC Bag Results',
            description: 'Quality control results from Starfish',
            enabled: true,
            ingestion_mode: 'blob_trigger',
            ai_agent_id: 'quality-data-extraction',
          },
          {
            source_id: 'weather-data',
            display_name: 'Weather Data',
            description: 'Regional weather observations',
            enabled: true,
            ingestion_mode: 'scheduled_pull',
            ai_agent_id: '',
          },
        ],
        pagination: {
          total_count: 2,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listSourceConfigs({ page_size: 25 });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/source-configs', { page_size: 25 });
      expect(result.data).toHaveLength(2);
      expect(result.data[0].ingestion_mode).toBe('blob_trigger');
      expect(result.data[1].ingestion_mode).toBe('scheduled_pull');
    });

    it('should filter by enabled_only', async () => {
      const mockResponse: SourceConfigListResponse = {
        data: [
          {
            source_id: 'qc-bag-result',
            display_name: 'QC Bag Results',
            description: 'Quality control results',
            enabled: true,
            ingestion_mode: 'blob_trigger',
            ai_agent_id: 'quality-data-extraction',
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listSourceConfigs({ enabled_only: true });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/source-configs', { enabled_only: true });
    });

    it('should filter by ingestion_mode', async () => {
      const mockResponse: SourceConfigListResponse = {
        data: [
          {
            source_id: 'weather-data',
            display_name: 'Weather Data',
            description: 'Regional weather observations',
            enabled: true,
            ingestion_mode: 'scheduled_pull',
            ai_agent_id: '',
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listSourceConfigs({ ingestion_mode: 'scheduled_pull' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/source-configs', {
        ingestion_mode: 'scheduled_pull',
      });
    });

    it('should handle empty results', async () => {
      const mockResponse: SourceConfigListResponse = {
        data: [],
        pagination: {
          total_count: 0,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listSourceConfigs();

      expect(result.data).toHaveLength(0);
      expect(result.pagination.total_count).toBe(0);
    });
  });

  describe('getSourceConfig', () => {
    it('should fetch blob_trigger source config detail', async () => {
      const mockConfig: SourceConfigDetailResponse = {
        source_id: 'qc-bag-result',
        display_name: 'QC Bag Results',
        description: 'Quality control results from Starfish',
        enabled: true,
        ingestion_mode: 'blob_trigger',
        ai_agent_id: 'quality-data-extraction',
        config_json: JSON.stringify({
          source_id: 'qc-bag-result',
          display_name: 'QC Bag Results',
          description: 'Quality control results from Starfish',
          enabled: true,
          ingestion: {
            mode: 'blob_trigger',
            landing_container: 'data-landing',
            file_pattern: '*.json',
            file_format: 'json',
            processor_type: 'json-extraction',
          },
          transformation: {
            ai_agent_id: 'quality-data-extraction',
            extract_fields: ['bag_id', 'quality_score'],
            link_field: 'bag_id',
            field_mappings: {},
          },
          storage: {
            raw_container: 'raw-data',
            index_collection: 'quality_results',
          },
        }),
        created_at: '2025-01-15T00:00:00Z',
        updated_at: '2025-01-15T00:00:00Z',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockConfig });

      const result = await getSourceConfig('qc-bag-result');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/source-configs/qc-bag-result');
      expect(result.source_id).toBe('qc-bag-result');
      expect(result.ingestion_mode).toBe('blob_trigger');
      expect(result.config_json).toBeDefined();

      // Verify config_json can be parsed
      const parsedConfig = JSON.parse(result.config_json);
      expect(parsedConfig.ingestion.mode).toBe('blob_trigger');
      expect(parsedConfig.ingestion.landing_container).toBe('data-landing');
    });

    it('should fetch scheduled_pull source config detail', async () => {
      const mockConfig: SourceConfigDetailResponse = {
        source_id: 'weather-data',
        display_name: 'Weather Data',
        description: 'Regional weather observations',
        enabled: true,
        ingestion_mode: 'scheduled_pull',
        ai_agent_id: '',
        config_json: JSON.stringify({
          source_id: 'weather-data',
          display_name: 'Weather Data',
          description: 'Regional weather observations',
          enabled: true,
          ingestion: {
            mode: 'scheduled_pull',
            provider: 'openweathermap',
            schedule: '0 6 * * *',
            request: {
              base_url: 'https://api.openweathermap.org',
              auth_type: 'api_key',
              timeout_seconds: 30,
            },
          },
          transformation: {
            ai_agent_id: null,
            extract_fields: ['temperature', 'humidity'],
            link_field: 'region_id',
            field_mappings: {},
          },
          storage: {
            raw_container: 'raw-weather',
            index_collection: 'weather_observations',
          },
        }),
        created_at: '2025-01-10T00:00:00Z',
        updated_at: '2025-01-20T00:00:00Z',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockConfig });

      const result = await getSourceConfig('weather-data');

      expect(result.source_id).toBe('weather-data');
      expect(result.ingestion_mode).toBe('scheduled_pull');

      // Verify scheduled_pull specific fields
      const parsedConfig = JSON.parse(result.config_json);
      expect(parsedConfig.ingestion.provider).toBe('openweathermap');
      expect(parsedConfig.ingestion.schedule).toBe('0 6 * * *');
      expect(parsedConfig.ingestion.request.base_url).toBe('https://api.openweathermap.org');
    });

    it('should handle disabled source config', async () => {
      const mockConfig: SourceConfigDetailResponse = {
        source_id: 'legacy-source',
        display_name: 'Legacy Source',
        description: 'Deprecated data source',
        enabled: false,
        ingestion_mode: 'blob_trigger',
        ai_agent_id: 'legacy-agent',
        config_json: JSON.stringify({
          source_id: 'legacy-source',
          display_name: 'Legacy Source',
          description: 'Deprecated data source',
          enabled: false,
          ingestion: { mode: 'blob_trigger' },
          transformation: { extract_fields: [], link_field: 'id', field_mappings: {} },
          storage: { raw_container: 'raw', index_collection: 'legacy' },
        }),
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2025-12-15T00:00:00Z',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockConfig });

      const result = await getSourceConfig('legacy-source');

      expect(result.enabled).toBe(false);
    });
  });

  describe('Error handling', () => {
    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(listSourceConfigs()).rejects.toThrow('Network error');
    });

    it('should throw error on 404 response', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Source config not found'));

      await expect(getSourceConfig('nonexistent')).rejects.toThrow('Source config not found');
    });

    it('should throw error on unauthorized access', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Unauthorized'));

      await expect(listSourceConfigs()).rejects.toThrow('Unauthorized');
    });
  });
});
