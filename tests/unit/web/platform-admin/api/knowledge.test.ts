/**
 * Unit tests for Knowledge API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.9b - Knowledge Management UI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  listDocuments,
  searchDocuments,
  getDocument,
  createDocument,
  updateDocument,
  deleteDocument,
  stageDocument,
  activateDocument,
  archiveDocument,
  rollbackDocument,
  getExtractionJob,
  listChunks,
  vectorizeDocument,
  getVectorizationJob,
  queryKnowledge,
  createExtractionProgressStream,
} from '../../../../../web/platform-admin/src/api/knowledge';
import type {
  DocumentListResponse,
  DocumentDetail,
  DeleteDocumentResponse,
  ExtractionJobStatus,
  ChunkListResponse,
  VectorizationJobStatus,
  QueryResponse,
} from '../../../../../web/platform-admin/src/api/types';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockDocument: DocumentDetail = {
  id: 'doc-123:v1',
  document_id: 'doc-123',
  version: 1,
  title: 'Blister Blight Treatment Guide',
  domain: 'plant_diseases',
  content: '# Blister Blight\n\nTreatment info...',
  status: 'draft',
  metadata: {
    author: 'Dr. Njeri Kamau',
    source: 'TBK Research',
    region: 'Nyeri',
    season: '',
    tags: [],
  },
  source_file: {
    filename: 'guide.pdf',
    file_type: 'pdf',
    file_size_bytes: 1024000,
    extraction_method: 'ocr',
    extraction_confidence: 0.94,
    page_count: 12,
  },
  change_summary: '',
  pinecone_namespace: 'draft',
  content_hash: 'abc123',
  created_at: '2025-12-22T10:00:00Z',
  updated_at: '2025-12-22T10:00:00Z',
};

const mockListResponse: DocumentListResponse = {
  data: [
    {
      document_id: 'doc-123',
      version: 1,
      title: 'Blister Blight Treatment Guide',
      domain: 'plant_diseases',
      status: 'active',
      author: 'Dr. Njeri Kamau',
      created_at: '2025-12-22T10:00:00Z',
      updated_at: '2025-12-22T10:00:00Z',
    },
  ],
  pagination: {
    total_count: 1,
    page_size: 20,
    page: 1,
    next_page_token: null,
    has_next: false,
    total_pages: 1,
    has_prev: false,
  },
};

describe('Knowledge API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('listDocuments', () => {
    it('should fetch documents with default params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockListResponse });
      const result = await listDocuments();
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge', {});
      expect(result.data).toHaveLength(1);
      expect(result.data[0].title).toBe('Blister Blight Treatment Guide');
    });

    it('should pass domain and status filters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockListResponse });
      await listDocuments({ domain: 'plant_diseases', status: 'active', page: 1, page_size: 20 });
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge', {
        domain: 'plant_diseases',
        status: 'active',
        page: 1,
        page_size: 20,
      });
    });

    it('should not include empty string filters', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockListResponse });
      await listDocuments({ domain: '', status: '' });
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge', {});
    });
  });

  describe('searchDocuments', () => {
    it('should search with query', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockListResponse });
      await searchDocuments({ query: 'blight' });
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/search', { query: 'blight' });
    });

    it('should pass domain filter with search', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockListResponse });
      await searchDocuments({ query: 'blight', domain: 'plant_diseases' });
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/search', {
        query: 'blight',
        domain: 'plant_diseases',
      });
    });
  });

  describe('getDocument', () => {
    it('should fetch document by ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDocument });
      const result = await getDocument('doc-123');
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/doc-123', {});
      expect(result.title).toBe('Blister Blight Treatment Guide');
    });

    it('should pass version param', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDocument });
      await getDocument('doc-123', 2);
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/doc-123', { version: 2 });
    });
  });

  describe('createDocument', () => {
    it('should create document with required fields', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockDocument });
      const result = await createDocument({ title: 'New Doc', domain: 'tea_cultivation' });
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge', {
        title: 'New Doc',
        domain: 'tea_cultivation',
      });
      expect(result.document_id).toBe('doc-123');
    });
  });

  describe('updateDocument', () => {
    it('should update document with change summary', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: { ...mockDocument, version: 2 } });
      const result = await updateDocument('doc-123', {
        content: 'Updated content',
        change_summary: 'Updated treatment recommendations',
      });
      expect(apiClient.put).toHaveBeenCalledWith('/admin/knowledge/doc-123', {
        content: 'Updated content',
        change_summary: 'Updated treatment recommendations',
      });
      expect(result.version).toBe(2);
    });
  });

  describe('deleteDocument', () => {
    it('should archive document', async () => {
      const mockDelete: DeleteDocumentResponse = { versions_archived: 3 };
      vi.mocked(apiClient.delete).mockResolvedValue({ data: mockDelete });
      const result = await deleteDocument('doc-123');
      expect(apiClient.delete).toHaveBeenCalledWith('/admin/knowledge/doc-123');
      expect(result.versions_archived).toBe(3);
    });
  });

  describe('lifecycle operations', () => {
    it('stageDocument should POST to stage endpoint', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { ...mockDocument, status: 'staged' } });
      const result = await stageDocument('doc-123');
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/doc-123/stage');
      expect(result.status).toBe('staged');
    });

    it('activateDocument should POST to activate endpoint', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { ...mockDocument, status: 'active' } });
      const result = await activateDocument('doc-123');
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/doc-123/activate');
      expect(result.status).toBe('active');
    });

    it('archiveDocument should POST to archive endpoint', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { ...mockDocument, status: 'archived' } });
      const result = await archiveDocument('doc-123');
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/doc-123/archive');
      expect(result.status).toBe('archived');
    });

    it('rollbackDocument should POST with target version', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: { ...mockDocument, version: 3, status: 'draft' } });
      const result = await rollbackDocument('doc-123', 1);
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/doc-123/rollback', { target_version: 1 });
      expect(result.version).toBe(3);
      expect(result.status).toBe('draft');
    });
  });

  describe('extraction', () => {
    it('getExtractionJob should fetch job status', async () => {
      const mockJob: ExtractionJobStatus = {
        job_id: 'job-1',
        document_id: 'doc-123',
        status: 'completed',
        progress_percent: 100,
        pages_processed: 12,
        total_pages: 12,
        error_message: '',
        started_at: '2025-12-22T10:00:00Z',
        completed_at: '2025-12-22T10:01:00Z',
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockJob });
      const result = await getExtractionJob('doc-123', 'job-1');
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/doc-123/extraction/job-1');
      expect(result.status).toBe('completed');
    });
  });

  describe('createExtractionProgressStream', () => {
    it('should call fetch with auth header and return cleanup function', () => {
      vi.stubGlobal('localStorage', { getItem: vi.fn().mockReturnValue('test-token'), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn(), length: 0, key: vi.fn() });

      const mockAbort = vi.fn();
      vi.stubGlobal('AbortController', vi.fn().mockImplementation(() => ({
        signal: 'mock-signal',
        abort: mockAbort,
      })));

      const mockFetch = vi.fn().mockReturnValue(new Promise(() => {}));
      vi.stubGlobal('fetch', mockFetch);

      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      const cleanup = createExtractionProgressStream('doc-123', 'job-1', onProgress, onComplete, onError);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/admin/knowledge/doc-123/extraction/progress?job_id=job-1'),
        expect.objectContaining({
          headers: { Accept: 'text/event-stream', Authorization: 'Bearer test-token' },
          signal: 'mock-signal',
        }),
      );

      cleanup();
      expect(mockAbort).toHaveBeenCalled();

      vi.unstubAllGlobals();
    });

    it('should call onProgress when progress SSE event received', async () => {
      vi.stubGlobal('localStorage', { getItem: vi.fn().mockReturnValue('test-token'), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn(), length: 0, key: vi.fn() });

      const sseData = 'event: progress\ndata: {"percent":50,"status":"in_progress","message":"Pages 6/12","pages_processed":6,"total_pages":12}\n\nevent: complete\ndata: {}\n\n';
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        },
      });

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: stream,
      }));

      const onProgress = vi.fn();
      const onComplete = vi.fn();
      const onError = vi.fn();

      createExtractionProgressStream('doc-123', 'job-1', onProgress, onComplete, onError);

      // Wait for async stream processing
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(onProgress).toHaveBeenCalledWith({
        percent: 50,
        status: 'in_progress',
        message: 'Pages 6/12',
        pages_processed: 6,
        total_pages: 12,
      });
      expect(onComplete).toHaveBeenCalled();

      vi.unstubAllGlobals();
    });
  });

  describe('chunks and vectorization', () => {
    it('listChunks should fetch with pagination', async () => {
      const mockChunks: ChunkListResponse = {
        data: [
          {
            chunk_id: 'chunk-1',
            document_id: 'doc-123',
            document_version: 1,
            chunk_index: 0,
            content: 'First chunk content',
            section_title: 'Introduction',
            word_count: 50,
            char_count: 300,
            pinecone_id: 'vec-1',
            created_at: '2025-12-22T10:00:00Z',
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 20,
          page: 1,
          next_page_token: null,
          has_next: false,
          total_pages: 1,
          has_prev: false,
        },
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockChunks });
      const result = await listChunks('doc-123', { page: 1, page_size: 20 });
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/doc-123/chunks', { page: 1, page_size: 20 });
      expect(result.data).toHaveLength(1);
    });

    it('vectorizeDocument should POST to vectorize', async () => {
      const mockJob: VectorizationJobStatus = {
        job_id: 'vjob-1',
        status: 'pending',
        document_id: 'doc-123',
        document_version: 1,
        namespace: 'staging',
        chunks_total: 0,
        chunks_embedded: 0,
        chunks_stored: 0,
        failed_count: 0,
        content_hash: 'abc123',
        error_message: '',
        started_at: null,
        completed_at: null,
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockJob });
      const result = await vectorizeDocument('doc-123');
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/doc-123/vectorize', { version: 0 });
      expect(result.job_id).toBe('vjob-1');
    });

    it('getVectorizationJob should fetch job status', async () => {
      const mockJob: VectorizationJobStatus = {
        job_id: 'vjob-1',
        status: 'completed',
        document_id: 'doc-123',
        document_version: 1,
        namespace: 'staging',
        chunks_total: 5,
        chunks_embedded: 5,
        chunks_stored: 5,
        failed_count: 0,
        content_hash: 'abc123',
        error_message: '',
        started_at: '2025-12-22T10:00:00Z',
        completed_at: '2025-12-22T10:01:00Z',
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockJob });
      const result = await getVectorizationJob('doc-123', 'vjob-1');
      expect(apiClient.get).toHaveBeenCalledWith('/admin/knowledge/doc-123/vectorization/vjob-1');
      expect(result.status).toBe('completed');
    });
  });

  describe('queryKnowledge', () => {
    it('should query knowledge base', async () => {
      const mockQuery: QueryResponse = {
        matches: [
          {
            chunk_id: 'chunk-1',
            content: 'Blister blight is caused by...',
            score: 0.95,
            document_id: 'doc-123',
            title: 'Blister Blight Treatment Guide',
            domain: 'plant_diseases',
          },
        ],
        query: 'What causes blister blight?',
        total_matches: 1,
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockQuery });
      const result = await queryKnowledge({
        query: 'What causes blister blight?',
        domains: ['plant_diseases'],
        top_k: 3,
      });
      expect(apiClient.post).toHaveBeenCalledWith('/admin/knowledge/query', {
        query: 'What causes blister blight?',
        domains: ['plant_diseases'],
        top_k: 3,
      });
      expect(result.matches).toHaveLength(1);
      expect(result.matches[0].score).toBe(0.95);
    });
  });
});
