/**
 * Knowledge API Module
 *
 * API functions for knowledge document management (CRUD, lifecycle, upload, query).
 * Maps to BFF /api/admin/knowledge endpoints.
 *
 * Story 9.9b: Knowledge Management UI
 */

import apiClient from './client';
import type {
  ChunkListResponse,
  CreateDocumentRequest,
  DeleteDocumentResponse,
  DocumentDetail,
  DocumentListResponse,
  ExtractionJobStatus,
  ExtractionProgressEvent,
  KnowledgeDomain,
  KnowledgeListParams,
  KnowledgeSearchParams,
  QueryKnowledgeRequest,
  QueryResponse,
  RollbackDocumentRequest,
  UpdateDocumentRequest,
  VectorizationJobStatus,
} from './types';

const BASE_PATH = '/admin/knowledge';

// ============================================================================
// CRUD Operations
// ============================================================================

/**
 * List knowledge documents with filtering and pagination.
 */
export async function listDocuments(params: KnowledgeListParams = {}): Promise<DocumentListResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params.domain !== undefined && params.domain !== '' && { domain: params.domain }),
    ...(params.status !== undefined && params.status !== '' && { status: params.status }),
    ...(params.author !== undefined && params.author !== '' && { author: params.author }),
    ...(params.page !== undefined && { page: params.page }),
    ...(params.page_size !== undefined && { page_size: params.page_size }),
  };
  const { data } = await apiClient.get<DocumentListResponse>(BASE_PATH, queryParams);
  return data;
}

/**
 * Search knowledge documents by query.
 */
export async function searchDocuments(params: KnowledgeSearchParams): Promise<DocumentListResponse> {
  const queryParams: Record<string, unknown> = {
    query: params.query,
    ...(params.domain !== undefined && params.domain !== '' && { domain: params.domain }),
    ...(params.top_k !== undefined && { top_k: params.top_k }),
  };
  const { data } = await apiClient.get<DocumentListResponse>(`${BASE_PATH}/search`, queryParams);
  return data;
}

/**
 * Get document detail by ID, optionally for a specific version.
 */
export async function getDocument(documentId: string, version?: number): Promise<DocumentDetail> {
  const queryParams: Record<string, unknown> = {
    ...(version !== undefined && { version }),
  };
  const { data } = await apiClient.get<DocumentDetail>(`${BASE_PATH}/${documentId}`, queryParams);
  return data;
}

/**
 * Create a new knowledge document (manual content creation).
 */
export async function createDocument(request: CreateDocumentRequest): Promise<DocumentDetail> {
  const { data } = await apiClient.post<DocumentDetail>(BASE_PATH, request);
  return data;
}

/**
 * Update an existing document (creates new version, requires change_summary).
 */
export async function updateDocument(documentId: string, request: UpdateDocumentRequest): Promise<DocumentDetail> {
  const { data } = await apiClient.put<DocumentDetail>(`${BASE_PATH}/${documentId}`, request);
  return data;
}

/**
 * Delete (archive) a document and all its versions.
 */
export async function deleteDocument(documentId: string): Promise<DeleteDocumentResponse> {
  const { data } = await apiClient.delete<DeleteDocumentResponse>(`${BASE_PATH}/${documentId}`);
  return data;
}

// ============================================================================
// Lifecycle Operations
// ============================================================================

/**
 * Stage a draft document for review.
 */
export async function stageDocument(documentId: string): Promise<DocumentDetail> {
  const { data } = await apiClient.post<DocumentDetail>(`${BASE_PATH}/${documentId}/stage`);
  return data;
}

/**
 * Activate a staged document for production use.
 */
export async function activateDocument(documentId: string): Promise<DocumentDetail> {
  const { data } = await apiClient.post<DocumentDetail>(`${BASE_PATH}/${documentId}/activate`);
  return data;
}

/**
 * Archive a document (remove from production).
 */
export async function archiveDocument(documentId: string): Promise<DocumentDetail> {
  const { data } = await apiClient.post<DocumentDetail>(`${BASE_PATH}/${documentId}/archive`);
  return data;
}

/**
 * Rollback document to a previous version (creates new draft from that version).
 */
export async function rollbackDocument(documentId: string, targetVersion: number): Promise<DocumentDetail> {
  const body: RollbackDocumentRequest = { target_version: targetVersion };
  const { data } = await apiClient.post<DocumentDetail>(`${BASE_PATH}/${documentId}/rollback`, body);
  return data;
}

// ============================================================================
// Upload & Extraction
// ============================================================================

/**
 * Upload a document file with metadata (multipart form).
 * Uses native fetch for FormData support.
 */
export async function uploadDocument(
  file: File,
  metadata: { title: string; domain: KnowledgeDomain; author?: string; source?: string; region?: string },
): Promise<ExtractionJobStatus> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', metadata.title);
  formData.append('domain', metadata.domain);
  if (metadata.author) formData.append('author', metadata.author);
  if (metadata.source) formData.append('source', metadata.source);
  if (metadata.region) formData.append('region', metadata.region);

  const token = localStorage.getItem('fp_auth_token');
  const baseURL = import.meta.env.VITE_BFF_URL || '/api';

  const response = await fetch(`${baseURL}${BASE_PATH}/upload`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (response.status === 401) {
    localStorage.removeItem('fp_auth_token');
    const baseUrl = import.meta.env.VITE_BASE_URL || '/';
    window.location.href = baseUrl;
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error((errorData as { detail?: string }).detail || `Upload failed: ${response.status}`);
  }

  return response.json() as Promise<ExtractionJobStatus>;
}

/**
 * Poll extraction job status.
 */
export async function getExtractionJob(documentId: string, jobId: string): Promise<ExtractionJobStatus> {
  const { data } = await apiClient.get<ExtractionJobStatus>(`${BASE_PATH}/${documentId}/extraction/${jobId}`);
  return data;
}

/**
 * Create an SSE stream for extraction progress updates using fetch.
 * Uses fetch instead of EventSource to support Authorization headers.
 * Returns a cleanup function to abort the connection.
 */
export function createExtractionProgressStream(
  documentId: string,
  jobId: string,
  onProgress: (event: ExtractionProgressEvent) => void,
  onComplete: () => void,
  onError: (error: string) => void,
): () => void {
  const baseURL = import.meta.env.VITE_BFF_URL || '/api';
  const url = `${baseURL}${BASE_PATH}/${documentId}/extraction/progress?job_id=${jobId}`;
  const token = localStorage.getItem('fp_auth_token');
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(url, {
        headers: {
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('fp_auth_token');
          const baseUrl = import.meta.env.VITE_BASE_URL || '/';
          window.location.href = baseUrl;
        }
        onError(`Connection failed: ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError('Stream not available');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        let eventType = '';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6);
          } else if (line === '' && eventType && eventData) {
            if (eventType === 'progress') {
              const parsed: ExtractionProgressEvent = JSON.parse(eventData);
              onProgress(parsed);
            } else if (eventType === 'complete') {
              onComplete();
              reader.cancel();
              return;
            } else if (eventType === 'error') {
              onError(eventData || 'Extraction error');
              reader.cancel();
              return;
            }
            eventType = '';
            eventData = '';
          }
        }
      }

      // Stream ended without explicit complete event
      onComplete();
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError('Connection lost');
      }
    }
  })();

  return () => controller.abort();
}

// ============================================================================
// Chunks & Vectorization
// ============================================================================

/**
 * List chunks for a document with pagination.
 */
export async function listChunks(
  documentId: string,
  params?: { page?: number; page_size?: number },
): Promise<ChunkListResponse> {
  const queryParams: Record<string, unknown> = {
    ...(params?.page !== undefined && { page: params.page }),
    ...(params?.page_size !== undefined && { page_size: params.page_size }),
  };
  const { data } = await apiClient.get<ChunkListResponse>(`${BASE_PATH}/${documentId}/chunks`, queryParams);
  return data;
}

/**
 * Trigger vectorization for a document.
 */
export async function vectorizeDocument(documentId: string, version?: number): Promise<VectorizationJobStatus> {
  const body = { version: version ?? 0 };
  const { data } = await apiClient.post<VectorizationJobStatus>(`${BASE_PATH}/${documentId}/vectorize`, body);
  return data;
}

/**
 * Poll vectorization job status.
 */
export async function getVectorizationJob(documentId: string, jobId: string): Promise<VectorizationJobStatus> {
  const { data } = await apiClient.get<VectorizationJobStatus>(`${BASE_PATH}/${documentId}/vectorization/${jobId}`);
  return data;
}

// ============================================================================
// Query
// ============================================================================

/**
 * Query the knowledge base (Test with AI feature).
 */
export async function queryKnowledge(request: QueryKnowledgeRequest): Promise<QueryResponse> {
  const { data } = await apiClient.post<QueryResponse>(`${BASE_PATH}/query`, request);
  return data;
}
