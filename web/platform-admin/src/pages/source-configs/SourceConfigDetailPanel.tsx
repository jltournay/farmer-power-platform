/**
 * Source Configuration Detail Panel
 *
 * Slide-out panel displaying full source configuration details in structured sections.
 * Implements Story 9.11c - Source Configuration Viewer UI (AC 9.11c.2, AC 9.11c.3).
 */

import { useMemo } from 'react';
import {
  Box,
  Typography,
  Chip,
  Divider,
  Card,
  CardContent,
  Alert,
  Table,
  TableBody,
  TableRow,
  TableCell,
} from '@mui/material';
import type { SourceConfigDetailResponse, SourceConfig } from '@/types/source-config';
import {
  parseConfigJson,
  getIngestionModeLabel,
  getIngestionModeColor,
  getEnabledLabel,
  getEnabledColor,
  getAiAgentId,
} from '@/types/source-config';

interface SourceConfigDetailPanelProps {
  config: SourceConfigDetailResponse;
}

/**
 * Renders a key-value row for configuration display.
 */
function ConfigRow({ label, value }: { label: string; value: React.ReactNode }): JSX.Element {
  return (
    <TableRow>
      <TableCell
        component="th"
        scope="row"
        sx={{
          fontWeight: 500,
          color: 'text.secondary',
          width: '40%',
          py: 1,
          borderBottom: 'none',
        }}
      >
        {label}
      </TableCell>
      <TableCell sx={{ py: 1, borderBottom: 'none' }}>{value}</TableCell>
    </TableRow>
  );
}

/**
 * Renders a section card with title and content.
 */
function SectionCard({ title, children }: { title: string; children: React.ReactNode }): JSX.Element {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          {title}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

/**
 * Renders an array as a comma-separated list.
 */
function ArrayDisplay({ items }: { items: string[] | null | undefined }): JSX.Element {
  if (!items || items.length === 0) {
    return <Typography color="text.secondary">—</Typography>;
  }
  return <Typography>{items.join(', ')}</Typography>;
}

/**
 * Renders a JSON object as formatted code.
 */
function JsonDisplay({ data }: { data: Record<string, unknown> | null | undefined }): JSX.Element {
  if (!data || Object.keys(data).length === 0) {
    return <Typography color="text.secondary">—</Typography>;
  }
  return (
    <Box
      component="pre"
      sx={{
        backgroundColor: 'grey.100',
        p: 1,
        borderRadius: 1,
        overflow: 'auto',
        fontSize: '0.75rem',
        m: 0,
      }}
    >
      {JSON.stringify(data, null, 2)}
    </Box>
  );
}

/**
 * Source configuration detail panel component.
 */
export function SourceConfigDetailPanel({ config }: SourceConfigDetailPanelProps): JSX.Element {
  // Parse the config JSON
  const parsedConfig = useMemo<SourceConfig | null>(() => {
    try {
      return parseConfigJson(config.config_json);
    } catch {
      return null;
    }
  }, [config.config_json]);

  if (!parsedConfig) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">Failed to parse configuration JSON</Alert>
      </Box>
    );
  }

  const ingestion = parsedConfig.ingestion;
  const isBlobTrigger = ingestion.mode === 'blob_trigger';
  const isScheduledPull = ingestion.mode === 'scheduled_pull';

  return (
    <Box sx={{ p: 2, overflow: 'auto' }}>
      {/* Overview Section */}
      <SectionCard title="Overview">
        <Table size="small">
          <TableBody>
            <ConfigRow label="Source ID" value={parsedConfig.source_id} />
            <ConfigRow label="Display Name" value={parsedConfig.display_name} />
            <ConfigRow label="Description" value={parsedConfig.description} />
            <ConfigRow
              label="Status"
              value={
                <Chip
                  label={getEnabledLabel(parsedConfig.enabled)}
                  size="small"
                  color={getEnabledColor(parsedConfig.enabled)}
                />
              }
            />
            <ConfigRow
              label="Ingestion Mode"
              value={
                <Chip
                  label={getIngestionModeLabel(ingestion.mode)}
                  size="small"
                  color={getIngestionModeColor(ingestion.mode)}
                />
              }
            />
          </TableBody>
        </Table>
      </SectionCard>

      {/* Ingestion Section - Conditional Rendering (AC 9.11c.3) */}
      <SectionCard title="Ingestion Configuration">
        <Table size="small">
          <TableBody>
            <ConfigRow label="Mode" value={getIngestionModeLabel(ingestion.mode)} />

            {/* Blob Trigger Fields (AC 9.11c.3) */}
            {isBlobTrigger && (
              <>
                <ConfigRow label="Landing Container" value={ingestion.landing_container || '—'} />
                <ConfigRow label="File Pattern" value={ingestion.file_pattern || '—'} />
                <ConfigRow label="File Format" value={ingestion.file_format || '—'} />
                <ConfigRow label="Trigger Mechanism" value={ingestion.trigger_mechanism || '—'} />
                <ConfigRow label="Processor Type" value={ingestion.processor_type || '—'} />
                {ingestion.path_pattern && (
                  <>
                    <ConfigRow label="Path Pattern" value={ingestion.path_pattern.pattern} />
                    <ConfigRow
                      label="Extract Fields"
                      value={<ArrayDisplay items={ingestion.path_pattern.extract_fields} />}
                    />
                  </>
                )}
                {ingestion.processed_file_config && (
                  <>
                    <ConfigRow label="Post-Process Action" value={ingestion.processed_file_config.action} />
                    {ingestion.processed_file_config.archive_container && (
                      <ConfigRow label="Archive Container" value={ingestion.processed_file_config.archive_container} />
                    )}
                    {ingestion.processed_file_config.archive_ttl_days && (
                      <ConfigRow label="Archive TTL (days)" value={ingestion.processed_file_config.archive_ttl_days} />
                    )}
                    {ingestion.processed_file_config.processed_folder && (
                      <ConfigRow label="Processed Folder" value={ingestion.processed_file_config.processed_folder} />
                    )}
                  </>
                )}
                {ingestion.zip_config && (
                  <>
                    <ConfigRow label="ZIP Manifest File" value={ingestion.zip_config.manifest_file} />
                    <ConfigRow label="ZIP Images Folder" value={ingestion.zip_config.images_folder} />
                    <ConfigRow label="Extract Images" value={ingestion.zip_config.extract_images ? 'Yes' : 'No'} />
                    <ConfigRow label="Image Storage Container" value={ingestion.zip_config.image_storage_container} />
                  </>
                )}
              </>
            )}

            {/* Scheduled Pull Fields (AC 9.11c.3) */}
            {isScheduledPull && (
              <>
                <ConfigRow label="Provider" value={ingestion.provider || '—'} />
                <ConfigRow label="Schedule (Cron)" value={ingestion.schedule || '—'} />
                {ingestion.request && (
                  <>
                    <ConfigRow label="Base URL" value={ingestion.request.base_url} />
                    <ConfigRow label="Auth Type" value={ingestion.request.auth_type} />
                    {ingestion.request.auth_secret_key && (
                      <ConfigRow label="Auth Secret Key" value={ingestion.request.auth_secret_key} />
                    )}
                    <ConfigRow label="Timeout (seconds)" value={ingestion.request.timeout_seconds} />
                    <ConfigRow label="Parameters" value={<JsonDisplay data={ingestion.request.parameters} />} />
                  </>
                )}
                {ingestion.iteration && (
                  <>
                    <ConfigRow label="Iterate Over" value={ingestion.iteration.foreach} />
                    <ConfigRow label="Source MCP" value={ingestion.iteration.source_mcp} />
                    <ConfigRow label="Source Tool" value={ingestion.iteration.source_tool} />
                    {ingestion.iteration.tool_arguments && (
                      <ConfigRow
                        label="Tool Arguments"
                        value={<JsonDisplay data={ingestion.iteration.tool_arguments as Record<string, unknown>} />}
                      />
                    )}
                    {ingestion.iteration.result_path && (
                      <ConfigRow label="Result Path" value={ingestion.iteration.result_path} />
                    )}
                    <ConfigRow label="Concurrency" value={ingestion.iteration.concurrency} />
                    {ingestion.iteration.inject_linkage && (
                      <ConfigRow
                        label="Inject Linkage"
                        value={<ArrayDisplay items={ingestion.iteration.inject_linkage} />}
                      />
                    )}
                  </>
                )}
                {ingestion.retry && (
                  <>
                    <ConfigRow label="Max Retry Attempts" value={ingestion.retry.max_attempts} />
                    <ConfigRow label="Backoff Strategy" value={ingestion.retry.backoff} />
                  </>
                )}
              </>
            )}
          </TableBody>
        </Table>
      </SectionCard>

      {/* Validation Section */}
      {parsedConfig.validation && (
        <SectionCard title="Validation Configuration">
          <Table size="small">
            <TableBody>
              <ConfigRow label="Schema Name" value={parsedConfig.validation.schema_name} />
              <ConfigRow
                label="Schema Version"
                value={parsedConfig.validation.schema_version ?? 'Latest'}
              />
              <ConfigRow label="Strict Mode" value={parsedConfig.validation.strict ? 'Yes' : 'No'} />
            </TableBody>
          </Table>
        </SectionCard>
      )}

      {/* Transformation Section */}
      <SectionCard title="Transformation Configuration">
        <Table size="small">
          <TableBody>
            <ConfigRow
              label="AI Agent ID"
              value={getAiAgentId(parsedConfig.transformation) || '—'}
            />
            <ConfigRow label="Link Field" value={parsedConfig.transformation.link_field} />
            <ConfigRow
              label="Extract Fields"
              value={<ArrayDisplay items={parsedConfig.transformation.extract_fields} />}
            />
            <ConfigRow
              label="Field Mappings"
              value={<JsonDisplay data={parsedConfig.transformation.field_mappings} />}
            />
          </TableBody>
        </Table>
      </SectionCard>

      {/* Storage Section */}
      <SectionCard title="Storage Configuration">
        <Table size="small">
          <TableBody>
            <ConfigRow label="Raw Container" value={parsedConfig.storage.raw_container} />
            <ConfigRow label="Index Collection" value={parsedConfig.storage.index_collection} />
            {parsedConfig.storage.file_container && (
              <ConfigRow label="File Container" value={parsedConfig.storage.file_container} />
            )}
            {parsedConfig.storage.file_path_pattern && (
              <ConfigRow label="File Path Pattern" value={parsedConfig.storage.file_path_pattern} />
            )}
            {parsedConfig.storage.ttl_days && (
              <ConfigRow label="TTL (days)" value={parsedConfig.storage.ttl_days} />
            )}
          </TableBody>
        </Table>
      </SectionCard>

      {/* Events Section */}
      {parsedConfig.events && (
        <SectionCard title="Events Configuration">
          <Table size="small">
            <TableBody>
              {parsedConfig.events.on_success && (
                <>
                  <ConfigRow label="Success Topic" value={parsedConfig.events.on_success.topic} />
                  <ConfigRow
                    label="Success Payload Fields"
                    value={<ArrayDisplay items={parsedConfig.events.on_success.payload_fields} />}
                  />
                </>
              )}
              {parsedConfig.events.on_failure && (
                <>
                  <ConfigRow label="Failure Topic" value={parsedConfig.events.on_failure.topic} />
                  <ConfigRow
                    label="Failure Payload Fields"
                    value={<ArrayDisplay items={parsedConfig.events.on_failure.payload_fields} />}
                  />
                </>
              )}
            </TableBody>
          </Table>
        </SectionCard>
      )}

      <Divider sx={{ my: 2 }} />

      {/* Read-only indicator (AC 9.11c.2) */}
      <Alert severity="warning" icon={false} sx={{ mb: 2 }}>
        ⚠️ Read-only view. Use <code>source-config</code> CLI to modify.
      </Alert>

      {/* Metadata */}
      <Typography variant="caption" color="text.secondary" display="block">
        Created: {config.created_at ? new Date(config.created_at).toLocaleString() : '—'}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block">
        Updated: {config.updated_at ? new Date(config.updated_at).toLocaleString() : '—'}
      </Typography>
    </Box>
  );
}
