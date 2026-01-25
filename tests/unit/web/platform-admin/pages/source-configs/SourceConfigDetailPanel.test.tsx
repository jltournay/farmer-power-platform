/**
 * Unit Tests for SourceConfigDetailPanel Component
 *
 * Tests the Source Configuration detail panel rendering with
 * conditional sections for different ingestion modes.
 * Story 9.11c - Source Configuration Viewer UI (AC 9.11c.2, AC 9.11c.3)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SourceConfigDetailPanel } from '../../../../../../web/platform-admin/src/pages/source-configs/SourceConfigDetailPanel';
import type { SourceConfigDetailResponse } from '../../../../../../web/platform-admin/src/types/source-config';

describe('SourceConfigDetailPanel', () => {
  const createBlobTriggerConfig = (): SourceConfigDetailResponse => ({
    source_id: 'qc-bag-result',
    display_name: 'QC Bag Results',
    description: 'Quality control results from Starfish',
    enabled: true,
    ingestion_mode: 'blob_trigger',
    ai_agent_id: 'quality-extraction',
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
        trigger_mechanism: 'event_grid',
        processor_type: 'json-extraction',
        path_pattern: {
          pattern: '{region}/{factory}/{date}',
          extract_fields: ['region', 'factory', 'date'],
        },
        processed_file_config: {
          action: 'archive',
          archive_container: 'processed-archive',
          archive_ttl_days: 90,
          processed_folder: null,
        },
      },
      validation: {
        schema_name: 'data/qc-bag-result.json',
        schema_version: 1,
        strict: true,
      },
      transformation: {
        ai_agent_id: 'quality-extraction',
        agent: null,
        extract_fields: ['bag_id', 'quality_score', 'weight'],
        link_field: 'farmer_id',
        field_mappings: { bag_weight: 'weight' },
      },
      storage: {
        raw_container: 'raw-data',
        index_collection: 'quality_results',
        file_container: null,
        file_path_pattern: null,
        ttl_days: 365,
      },
      events: {
        on_success: {
          topic: 'collection.quality_result.received',
          payload_fields: ['farmer_id', 'grade'],
        },
        on_failure: {
          topic: 'collection.ingestion.failed',
          payload_fields: ['source_id', 'error'],
        },
      },
    }),
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-20T14:30:00Z',
  });

  const createScheduledPullConfig = (): SourceConfigDetailResponse => ({
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
        provider: 'open-meteo',
        schedule: '0 6 * * *',
        request: {
          base_url: 'https://api.open-meteo.com/v1/forecast',
          auth_type: 'none',
          auth_secret_key: null,
          parameters: { units: 'metric' },
          timeout_seconds: 30,
        },
        iteration: {
          foreach: 'region',
          source_mcp: 'plantation',
          source_tool: 'list_regions',
          tool_arguments: { include_inactive: false },
          result_path: 'regions',
          concurrency: 5,
          inject_linkage: ['region_id'],
        },
        retry: {
          max_attempts: 3,
          backoff: 'exponential',
        },
      },
      validation: null,
      transformation: {
        ai_agent_id: null,
        agent: null,
        extract_fields: ['temperature', 'humidity', 'rainfall'],
        link_field: 'region_id',
        field_mappings: {},
      },
      storage: {
        raw_container: 'raw-weather',
        index_collection: 'weather_observations',
        file_container: null,
        file_path_pattern: null,
        ttl_days: null,
      },
      events: null,
    }),
    created_at: '2026-01-10T08:00:00Z',
    updated_at: null,
  });

  describe('Overview Section', () => {
    it('renders source_id', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('qc-bag-result')).toBeInTheDocument();
    });

    it('renders display_name', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('QC Bag Results')).toBeInTheDocument();
    });

    it('renders description', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('Quality control results from Starfish')).toBeInTheDocument();
    });

    it('renders enabled status chip', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('Enabled')).toBeInTheDocument();
    });

    it('renders disabled status chip for disabled config', () => {
      const config = createBlobTriggerConfig();
      const parsed = JSON.parse(config.config_json);
      parsed.enabled = false;
      config.config_json = JSON.stringify(parsed);

      render(<SourceConfigDetailPanel config={config} />);
      expect(screen.getByText('Disabled')).toBeInTheDocument();
    });

    it('renders ingestion mode chip', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      // "Blob Trigger" appears in both Overview chip and Ingestion section
      expect(screen.getAllByText('Blob Trigger').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Blob Trigger Ingestion Fields (AC 9.11c.3)', () => {
    it('renders landing_container', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('data-landing')).toBeInTheDocument();
    });

    it('renders file_pattern', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('*.json')).toBeInTheDocument();
    });

    it('renders file_format', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('json')).toBeInTheDocument();
    });

    it('renders trigger_mechanism', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('event_grid')).toBeInTheDocument();
    });

    it('renders processor_type', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('json-extraction')).toBeInTheDocument();
    });

    it('renders path_pattern fields', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('{region}/{factory}/{date}')).toBeInTheDocument();
      expect(screen.getByText('region, factory, date')).toBeInTheDocument();
    });

    it('renders processed_file_config fields', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('archive')).toBeInTheDocument();
      expect(screen.getByText('processed-archive')).toBeInTheDocument();
      expect(screen.getByText('90')).toBeInTheDocument();
    });
  });

  describe('Scheduled Pull Ingestion Fields (AC 9.11c.3)', () => {
    it('renders provider', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('open-meteo')).toBeInTheDocument();
    });

    it('renders schedule', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('0 6 * * *')).toBeInTheDocument();
    });

    it('renders request config fields', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('https://api.open-meteo.com/v1/forecast')).toBeInTheDocument();
      expect(screen.getByText('none')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('renders iteration config fields', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('region')).toBeInTheDocument();
      expect(screen.getByText('plantation')).toBeInTheDocument();
      expect(screen.getByText('list_regions')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('renders tool_arguments when present', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      // tool_arguments is { include_inactive: false }
      expect(screen.getByText(/"include_inactive": false/)).toBeInTheDocument();
    });

    it('renders result_path when present', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('regions')).toBeInTheDocument();
    });

    it('renders inject_linkage when present', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      // 'region_id' appears in both link_field and inject_linkage
      expect(screen.getAllByText('region_id').length).toBeGreaterThanOrEqual(1);
    });

    it('renders retry config fields', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('exponential')).toBeInTheDocument();
    });

    it('does NOT render blob_trigger fields for scheduled_pull', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.queryByText('Landing Container')).not.toBeInTheDocument();
      expect(screen.queryByText('File Pattern')).not.toBeInTheDocument();
      expect(screen.queryByText('File Format')).not.toBeInTheDocument();
    });
  });

  describe('Validation Section', () => {
    it('renders validation config when present', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('data/qc-bag-result.json')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('Yes')).toBeInTheDocument(); // strict: true
    });

    it('does NOT render validation section when null', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.queryByText('Validation Configuration')).not.toBeInTheDocument();
    });
  });

  describe('Transformation Section', () => {
    it('renders ai_agent_id', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('quality-extraction')).toBeInTheDocument();
    });

    it('renders link_field', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('farmer_id')).toBeInTheDocument();
    });

    it('renders extract_fields as comma-separated list', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('bag_id, quality_score, weight')).toBeInTheDocument();
    });

    it('renders field_mappings as JSON', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText(/"bag_weight": "weight"/)).toBeInTheDocument();
    });

    it('shows dash when ai_agent_id is null', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      // AI Agent ID row should show "—"
      const rows = screen.getAllByRole('row');
      const agentRow = rows.find((row) => row.textContent?.includes('AI Agent ID'));
      expect(agentRow?.textContent).toContain('—');
    });
  });

  describe('Storage Section', () => {
    it('renders raw_container', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('raw-data')).toBeInTheDocument();
    });

    it('renders index_collection', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('quality_results')).toBeInTheDocument();
    });

    it('renders ttl_days when present', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('365')).toBeInTheDocument();
    });

    it('does NOT render ttl_days when null', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.queryByText('TTL (days)')).not.toBeInTheDocument();
    });
  });

  describe('Events Section', () => {
    it('renders on_success event config', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('collection.quality_result.received')).toBeInTheDocument();
      expect(screen.getByText('farmer_id, grade')).toBeInTheDocument();
    });

    it('renders on_failure event config', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText('collection.ingestion.failed')).toBeInTheDocument();
      expect(screen.getByText('source_id, error')).toBeInTheDocument();
    });

    it('does NOT render events section when null', () => {
      render(<SourceConfigDetailPanel config={createScheduledPullConfig()} />);
      expect(screen.queryByText('Events Configuration')).not.toBeInTheDocument();
    });
  });

  describe('Read-Only Indicator (AC 9.11c.2)', () => {
    it('renders read-only warning message', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText(/Read-only view/)).toBeInTheDocument();
      expect(screen.getByText(/source-config/)).toBeInTheDocument();
      expect(screen.getByText(/CLI to modify/)).toBeInTheDocument();
    });
  });

  describe('Metadata Footer', () => {
    it('renders created_at timestamp', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      // Should contain the formatted date
      expect(screen.getByText(/Created:/)).toBeInTheDocument();
    });

    it('renders updated_at timestamp', () => {
      render(<SourceConfigDetailPanel config={createBlobTriggerConfig()} />);
      expect(screen.getByText(/Updated:/)).toBeInTheDocument();
    });

    it('shows dash when timestamps are null', () => {
      const config = createScheduledPullConfig();
      config.created_at = null;
      config.updated_at = null;

      render(<SourceConfigDetailPanel config={config} />);
      // Both should show "—"
      const createdText = screen.getByText(/Created:/);
      const updatedText = screen.getByText(/Updated:/);
      expect(createdText.textContent).toContain('—');
      expect(updatedText.textContent).toContain('—');
    });
  });

  describe('Error Handling', () => {
    it('shows error alert when config_json is invalid', () => {
      const config = createBlobTriggerConfig();
      config.config_json = 'invalid json {{{';

      render(<SourceConfigDetailPanel config={config} />);
      expect(screen.getByText('Failed to parse configuration JSON')).toBeInTheDocument();
    });
  });
});
