/**
 * AI Agent Configuration TypeScript Interfaces
 *
 * Type definitions for AI Agent & Prompt Viewer matching BFF API schemas.
 * Mirrors fp_common/models/agent_config_summary.py Pydantic models.
 *
 * Story 9.12c: AI Agent & Prompt Viewer UI
 */

// ============================================================================
// Agent Type and Status Types
// ============================================================================

/** Agent type (maps to AI Model agent types) */
export type AgentType = 'extractor' | 'explorer' | 'generator' | 'conversational' | 'tiered-vision';

/** Agent configuration status */
export type AgentStatus = 'draft' | 'staged' | 'active' | 'archived';

// ============================================================================
// LLM Configuration Types (parsed from config_json)
// ============================================================================

/** Retry configuration for LLM calls */
export interface RetryConfig {
  max_retries?: number;
  backoff?: string;
  timeout_seconds?: number;
}

/** LLM configuration block */
export interface LlmConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  response_format?: string;
  retry?: RetryConfig;
}

// ============================================================================
// RAG Configuration Types (parsed from config_json)
// ============================================================================

/** RAG configuration block */
export interface RagConfig {
  enabled: boolean;
  knowledge_domains?: string[];
  domains?: string[]; // Alias for knowledge_domains
  top_k?: number;
  min_similarity?: number;
  score_threshold?: number; // Alias for min_similarity
  namespace?: string;
  include_metadata?: boolean;
  rerank_enabled?: boolean;
  reranking_model?: string | null;
}

// ============================================================================
// Contract Configuration Types (parsed from config_json)
// ============================================================================

/** Schema definition for contracts */
export interface SchemaDefinition {
  type: string;
  required?: string[];
  properties?: Record<string, unknown>;
}

/** Event configuration */
export interface EventDefinition {
  event: string;
  schema: SchemaDefinition;
}

/** Input contract configuration */
export interface InputContract {
  event?: string;
  schema?: SchemaDefinition;
}

/** Output contract configuration */
export interface OutputContract {
  event?: string;
  schema?: SchemaDefinition;
}

/** Extraction schema for extractor agents */
export interface ExtractionSchema {
  required_fields: string[];
  optional_fields?: string[];
  field_types?: Record<string, string>;
}

/** Error handling configuration */
export interface ErrorHandlingConfig {
  max_attempts?: number;
  backoff_ms?: number[];
  on_failure?: string;
  dead_letter_topic?: string | null;
}

/** Metadata block */
export interface AgentMetadata {
  author?: string;
  created_at?: string;
  updated_at?: string;
  changelog?: string;
  git_commit?: string | null;
}

// ============================================================================
// Complete Agent Configuration (parsed from config_json)
// ============================================================================

/** Complete agent configuration parsed from config_json */
export interface AgentConfig {
  agent_id: string;
  version: string;
  type: AgentType;
  status: AgentStatus;
  description: string;

  // Event configuration
  input?: InputContract;
  output?: OutputContract;

  // LLM configuration
  llm: LlmConfig;

  // RAG configuration (optional, mainly for explorer agents)
  rag?: RagConfig;

  // Extraction schema (for extractor agents)
  extraction_schema?: ExtractionSchema;

  // MCP sources
  mcp_sources?: string[];

  // Error handling
  error_handling?: ErrorHandlingConfig;

  // Metadata
  metadata?: AgentMetadata;
}

// ============================================================================
// Prompt Types
// ============================================================================

/** Prompt content structure */
export interface PromptContent {
  system_prompt: string;
  template: string;
  output_schema?: Record<string, unknown>;
  few_shot_examples?: Array<{
    input: unknown;
    output: unknown;
  }>;
}

/** Prompt A/B test configuration */
export interface PromptAbTestConfig {
  enabled: boolean;
  traffic_percentage?: number;
  test_id?: string | null;
}

/** Prompt metadata */
export interface PromptMetadata {
  author?: string;
  created_at?: string;
  updated_at?: string;
  changelog?: string;
  git_commit?: string | null;
}

// ============================================================================
// API Response Types
// ============================================================================

/** Prompt summary for list views */
export interface PromptSummary {
  id: string;
  prompt_id: string;
  agent_id: string;
  version: string;
  status: string;
  author: string;
  updated_at: string | null;
}

/** Full prompt detail (for expanded view) */
export interface PromptDetail extends PromptSummary {
  content?: PromptContent;
  metadata?: PromptMetadata;
  ab_test?: PromptAbTestConfig;
}

/** Agent configuration summary for list views */
export interface AgentConfigSummary {
  agent_id: string;
  version: string;
  agent_type: AgentType;
  status: AgentStatus;
  description: string;
  model: string;
  prompt_count: number;
  updated_at: string | null;
}

/** Agent configuration detail response from BFF */
export interface AgentConfigDetail extends AgentConfigSummary {
  config_json: string; // JSON string - must be parsed client-side
  prompts: PromptSummary[];
  created_at: string | null;
}

/** Pagination metadata */
export interface AgentConfigPaginationMeta {
  total_count: number;
  page_size: number;
  next_page_token: string | null;
}

/** Agent configuration list API response */
export interface AgentConfigListResponse {
  data: AgentConfigSummary[];
  pagination: AgentConfigPaginationMeta;
}

/** Agent configuration list query parameters */
export interface AgentConfigListParams {
  page_size?: number;
  page_token?: string;
  agent_type?: AgentType;
  status?: AgentStatus;
}

/** Prompt list response from BFF */
export interface PromptListResponse {
  data: PromptSummary[];
  total_count: number;
}

// ============================================================================
// Helper Functions
// ============================================================================

/** Get display label for agent type */
export function getAgentTypeLabel(type: AgentType): string {
  const labels: Record<AgentType, string> = {
    extractor: 'Extractor',
    explorer: 'Explorer',
    generator: 'Generator',
    conversational: 'Conversational',
    'tiered-vision': 'Tiered Vision',
  };
  return labels[type] || type;
}

/** Get chip color for agent type */
export function getAgentTypeColor(type: AgentType): 'info' | 'warning' | 'success' | 'secondary' | 'primary' {
  const colors: Record<AgentType, 'info' | 'warning' | 'success' | 'secondary' | 'primary'> = {
    extractor: 'info',
    explorer: 'warning',
    generator: 'success',
    conversational: 'secondary',
    'tiered-vision': 'primary',
  };
  return colors[type] || 'info';
}

/** Get display label for status */
export function getStatusLabel(status: AgentStatus | string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    staged: 'Staged',
    active: 'Active',
    archived: 'Archived',
  };
  return labels[status] || status;
}

/** Get chip color for status */
export function getStatusColor(status: AgentStatus | string): 'success' | 'warning' | 'default' | 'info' {
  const colors: Record<string, 'success' | 'warning' | 'default' | 'info'> = {
    active: 'success',
    staged: 'warning',
    archived: 'default',
    draft: 'info',
  };
  return colors[status] || 'default';
}

/** Parse config_json string into typed AgentConfig object */
export function parseConfigJson(configJson: string): AgentConfig | null {
  try {
    return JSON.parse(configJson) as AgentConfig;
  } catch {
    return null;
  }
}

/** Get RAG domains from RAG config, handling both field names */
export function getRagDomains(ragConfig?: RagConfig): string[] {
  if (!ragConfig) return [];
  return ragConfig.knowledge_domains || ragConfig.domains || [];
}

/** Check if RAG is enabled */
export function isRagEnabled(ragConfig?: RagConfig): boolean {
  return ragConfig?.enabled ?? false;
}

/** Format date string for display */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}
