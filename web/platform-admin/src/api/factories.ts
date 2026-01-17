/**
 * Factories API Module
 *
 * API functions for factory management (CRUD operations).
 * Maps to BFF /api/admin/factories endpoints.
 */

import apiClient from './client';
import type {
  CollectionPointCreateRequest,
  CollectionPointDetail,
  FactoryCreateRequest,
  FactoryDetail,
  FactoryListParams,
  FactoryListResponse,
  FactoryUpdateRequest,
} from './types';

const BASE_PATH = '/admin/factories';

/**
 * List all factories with pagination.
 *
 * @param params - Query parameters for filtering/pagination
 * @returns Paginated list of factory summaries
 */
export async function listFactories(params: FactoryListParams = {}): Promise<FactoryListResponse> {
  const { data } = await apiClient.get<FactoryListResponse>(BASE_PATH, params as Record<string, unknown>);
  return data;
}

/**
 * Get factory detail by ID.
 *
 * @param factoryId - Factory ID (format: KEN-FAC-XXX or KEN-E2E-XXX)
 * @returns Full factory detail including quality thresholds and collection points
 */
export async function getFactory(factoryId: string): Promise<FactoryDetail> {
  const { data } = await apiClient.get<FactoryDetail>(`${BASE_PATH}/${factoryId}`);
  return data;
}

/**
 * Create a new factory.
 *
 * @param request - Factory creation payload
 * @returns Created factory detail
 */
export async function createFactory(request: FactoryCreateRequest): Promise<FactoryDetail> {
  const { data } = await apiClient.post<FactoryDetail>(BASE_PATH, request);
  return data;
}

/**
 * Update an existing factory.
 *
 * @param factoryId - Factory ID to update
 * @param request - Fields to update (partial update supported)
 * @returns Updated factory detail
 */
export async function updateFactory(
  factoryId: string,
  request: FactoryUpdateRequest
): Promise<FactoryDetail> {
  const { data } = await apiClient.put<FactoryDetail>(`${BASE_PATH}/${factoryId}`, request);
  return data;
}

/**
 * Create a collection point under a factory.
 *
 * @param factoryId - Parent factory ID
 * @param request - Collection point creation payload
 * @returns Created collection point detail
 */
export async function createCollectionPoint(
  factoryId: string,
  request: CollectionPointCreateRequest
): Promise<CollectionPointDetail> {
  const { data } = await apiClient.post<CollectionPointDetail>(
    `${BASE_PATH}/${factoryId}/collection-points`,
    request
  );
  return data;
}

/** Re-export types for convenience */
export type {
  CollectionPointCreateRequest,
  CollectionPointDetail,
  CollectionPointSummary,
  ContactInfo,
  FactoryCreateRequest,
  FactoryDetail,
  FactoryFormData,
  FactoryListParams,
  FactoryListResponse,
  FactorySummary,
  FactoryUpdateRequest,
  GeoLocation,
  GradingModelSummary,
  PaymentPolicyAPI,
  PaymentPolicyType,
  QualityThresholdsAPI,
} from './types';

export {
  FACTORY_FORM_DEFAULTS,
  factoryDetailToFormData,
  factoryFormDataToCreateRequest,
  factoryFormDataToUpdateRequest,
} from './types';
