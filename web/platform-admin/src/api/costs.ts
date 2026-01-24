/**
 * Cost API Module
 *
 * API functions for platform cost monitoring (Story 9.10b).
 * Maps to BFF /api/admin/costs endpoints created in Story 9.10a.
 */

import apiClient from './client';
import type {
  BudgetConfigRequest,
  BudgetConfigResponse,
  BudgetStatusResponse,
  CostDateRangeParams,
  CostSummaryResponse,
  CurrentDayCostResponse,
  DailyTrendResponse,
  DocumentCostResponse,
  EmbeddingByDomainResponse,
  LlmByAgentTypeResponse,
  LlmByModelResponse,
} from './types';

const BASE_PATH = '/admin/costs';

/**
 * Get cost summary with type breakdown for a date range.
 */
export async function getCostSummary(params: CostDateRangeParams = {}): Promise<CostSummaryResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.start_date && { start_date: params.start_date }),
    ...(params.end_date && { end_date: params.end_date }),
  };
  const { data } = await apiClient.get<CostSummaryResponse>(`${BASE_PATH}/summary`, queryParams);
  return data;
}

/**
 * Get daily cost trend data.
 */
export async function getDailyTrend(days?: number): Promise<DailyTrendResponse> {
  const queryParams: Record<string, unknown> = {
    ...(days !== undefined && { days }),
  };
  const { data } = await apiClient.get<DailyTrendResponse>(`${BASE_PATH}/trend/daily`, queryParams);
  return data;
}

/**
 * Get current day cost (NOT cached, for live polling).
 */
export async function getCurrentDayCost(): Promise<CurrentDayCostResponse> {
  const { data } = await apiClient.get<CurrentDayCostResponse>(`${BASE_PATH}/today`);
  return data;
}

/**
 * Get LLM cost breakdown by agent type.
 */
export async function getLlmByAgentType(params: CostDateRangeParams = {}): Promise<LlmByAgentTypeResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.start_date && { start_date: params.start_date }),
    ...(params.end_date && { end_date: params.end_date }),
  };
  const { data } = await apiClient.get<LlmByAgentTypeResponse>(`${BASE_PATH}/llm/by-agent-type`, queryParams);
  return data;
}

/**
 * Get LLM cost breakdown by model.
 */
export async function getLlmByModel(params: CostDateRangeParams = {}): Promise<LlmByModelResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.start_date && { start_date: params.start_date }),
    ...(params.end_date && { end_date: params.end_date }),
  };
  const { data } = await apiClient.get<LlmByModelResponse>(`${BASE_PATH}/llm/by-model`, queryParams);
  return data;
}

/**
 * Get document processing costs.
 */
export async function getDocumentCosts(params: CostDateRangeParams = {}): Promise<DocumentCostResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.start_date && { start_date: params.start_date }),
    ...(params.end_date && { end_date: params.end_date }),
  };
  const { data } = await apiClient.get<DocumentCostResponse>(`${BASE_PATH}/documents`, queryParams);
  return data;
}

/**
 * Get embedding costs by knowledge domain.
 */
export async function getEmbeddingsByDomain(params: CostDateRangeParams = {}): Promise<EmbeddingByDomainResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.start_date && { start_date: params.start_date }),
    ...(params.end_date && { end_date: params.end_date }),
  };
  const { data } = await apiClient.get<EmbeddingByDomainResponse>(`${BASE_PATH}/embeddings/by-domain`, queryParams);
  return data;
}

/**
 * Get current budget status.
 */
export async function getBudgetStatus(): Promise<BudgetStatusResponse> {
  const { data } = await apiClient.get<BudgetStatusResponse>(`${BASE_PATH}/budget`);
  return data;
}

/**
 * Configure budget thresholds.
 */
export async function configureBudget(request: BudgetConfigRequest): Promise<BudgetConfigResponse> {
  const { data } = await apiClient.put<BudgetConfigResponse>(`${BASE_PATH}/budget`, request);
  return data;
}
