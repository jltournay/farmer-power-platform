/**
 * Farmers API Module
 *
 * API functions for farmer management (CRUD operations).
 * Maps to BFF /api/admin/farmers endpoints.
 *
 * Story 9.5: Farmer Management
 */

import apiClient from './client';
import type {
  FarmerCreateRequest,
  FarmerDetail,
  FarmerImportResponse,
  FarmerListParams,
  FarmerListResponse,
  FarmerUpdateRequest,
} from './types';

const BASE_PATH = '/admin/farmers';

/**
 * List all farmers with pagination and filtering.
 *
 * @param params - Query parameters for filtering/pagination
 * @returns Paginated list of farmer summaries
 */
export async function listFarmers(params: FarmerListParams = {}): Promise<FarmerListResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.page_size !== undefined && { page_size: params.page_size }),
    ...(params.page_token !== undefined && { page_token: params.page_token }),
    ...(params.region_id !== undefined && { region_id: params.region_id }),
    ...(params.collection_point_id !== undefined && { collection_point_id: params.collection_point_id }),
    ...(params.farm_scale !== undefined && { farm_scale: params.farm_scale }),
    ...(params.tier !== undefined && { tier: params.tier }),
    ...(params.active_only !== undefined && { active_only: params.active_only }),
    ...(params.search !== undefined && params.search !== '' && { search: params.search }),
  };
  const { data } = await apiClient.get<FarmerListResponse>(BASE_PATH, queryParams);
  return data;
}

/**
 * Get farmer detail by ID.
 *
 * @param farmerId - Farmer ID (format: WM-XXXX)
 * @returns Full farmer detail including performance metrics
 */
export async function getFarmer(farmerId: string): Promise<FarmerDetail> {
  const { data } = await apiClient.get<FarmerDetail>(`${BASE_PATH}/${farmerId}`);
  return data;
}

/**
 * Create a new farmer.
 *
 * @param request - Farmer creation payload
 * @returns Created farmer detail
 */
export async function createFarmer(request: FarmerCreateRequest): Promise<FarmerDetail> {
  const { data } = await apiClient.post<FarmerDetail>(BASE_PATH, request);
  return data;
}

/**
 * Update an existing farmer.
 *
 * @param farmerId - Farmer ID to update
 * @param request - Fields to update (partial update supported)
 * @returns Updated farmer detail
 */
export async function updateFarmer(
  farmerId: string,
  request: FarmerUpdateRequest
): Promise<FarmerDetail> {
  const { data } = await apiClient.put<FarmerDetail>(`${BASE_PATH}/${farmerId}`, request);
  return data;
}

/**
 * Import farmers from CSV file.
 *
 * Story 9.5a: defaultCollectionPointId removed - CP assigned on first delivery
 *
 * @param file - CSV file to import
 * @param skipHeader - Whether to skip the first row (default: true)
 * @returns Import results with success/error counts
 */
export async function importFarmers(
  file: File,
  skipHeader: boolean = true
): Promise<FarmerImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  // Story 9.5a: collection_point_id removed - CP assigned on first delivery
  formData.append('skip_header', String(skipHeader));

  // Use native fetch for multipart/form-data
  const token = localStorage.getItem('fp_auth_token');
  const baseURL = import.meta.env.VITE_BFF_URL || '/api';
  const url = `${baseURL}${BASE_PATH}/import`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error((errorData as { detail?: string }).detail || `HTTP error ${response.status}`);
  }

  return response.json() as Promise<FarmerImportResponse>;
}

/** Re-export types for convenience */
export type {
  CollectionPointSummaryForFarmer,
  CommunicationPreferences,
  FarmerCreateRequest,
  FarmerDetail,
  FarmerFormData,
  FarmerImportResponse,
  FarmerListParams,
  FarmerListResponse,
  FarmerPerformanceMetrics,
  FarmerSummary,
  FarmerUpdateRequest,
  FarmScale,
  ImportErrorRow,
  InteractionPreference,
  NotificationChannel,
  PreferredLanguage,
  TierLevel,
  TrendIndicator,
} from './types';

export {
  FARMER_FORM_DEFAULTS,
  FARM_SCALE_OPTIONS,
  getTierColor,
  getTrendColor,
  getTrendIcon,
  INTERACTION_PREF_OPTIONS,
  LANGUAGE_OPTIONS,
  NOTIFICATION_CHANNEL_OPTIONS,
  TIER_LEVEL_OPTIONS,
  farmerDetailToFormData,
  farmerFormDataToCreateRequest,
  farmerFormDataToUpdateRequest,
} from './types';
