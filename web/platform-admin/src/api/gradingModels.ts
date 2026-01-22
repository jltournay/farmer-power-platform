/**
 * Grading Models API Module
 *
 * API functions for grading model management (read + assignment).
 * Maps to BFF /api/admin/grading-models endpoints.
 */

import apiClient from './client';
import type {
  GradingModelDetailResponse,
  GradingModelListParams,
  GradingModelListResponse,
} from './types';

const BASE_PATH = '/admin/grading-models';

/**
 * List all grading models with optional filters.
 */
export async function listGradingModels(
  params: GradingModelListParams = {}
): Promise<GradingModelListResponse> {
  const { data } = await apiClient.get<GradingModelListResponse>(
    BASE_PATH,
    params as Record<string, unknown>
  );
  return data;
}

/**
 * Get grading model detail by ID.
 */
export async function getGradingModel(modelId: string): Promise<GradingModelDetailResponse> {
  const { data } = await apiClient.get<GradingModelDetailResponse>(`${BASE_PATH}/${modelId}`);
  return data;
}

/**
 * Assign a grading model to a factory.
 * Returns updated grading model detail with refreshed factory list.
 */
export async function assignGradingModelToFactory(
  modelId: string,
  factoryId: string
): Promise<GradingModelDetailResponse> {
  const { data } = await apiClient.post<GradingModelDetailResponse>(
    `${BASE_PATH}/${modelId}/assign`,
    { factory_id: factoryId }
  );
  return data;
}
