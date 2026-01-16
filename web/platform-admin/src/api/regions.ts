/**
 * Regions API Module
 *
 * API functions for region management (CRUD operations).
 * Maps to BFF /api/admin/regions endpoints.
 */

import apiClient from './client';
import type {
  RegionCreateRequest,
  RegionDetail,
  RegionListParams,
  RegionListResponse,
  RegionUpdateRequest,
} from './types';

const BASE_PATH = '/admin/regions';

/**
 * List all regions with pagination.
 *
 * @param params - Query parameters for filtering/pagination
 * @returns Paginated list of region summaries
 */
export async function listRegions(params: RegionListParams = {}): Promise<RegionListResponse> {
  const { data } = await apiClient.get<RegionListResponse>(BASE_PATH, params as Record<string, unknown>);
  return data;
}

/**
 * Get region detail by ID.
 *
 * @param regionId - Region ID (format: {county}-{altitude_band})
 * @returns Full region detail including weather config and boundaries
 */
export async function getRegion(regionId: string): Promise<RegionDetail> {
  const { data } = await apiClient.get<RegionDetail>(`${BASE_PATH}/${regionId}`);
  return data;
}

/**
 * Create a new region.
 *
 * @param request - Region creation payload
 * @returns Created region detail
 */
export async function createRegion(request: RegionCreateRequest): Promise<RegionDetail> {
  const { data } = await apiClient.post<RegionDetail>(BASE_PATH, request);
  return data;
}

/**
 * Update an existing region.
 *
 * @param regionId - Region ID to update
 * @param request - Fields to update (partial update supported)
 * @returns Updated region detail
 */
export async function updateRegion(
  regionId: string,
  request: RegionUpdateRequest
): Promise<RegionDetail> {
  const { data } = await apiClient.put<RegionDetail>(`${BASE_PATH}/${regionId}`, request);
  return data;
}

/** Re-export types for convenience */
export type {
  RegionCreateRequest,
  RegionDetail,
  RegionListParams,
  RegionListResponse,
  RegionUpdateRequest,
} from './types';
