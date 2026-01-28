/**
 * AI Agents API Module
 *
 * API functions for AI agent configuration viewer (read-only).
 * Maps to BFF /api/admin/ai-agents endpoints.
 *
 * Story 9.12c: AI Agent & Prompt Viewer UI
 */

import apiClient from './client';
import type {
  AgentConfigDetail,
  AgentConfigListParams,
  AgentConfigListResponse,
  PromptListResponse,
} from '@/types/agent-config';

const BASE_PATH = '/admin/ai-agents';

/**
 * List all AI agent configurations with optional filters.
 *
 * @param params - Query parameters for filtering and pagination
 * @returns Paginated list of agent configuration summaries
 */
export async function listAiAgents(
  params: AgentConfigListParams = {}
): Promise<AgentConfigListResponse> {
  const { data } = await apiClient.get<AgentConfigListResponse>(
    BASE_PATH,
    params as Record<string, unknown>
  );
  return data;
}

/**
 * Get AI agent configuration detail by ID.
 *
 * Returns the full agent configuration including config_json blob
 * and linked prompts array.
 *
 * @param agentId - Agent configuration ID (e.g., 'disease-diagnosis')
 * @returns Full agent configuration detail
 */
export async function getAiAgent(agentId: string): Promise<AgentConfigDetail> {
  const { data } = await apiClient.get<AgentConfigDetail>(
    `${BASE_PATH}/${encodeURIComponent(agentId)}`
  );
  return data;
}

/**
 * List prompts linked to a specific AI agent.
 *
 * Note: For detail views, prompts are already included in getAiAgent() response.
 * This endpoint is useful for filtered views or when only prompts are needed.
 *
 * @param agentId - Agent configuration ID
 * @param status - Optional filter by prompt status
 * @returns List of prompt summaries for the agent
 */
export async function listPromptsByAgent(
  agentId: string,
  status?: string
): Promise<PromptListResponse> {
  const params: Record<string, unknown> = {};
  if (status) {
    params.status = status;
  }

  const { data } = await apiClient.get<PromptListResponse>(
    `${BASE_PATH}/${encodeURIComponent(agentId)}/prompts`,
    params
  );
  return data;
}
