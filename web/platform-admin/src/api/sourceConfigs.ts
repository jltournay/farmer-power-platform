/**
 * Source Configurations API Module
 *
 * API functions for source configuration management (read-only).
 * Maps to BFF /api/admin/source-configs endpoints.
 */

import apiClient from './client';
import type {
  SourceConfigDetailResponse,
  SourceConfigListParams,
  SourceConfigListResponse,
} from '@/types/source-config';

const BASE_PATH = '/admin/source-configs';

/**
 * List all source configurations with optional filters.
 */
export async function listSourceConfigs(
  params: SourceConfigListParams = {}
): Promise<SourceConfigListResponse> {
  const { data } = await apiClient.get<SourceConfigListResponse>(
    BASE_PATH,
    params as Record<string, unknown>
  );
  return data;
}

/**
 * Get source configuration detail by ID.
 */
export async function getSourceConfig(sourceId: string): Promise<SourceConfigDetailResponse> {
  const { data } = await apiClient.get<SourceConfigDetailResponse>(`${BASE_PATH}/${sourceId}`);
  return data;
}
