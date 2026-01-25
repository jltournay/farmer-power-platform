/**
 * Unit Tests for Source Configuration TypeScript Types
 *
 * Tests type helper functions and JSON parsing for source configurations.
 */

import { describe, it, expect } from 'vitest';
import {
  getIngestionModeLabel,
  getIngestionModeColor,
  getEnabledLabel,
  getEnabledColor,
  parseConfigJson,
  getAiAgentId,
  type SourceConfig,
  type TransformationConfig,
} from '../../../../../web/platform-admin/src/types/source-config';

describe('Source Config Type Helpers', () => {
  describe('getIngestionModeLabel', () => {
    it('returns "Blob Trigger" for blob_trigger mode', () => {
      expect(getIngestionModeLabel('blob_trigger')).toBe('Blob Trigger');
    });

    it('returns "Scheduled Pull" for scheduled_pull mode', () => {
      expect(getIngestionModeLabel('scheduled_pull')).toBe('Scheduled Pull');
    });
  });

  describe('getIngestionModeColor', () => {
    it('returns "primary" for blob_trigger mode', () => {
      expect(getIngestionModeColor('blob_trigger')).toBe('primary');
    });

    it('returns "secondary" for scheduled_pull mode', () => {
      expect(getIngestionModeColor('scheduled_pull')).toBe('secondary');
    });
  });

  describe('getEnabledLabel', () => {
    it('returns "Enabled" when enabled is true', () => {
      expect(getEnabledLabel(true)).toBe('Enabled');
    });

    it('returns "Disabled" when enabled is false', () => {
      expect(getEnabledLabel(false)).toBe('Disabled');
    });
  });

  describe('getEnabledColor', () => {
    it('returns "success" when enabled is true', () => {
      expect(getEnabledColor(true)).toBe('success');
    });

    it('returns "default" when enabled is false', () => {
      expect(getEnabledColor(false)).toBe('default');
    });
  });

  describe('parseConfigJson', () => {
    it('parses a valid blob_trigger source config JSON', () => {
      const configJson = JSON.stringify({
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
        validation: {
          schema_name: 'data/qc-bag-result.json',
          schema_version: 1,
          strict: true,
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
      } as SourceConfig);

      const result = parseConfigJson(configJson);

      expect(result.source_id).toBe('qc-bag-result');
      expect(result.ingestion.mode).toBe('blob_trigger');
      expect(result.ingestion.landing_container).toBe('data-landing');
      expect(result.transformation.ai_agent_id).toBe('quality-data-extraction');
    });

    it('parses a valid scheduled_pull source config JSON', () => {
      const configJson = JSON.stringify({
        source_id: 'weather-data',
        display_name: 'Weather Data',
        description: 'Weather data from external API',
        enabled: true,
        ingestion: {
          mode: 'scheduled_pull',
          provider: 'openweathermap',
          schedule: '0 6 * * *',
          request: {
            base_url: 'https://api.openweathermap.org',
            auth_type: 'api_key',
            auth_secret_key: 'weather-api-key',
            parameters: { units: 'metric' },
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
      } as SourceConfig);

      const result = parseConfigJson(configJson);

      expect(result.source_id).toBe('weather-data');
      expect(result.ingestion.mode).toBe('scheduled_pull');
      expect(result.ingestion.provider).toBe('openweathermap');
      expect(result.ingestion.request?.base_url).toBe('https://api.openweathermap.org');
    });
  });

  describe('getAiAgentId', () => {
    it('returns ai_agent_id when set', () => {
      const transformation: TransformationConfig = {
        ai_agent_id: 'quality-extraction',
        agent: null,
        extract_fields: [],
        link_field: 'id',
        field_mappings: {},
      };
      expect(getAiAgentId(transformation)).toBe('quality-extraction');
    });

    it('returns agent as fallback when ai_agent_id is null', () => {
      const transformation: TransformationConfig = {
        ai_agent_id: null,
        agent: 'legacy-agent',
        extract_fields: [],
        link_field: 'id',
        field_mappings: {},
      };
      expect(getAiAgentId(transformation)).toBe('legacy-agent');
    });

    it('prefers ai_agent_id over agent', () => {
      const transformation: TransformationConfig = {
        ai_agent_id: 'new-agent',
        agent: 'old-agent',
        extract_fields: [],
        link_field: 'id',
        field_mappings: {},
      };
      expect(getAiAgentId(transformation)).toBe('new-agent');
    });

    it('returns null when both ai_agent_id and agent are null', () => {
      const transformation: TransformationConfig = {
        ai_agent_id: null,
        agent: null,
        extract_fields: [],
        link_field: 'id',
        field_mappings: {},
      };
      expect(getAiAgentId(transformation)).toBeNull();
    });
  });
});
