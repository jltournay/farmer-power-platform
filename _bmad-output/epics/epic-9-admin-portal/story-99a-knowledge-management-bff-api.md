# Story 9.9a: Knowledge Management BFF REST API

As a **frontend developer**,
I want **REST API endpoints in the BFF for knowledge document management**,
So that **the Knowledge Management UI can perform CRUD, lifecycle, and extraction operations on RAG documents**.

## Acceptance Criteria

**AC 9.9a.1: Document CRUD Endpoints**

**Given** the BFF is running
**When** I call the knowledge management REST endpoints
**Then** the following operations are available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/knowledge` | List documents (paginated, filterable by domain/status/author) |
| `GET` | `/api/v1/admin/knowledge/search` | Search documents by title/content |
| `GET` | `/api/v1/admin/knowledge/{document_id}` | Get document details (specific version or active) |
| `POST` | `/api/v1/admin/knowledge` | Create new document (with metadata) |
| `PUT` | `/api/v1/admin/knowledge/{document_id}` | Update document (creates new version) |
| `DELETE` | `/api/v1/admin/knowledge/{document_id}` | Delete/archive document |

**AC 9.9a.2: Document Lifecycle Endpoints**

**Given** a document exists in a valid state
**When** I call lifecycle transition endpoints
**Then** the following transitions are available:

| Method | Path | Transition |
|--------|------|------------|
| `POST` | `/api/v1/admin/knowledge/{document_id}/stage` | draft -> staged |
| `POST` | `/api/v1/admin/knowledge/{document_id}/activate` | staged -> active (archives previous active) |
| `POST` | `/api/v1/admin/knowledge/{document_id}/archive` | any -> archived |
| `POST` | `/api/v1/admin/knowledge/{document_id}/rollback` | Creates new draft from old version |

**AC 9.9a.3: File Upload & Extraction Endpoints**

**Given** I upload a document file (PDF, DOCX, MD, TXT)
**When** I call the upload endpoint with multipart form data
**Then**:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/knowledge/upload` | Upload file + metadata, triggers extraction |
| `GET` | `/api/v1/admin/knowledge/{document_id}/extraction/{job_id}` | Poll extraction job status |

**And** the upload endpoint accepts multipart form with file + metadata fields (title, domain, author, source, region)
**And** the file is stored in Azure Blob Storage
**And** extraction is triggered automatically after upload

**AC 9.9a.4: Extraction Progress SSE Streaming**

**Given** a document extraction is in progress
**When** I connect to the progress SSE endpoint
**Then**:

| Method | Path | Type | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/admin/knowledge/{document_id}/extraction/progress` | SSE stream | Real-time extraction progress |

**And** the endpoint returns `Content-Type: text/event-stream`
**And** events are formatted as: `event: progress\ndata: {"percent": 0-100, "status": "...", "message": "..."}\n\n`
**And** the endpoint uses `SSEManager` + `grpc_stream_to_sse` from BFF SSE infrastructure (Story 0.5.9)
**And** the endpoint wraps the gRPC `StreamExtractionProgress` server-streaming RPC

**AC 9.9a.5: Chunking & Vectorization Endpoints**

**Given** a document has been extracted
**When** I call chunking/vectorization endpoints
**Then**:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/knowledge/{document_id}/chunks` | List chunks (paginated) |
| `POST` | `/api/v1/admin/knowledge/{document_id}/vectorize` | Trigger vectorization |
| `GET` | `/api/v1/admin/knowledge/{document_id}/vectorization/{job_id}` | Poll vectorization job status |

**AC 9.9a.6: Knowledge Query Endpoint**

**Given** active documents exist in the knowledge base
**When** I call the query endpoint
**Then**:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/knowledge/query` | Query knowledge base (for "Test with AI" feature) |

**And** the response includes retrieval matches with content, score, and source document metadata

**AC 9.9a.7: Pydantic Request/Response Schemas**

**Given** the endpoints are implemented
**Then** all request/response models use Pydantic v2 schemas
**And** schemas are defined in `services/bff/src/bff/api/schemas/admin/knowledge_schemas.py`
**And** schemas include proper validation (e.g., domain enum, file type validation, max file size)

**AC 9.9a.8: Route Registration**

**Given** the knowledge routes are implemented
**Then** they are registered in the admin router
**And** accessible under the `/api/v1/admin/knowledge` prefix
**And** protected by admin authentication

## Technical Notes

- **gRPC Client:** Extend existing `AiModelClient` in `services/bff/src/bff/infrastructure/clients/ai_model_client.py` to call RAGDocumentService RPCs
- **SSE Infrastructure:** Use `SSEManager` and `grpc_stream_to_sse` from `bff.infrastructure.sse` (Story 0.5.9)
- **File Upload:** FastAPI `UploadFile` for multipart form handling
- **Blob Storage:** Azure Blob Storage for original file persistence
- **Proto Source of Truth:** All request/response shapes derive from `proto/ai_model/v1/ai_model.proto` RAGDocumentService definitions
- **DAPR Integration:** All gRPC calls go through DAPR sidecar service invocation (app-id: `ai-model`)

### gRPC RPCs Wrapped

| BFF Endpoint | gRPC RPC |
|---|---|
| `GET /knowledge` | `ListDocuments` |
| `GET /knowledge/search` | `SearchDocuments` |
| `GET /knowledge/{id}` | `GetDocument` |
| `POST /knowledge` | `CreateDocument` |
| `PUT /knowledge/{id}` | `UpdateDocument` |
| `DELETE /knowledge/{id}` | `DeleteDocument` |
| `POST /knowledge/{id}/stage` | `StageDocument` |
| `POST /knowledge/{id}/activate` | `ActivateDocument` |
| `POST /knowledge/{id}/archive` | `ArchiveDocument` |
| `POST /knowledge/{id}/rollback` | `RollbackDocument` |
| `POST /knowledge/upload` | `CreateDocument` + `ExtractDocument` |
| `GET /knowledge/{id}/extraction/{job_id}` | `GetExtractionJob` |
| `GET /knowledge/{id}/extraction/progress` | `StreamExtractionProgress` (SSE) |
| `GET /knowledge/{id}/chunks` | `ListChunks` |
| `POST /knowledge/{id}/vectorize` | `VectorizeDocument` |
| `GET /knowledge/{id}/vectorization/{job_id}` | `GetVectorizationJob` |
| `POST /knowledge/query` | `QueryKnowledge` |

## Dependencies

- Story 9.1: Platform Admin Application Scaffold
- Story 0.5.6: BFF Service Setup
- Story 0.5.9: BFF SSE Infrastructure (for extraction progress streaming)
- Story 0.75.10: RAG Document gRPC API (backend implementation)
- Story 0.75.10b: Document Extraction Operations
- Story 0.75.10d: Document Chunking Operations
- Story 0.75.13c: Vectorization gRPC Wiring
- Story 0.75.23: QueryKnowledge RPC

## Story Points: 3

---
