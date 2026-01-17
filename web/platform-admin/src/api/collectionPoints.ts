/**
 * Collection Points API Module
 *
 * API functions for collection point management (CRUD operations).
 * Maps to BFF /api/admin/collection-points endpoints.
 *
 * Story 9.4: Collection Point Management
 */

import apiClient from './client';
import type {
  CollectionPointDetailFull,
  CollectionPointListParams,
  CollectionPointListResponse,
  CollectionPointUpdateRequest,
} from './types';

const BASE_PATH = '/admin/collection-points';

/**
 * Get collection point detail by ID.
 *
 * @param cpId - Collection point ID (format: {region}-cp-XXX)
 * @returns Full collection point detail with operating hours, capacity, etc.
 */
export async function getCollectionPoint(cpId: string): Promise<CollectionPointDetailFull> {
  const { data } = await apiClient.get<CollectionPointDetailFull>(`${BASE_PATH}/${cpId}`);
  return data;
}

/**
 * Update an existing collection point.
 *
 * @param cpId - Collection point ID to update
 * @param request - Fields to update (partial update supported)
 * @returns Updated collection point detail
 */
export async function updateCollectionPoint(
  cpId: string,
  request: CollectionPointUpdateRequest
): Promise<CollectionPointDetailFull> {
  const { data } = await apiClient.put<CollectionPointDetailFull>(`${BASE_PATH}/${cpId}`, request);
  return data;
}

/**
 * List collection points for a factory.
 *
 * @param params - Query parameters including required factory_id
 * @returns Paginated list of collection point summaries
 */
export async function listCollectionPoints(
  params: CollectionPointListParams
): Promise<CollectionPointListResponse> {
  const queryParams: Record<string, unknown> = {
    factory_id: params.factory_id,
    ...(params.page_size !== undefined && { page_size: params.page_size }),
    ...(params.page_token !== undefined && { page_token: params.page_token }),
    ...(params.active_only !== undefined && { active_only: params.active_only }),
  };
  const { data } = await apiClient.get<CollectionPointListResponse>(BASE_PATH, queryParams);
  return data;
}

/** Re-export types for convenience */
export type {
  CollectionPointCapacity,
  CollectionPointCreateRequest,
  CollectionPointDetail,
  CollectionPointDetailFull,
  CollectionPointFormData,
  CollectionPointListParams,
  CollectionPointListResponse,
  CollectionPointStatus,
  CollectionPointSummary,
  CollectionPointUpdateRequest,
  LeadFarmerSummary,
  OperatingHours,
} from './types';

export {
  COLLECTION_DAYS,
  CP_FORM_DEFAULTS,
  cpDetailToFormData,
  cpFormDataToUpdateRequest,
  formatTimeRange,
  parseTimeRange,
  STORAGE_TYPE_OPTIONS,
} from './types';
