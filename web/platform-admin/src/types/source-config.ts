/**
 * Source Configuration TypeScript Interfaces
 *
 * Type definitions for Source Configuration viewer matching BFF API schemas.
 * Mirrors fp_common/models/source_config.py Pydantic models.
 */

// ============================================================================
// Ingestion Mode Types
// ============================================================================

/** Ingestion mode type */
export type IngestionMode = 'blob_trigger' | 'scheduled_pull';

/** File format type */
export type FileFormat = 'json' | 'zip';

/** Authentication type for scheduled pulls */
export type AuthType = 'none' | 'api_key' | 'oauth2';

/** Trigger mechanism type */
export type TriggerMechanism = 'event_grid';

/** Processed file action type */
export type ProcessedFileAction = 'archive' | 'move' | 'delete';

/** Backoff strategy type */
export type BackoffStrategy = 'exponential' | 'linear';

// ============================================================================
// Ingestion Configuration Types (blob_trigger mode)
// ============================================================================

/** Path pattern extraction configuration */
export interface PathPatternConfig {
  pattern: string;
  extract_fields: string[];
}

/** Configuration for handling files after processing */
export interface ProcessedFileConfig {
  action: ProcessedFileAction;
  archive_container: string | null;
  archive_ttl_days: number | null;
  processed_folder: string | null;
}

/** ZIP file handling configuration */
export interface ZipConfig {
  manifest_file: string;
  images_folder: string;
  extract_images: boolean;
  image_storage_container: string;
}

// ============================================================================
// Ingestion Configuration Types (scheduled_pull mode)
// ============================================================================

/** HTTP request configuration for scheduled pulls */
export interface RequestConfig {
  base_url: string;
  auth_type: AuthType;
  auth_secret_key: string | null;
  parameters: Record<string, string>;
  timeout_seconds: number;
}

/** Iteration configuration for scheduled pulls */
export interface IterationConfig {
  foreach: string;
  source_mcp: string;
  source_tool: string;
  tool_arguments: Record<string, unknown> | null;
  result_path: string | null;
  inject_linkage: string[] | null;
  concurrency: number;
}

/** Retry configuration for failed operations */
export interface RetryConfig {
  max_attempts: number;
  backoff: BackoffStrategy;
}

// ============================================================================
// Complete Ingestion Configuration (Union of blob_trigger and scheduled_pull)
// ============================================================================

/** Ingestion configuration block */
export interface IngestionConfig {
  mode: IngestionMode;

  // blob_trigger fields (optional when mode is scheduled_pull)
  landing_container?: string | null;
  path_pattern?: PathPatternConfig | null;
  file_pattern?: string | null;
  file_format?: FileFormat | null;
  trigger_mechanism?: TriggerMechanism | null;
  processed_file_config?: ProcessedFileConfig | null;
  zip_config?: ZipConfig | null;
  processor_type?: string | null;

  // scheduled_pull fields (optional when mode is blob_trigger)
  provider?: string | null;
  schedule?: string | null;
  request?: RequestConfig | null;
  iteration?: IterationConfig | null;
  retry?: RetryConfig | null;
}

// ============================================================================
// Validation Configuration
// ============================================================================

/** Validation configuration block */
export interface ValidationConfig {
  schema_name: string;
  schema_version: number | null;
  strict: boolean;
}

// ============================================================================
// Transformation Configuration
// ============================================================================

/** Transformation configuration block */
export interface TransformationConfig {
  ai_agent_id: string | null;
  agent: string | null; // deprecated, use ai_agent_id
  extract_fields: string[];
  link_field: string;
  field_mappings: Record<string, string>;
}

// ============================================================================
// Storage Configuration
// ============================================================================

/** Storage configuration block */
export interface StorageConfig {
  raw_container: string;
  index_collection: string;
  file_container: string | null;
  file_path_pattern: string | null;
  ttl_days: number | null;
}

// ============================================================================
// Events Configuration
// ============================================================================

/** Single event configuration */
export interface EventConfig {
  topic: string;
  payload_fields: string[];
}

/** Events configuration for domain event emission */
export interface EventsConfig {
  on_success: EventConfig | null;
  on_failure: EventConfig | null;
}

// ============================================================================
// Complete Source Configuration
// ============================================================================

/** Complete source configuration (parsed from config_json) */
export interface SourceConfig {
  source_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  ingestion: IngestionConfig;
  validation: ValidationConfig | null;
  transformation: TransformationConfig;
  storage: StorageConfig;
  events: EventsConfig | null;
}

// ============================================================================
// API Response Types
// ============================================================================

/** Source configuration summary for list views */
export interface SourceConfigSummary {
  source_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  ingestion_mode: IngestionMode;
  ai_agent_id: string;
}

/** Source configuration detail response from BFF */
export interface SourceConfigDetailResponse {
  source_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  ingestion_mode: IngestionMode;
  ai_agent_id: string;
  config_json: string; // JSON string - must be parsed client-side
  created_at: string | null;
  updated_at: string | null;
}

/** Pagination metadata */
export interface SourceConfigPaginationMeta {
  total_count: number;
  page_size: number;
  next_page_token: string | null;
}

/** Source configuration list API response */
export interface SourceConfigListResponse {
  data: SourceConfigSummary[];
  pagination: SourceConfigPaginationMeta;
}

/** Source configuration list query parameters */
export interface SourceConfigListParams {
  page_size?: number;
  page_token?: string;
  enabled_only?: boolean;
  ingestion_mode?: IngestionMode;
}

// ============================================================================
// Helper Functions
// ============================================================================

/** Get display label for ingestion mode */
export function getIngestionModeLabel(mode: IngestionMode): string {
  switch (mode) {
    case 'blob_trigger':
      return 'Blob Trigger';
    case 'scheduled_pull':
      return 'Scheduled Pull';
  }
}

/** Get chip color for ingestion mode */
export function getIngestionModeColor(mode: IngestionMode): 'primary' | 'secondary' {
  switch (mode) {
    case 'blob_trigger':
      return 'primary';
    case 'scheduled_pull':
      return 'secondary';
  }
}

/** Get chip color for enabled status */
export function getEnabledColor(enabled: boolean): 'success' | 'default' {
  return enabled ? 'success' : 'default';
}

/** Get display label for enabled status */
export function getEnabledLabel(enabled: boolean): string {
  return enabled ? 'Enabled' : 'Disabled';
}

/** Parse config_json string into typed SourceConfig object */
export function parseConfigJson(configJson: string): SourceConfig {
  return JSON.parse(configJson) as SourceConfig;
}

/** Get AI agent ID, preferring ai_agent_id over deprecated agent field */
export function getAiAgentId(transformation: TransformationConfig): string | null {
  return transformation.ai_agent_id || transformation.agent || null;
}
