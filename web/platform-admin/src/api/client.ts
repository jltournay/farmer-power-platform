/**
 * API Client Configuration
 *
 * Fetch-based API client with authentication for BFF API.
 * Environment-aware base URL configuration.
 */

/**
 * Standard API error response structure from BFF.
 */
export interface ApiErrorResponse {
  error: string;
  detail: string;
  code?: string;
}

/**
 * API Client class for making authenticated requests to the BFF.
 */
class ApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = import.meta.env.VITE_BFF_URL || '/api';
  }

  /**
   * Get authentication headers with JWT token.
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Handle response and extract data or throw error.
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const errorData = (await response.json().catch(() => ({}))) as ApiErrorResponse;
      throw new Error(errorData.detail || `HTTP error ${response.status}`);
    }

    return response.json() as Promise<T>;
  }

  /**
   * Build URL with query parameters.
   */
  private buildUrl(path: string, params?: Record<string, unknown>): string {
    const url = new URL(path, this.baseURL.startsWith('http') ? this.baseURL : window.location.origin + this.baseURL);

    if (!this.baseURL.startsWith('http')) {
      url.pathname = this.baseURL + path;
    }

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    return url.toString();
  }

  /**
   * GET request.
   */
  async get<T>(path: string, params?: Record<string, unknown>): Promise<{ data: T }> {
    const response = await fetch(this.buildUrl(path, params), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    const data = await this.handleResponse<T>(response);
    return { data };
  }

  /**
   * POST request.
   */
  async post<T>(path: string, body?: unknown): Promise<{ data: T }> {
    const response = await fetch(this.buildUrl(path), {
      method: 'POST',
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await this.handleResponse<T>(response);
    return { data };
  }

  /**
   * PUT request.
   */
  async put<T>(path: string, body?: unknown): Promise<{ data: T }> {
    const response = await fetch(this.buildUrl(path), {
      method: 'PUT',
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await this.handleResponse<T>(response);
    return { data };
  }

  /**
   * DELETE request.
   */
  async delete<T>(path: string): Promise<{ data: T }> {
    const response = await fetch(this.buildUrl(path), {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    const data = await this.handleResponse<T>(response);
    return { data };
  }
}

/**
 * Create API client instance.
 */
export function createApiClient(): ApiClient {
  return new ApiClient();
}

// Singleton instance for app-wide use
export const apiClient = createApiClient();

export default apiClient;
