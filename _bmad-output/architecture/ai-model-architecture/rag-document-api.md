# RAG Document API

RAG documents are managed through a gRPC API exposed by the AI Model service. This enables:
- **Admin UI** for agronomists (non-technical experts) to manage knowledge
- **CLI** for Ops team automation and bulk operations

## RAG Document Pydantic Model

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class RAGDocumentMetadata(BaseModel):
    """Metadata for RAG document."""
    author: str                              # Agronomist who created/updated
    source: str | None = None                # Original source (book, research paper, etc.)
    region: str | None = None                # Geographic relevance (e.g., "Kenya", "Rwanda")
    season: str | None = None                # Seasonal relevance (e.g., "dry_season", "monsoon")
    tags: list[str] = []                     # Searchable tags


class SourceFile(BaseModel):
    """Original uploaded file reference (for PDF/DOCX uploads)."""
    filename: str                            # "blister-blight-guide.pdf"
    file_type: Literal["pdf", "docx", "md", "txt"]
    blob_path: str                           # Azure Blob path to original file
    file_size_bytes: int
    extraction_method: Literal[
        "manual",           # User typed content directly
        "text_extraction",  # PyMuPDF for digital PDFs
        "azure_doc_intel",  # Azure Document Intelligence for scanned/complex PDFs
        "vision_llm"        # Vision LLM for diagrams/tables
    ] | None = None
    extraction_confidence: float | None = None  # 0-1 quality score
    page_count: int | None = None


class RAGDocument(BaseModel):
    """RAG knowledge document for expert knowledge storage."""
    document_id: str                         # Stable ID across versions
    version: int = 1                         # Incrementing version number

    # Content
    title: str
    domain: Literal[
        "plant_diseases",
        "tea_cultivation",
        "weather_patterns",
        "quality_standards",
        "regional_context"
    ]
    content: str                             # Extracted/authored markdown text

    # Source file (if uploaded as PDF/DOCX)
    source_file: SourceFile | None = None    # Original file reference

    # Lifecycle
    status: Literal["draft", "staged", "active", "archived"] = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: RAGDocumentMetadata

    # Change tracking
    change_summary: str | None = None        # What changed from previous version

    # Embedding reference (populated after vectorization)
    pinecone_namespace: str | None = None    # e.g., "knowledge-v12"
    pinecone_ids: list[str] = []             # Vector IDs in Pinecone
    content_hash: str | None = None          # SHA256 for change detection
```

## PDF Ingestion Pipeline

Agronomists can upload PDFs directly. The system auto-detects the PDF type and uses the appropriate extraction method:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PDF INGESTION PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PDF Upload                                                         │
│      │                                                              │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    PDF TYPE DETECTION                        │   │
│  │  • Check if text layer exists                               │   │
│  │  • Detect scanned images                                    │   │
│  │  • Identify tables/diagrams                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│      │                                                              │
│      ├──► Digital PDF (has text layer)                             │
│      │    └─► PyMuPDF extraction                                   │
│      │        • Fast, cheap, accurate                              │
│      │        • ~100ms per page                                    │
│      │                                                              │
│      ├──► Scanned PDF (image-based)                                │
│      │    └─► Azure Document Intelligence                          │
│      │        • OCR + layout analysis                              │
│      │        • Table extraction                                   │
│      │        • ~2-5s per page                                     │
│      │                                                              │
│      └──► Complex PDF (diagrams, mixed content)                    │
│           └─► Vision LLM (Claude/GPT-4V)                           │
│               • Semantic understanding                             │
│               • Diagram description                                │
│               • ~5-10s per page, higher cost                       │
│                                                                     │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT                                    │   │
│  │  • Markdown content                                         │   │
│  │  • Original PDF stored in Azure Blob                        │   │
│  │  • Extraction confidence score                              │   │
│  │  • Review flag if confidence < 0.8                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Extraction Methods:**

| Method | Use Case | Speed | Cost | Accuracy |
|--------|----------|-------|------|----------|
| **PyMuPDF** | Digital PDFs with text layer | ~100ms/page | Free | 99%+ |
| **Azure Document Intelligence** | Scanned PDFs, forms, tables | ~2-5s/page | $0.01/page | 95%+ |
| **Vision LLM** | Complex diagrams, mixed content | ~5-10s/page | $0.02-0.05/page | 90%+ |

**Azure Document Intelligence Configuration:**

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential


class PDFExtractor:
    """Extract text from PDFs using appropriate method."""

    def __init__(self, settings: Settings):
        self.doc_intel_client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_intel_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key)
        )

    async def extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        """Extract content from PDF, auto-detecting best method."""
        # 1. Try text extraction first (fast, free)
        text_result = await self._try_text_extraction(pdf_bytes)
        if text_result.confidence > 0.9:
            return text_result

        # 2. Fall back to Azure Document Intelligence
        return await self._extract_with_azure(pdf_bytes, filename)

    async def _try_text_extraction(self, pdf_bytes: bytes) -> ExtractionResult:
        """Try PyMuPDF text extraction for digital PDFs."""
        import pymupdf

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        total_chars = 0

        for page in doc:
            text = page.get_text("markdown")
            pages_text.append(text)
            total_chars += len(text)

        # Low char count per page suggests scanned PDF
        avg_chars_per_page = total_chars / len(doc) if doc else 0
        confidence = min(1.0, avg_chars_per_page / 500)  # Expect ~500+ chars/page

        return ExtractionResult(
            content="\n\n---\n\n".join(pages_text),
            method="text_extraction",
            confidence=confidence,
            page_count=len(doc),
            review_recommended=confidence < 0.8
        )

    async def _extract_with_azure(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> ExtractionResult:
        """Extract using Azure Document Intelligence."""
        poller = await self.doc_intel_client.begin_analyze_document(
            model_id="prebuilt-layout",  # Best for general documents
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result = await poller.result()

        # Convert to markdown
        markdown_content = self._azure_result_to_markdown(result)

        return ExtractionResult(
            content=markdown_content,
            method="azure_doc_intel",
            confidence=0.95,  # Azure is generally reliable
            page_count=len(result.pages),
            review_recommended=False
        )

    def _azure_result_to_markdown(self, result) -> str:
        """Convert Azure Document Intelligence result to markdown."""
        sections = []

        for paragraph in result.paragraphs or []:
            # Handle headings
            if paragraph.role == "title":
                sections.append(f"# {paragraph.content}")
            elif paragraph.role == "sectionHeading":
                sections.append(f"## {paragraph.content}")
            else:
                sections.append(paragraph.content)

        # Handle tables
        for table in result.tables or []:
            sections.append(self._table_to_markdown(table))

        return "\n\n".join(sections)


class ExtractionResult(BaseModel):
    """Result of PDF extraction."""
    content: str
    method: Literal["text_extraction", "azure_doc_intel", "vision_llm"]
    confidence: float
    page_count: int
    review_recommended: bool
    warnings: list[str] = []
```

## gRPC API (Proto Definition)

```protobuf
// proto/ai_model/v1/rag_document.proto
syntax = "proto3";

package farmer_power.ai_model.v1;

import "google/protobuf/timestamp.proto";

service RAGDocumentService {
  // CRUD Operations
  rpc CreateDocument(CreateDocumentRequest) returns (CreateDocumentResponse);
  rpc GetDocument(GetDocumentRequest) returns (RAGDocument);
  rpc UpdateDocument(UpdateDocumentRequest) returns (RAGDocument);
  rpc DeleteDocument(DeleteDocumentRequest) returns (DeleteDocumentResponse);

  // List & Search
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse);
  rpc SearchDocuments(SearchDocumentsRequest) returns (SearchDocumentsResponse);

  // Lifecycle Management
  rpc StageDocument(StageDocumentRequest) returns (RAGDocument);
  rpc ActivateDocument(ActivateDocumentRequest) returns (RAGDocument);
  rpc ArchiveDocument(ArchiveDocumentRequest) returns (RAGDocument);
  rpc RollbackDocument(RollbackDocumentRequest) returns (RAGDocument);

  // A/B Testing
  rpc StartABTest(StartABTestRequest) returns (ABTestStatus);
  rpc GetABTestStatus(GetABTestStatusRequest) returns (ABTestStatus);
  rpc EndABTest(EndABTestRequest) returns (ABTestResult);
}

message RAGDocument {
  string document_id = 1;
  int32 version = 2;
  string title = 3;
  string domain = 4;
  string content = 5;
  string status = 6;
  RAGDocumentMetadata metadata = 7;
  string change_summary = 8;
  google.protobuf.Timestamp created_at = 9;
  google.protobuf.Timestamp updated_at = 10;
  optional SourceFile source_file = 11;      // If created from PDF/DOCX
}

message RAGDocumentMetadata {
  string author = 1;
  optional string source = 2;
  optional string region = 3;
  optional string season = 4;
  repeated string tags = 5;
}

message SourceFile {
  string filename = 1;
  string file_type = 2;                      // "pdf", "docx", "md", "txt"
  string blob_path = 3;                      // Azure Blob path to original
  int64 file_size_bytes = 4;
  string extraction_method = 5;              // "text_extraction", "azure_doc_intel", "vision_llm"
  float extraction_confidence = 6;           // 0-1 quality score
  int32 page_count = 7;
}

message CreateDocumentRequest {
  string title = 1;
  string domain = 2;
  RAGDocumentMetadata metadata = 3;

  // Content source: provide ONE of these
  oneof content_source {
    string content = 4;                      // Direct markdown content
    bytes pdf_file = 5;                      // PDF binary for extraction
    bytes docx_file = 6;                     // DOCX binary for extraction
  }
}

message CreateDocumentResponse {
  RAGDocument document = 1;
  optional ExtractionResult extraction = 2;  // Present if PDF/DOCX was processed
}

message ExtractionResult {
  string method = 1;                         // "text_extraction", "azure_doc_intel", "vision_llm"
  float confidence = 2;                      // 0-1 quality score
  int32 page_count = 3;
  bool review_recommended = 4;               // True if human review advised
  repeated string warnings = 5;              // Any issues detected
}

message GetDocumentRequest {
  string document_id = 1;
  optional int32 version = 2;            // If omitted, returns latest
}

message UpdateDocumentRequest {
  string document_id = 1;
  string title = 2;
  string content = 3;
  RAGDocumentMetadata metadata = 4;
  string change_summary = 5;             // Required: what changed
}

message DeleteDocumentRequest {
  string document_id = 1;
}

message DeleteDocumentResponse {
  bool success = 1;
}

message ListDocumentsRequest {
  optional string domain = 1;            // Filter by domain
  optional string status = 2;            // Filter by status
  optional string author = 3;            // Filter by author
  int32 page = 4;
  int32 page_size = 5;
}

message ListDocumentsResponse {
  repeated RAGDocument documents = 1;
  int32 total_count = 2;
  int32 page = 3;
  int32 page_size = 4;
}

message SearchDocumentsRequest {
  string query = 1;                      // Full-text search
  optional string domain = 2;
  optional string status = 3;
  int32 limit = 4;
}

message SearchDocumentsResponse {
  repeated RAGDocument documents = 1;
}

message StageDocumentRequest {
  string document_id = 1;
}

message ActivateDocumentRequest {
  string document_id = 1;
}

message ArchiveDocumentRequest {
  string document_id = 1;
}

message RollbackDocumentRequest {
  string document_id = 1;
  int32 to_version = 2;
}

message StartABTestRequest {
  string document_id = 1;
  int32 traffic_percentage = 2;          // % of queries using staged version
  int32 duration_days = 3;
}

message ABTestStatus {
  string test_id = 1;
  string document_id = 2;
  string status = 3;                     // "running", "completed", "cancelled"
  int32 staged_queries = 4;
  int32 active_queries = 5;
  google.protobuf.Timestamp started_at = 6;
  google.protobuf.Timestamp ends_at = 7;
}

message GetABTestStatusRequest {
  string test_id = 1;
}

message EndABTestRequest {
  string test_id = 1;
  bool promote = 2;                      // true = activate staged, false = rollback
}

message ABTestResult {
  string test_id = 1;
  bool promoted = 2;
  string outcome = 3;                    // Summary of results
}
```

## Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAG DOCUMENT MANAGEMENT FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ADMIN UI (Web)                     BFF                    AI MODEL     │
│  ┌─────────────────┐           ┌──────────┐           ┌──────────────┐ │
│  │  Agronomist     │  GraphQL  │          │   gRPC    │              │ │
│  │  uploads PDF    │──────────▶│  BFF     │──────────▶│  RAGDocument │ │
│  │                 │           │  Service │           │  Service     │ │
│  │  • PDF file     │           │          │           │              │ │
│  │  • Title        │           │          │           │  • Extract   │ │
│  │  • Domain       │           │          │           │  • Store     │ │
│  │  • Metadata     │           │          │           │  • Vectorize │ │
│  └─────────────────┘           └──────────┘           └──────────────┘ │
│                                                              │          │
│                                         ┌────────────────────┼──────┐   │
│                                         │                    │      │   │
│                                         ▼                    ▼      │   │
│  CLI (Ops)                       ┌──────────────┐    ┌────────────┐ │   │
│  ┌─────────────────┐             │ Azure Doc    │    │  MongoDB   │ │   │
│  │ farmer-cli rag  │             │ Intelligence │    │ (documents)│ │   │
│  │   create --pdf  │────────────▶│  (OCR/PDF)   │    └────────────┘ │   │
│  │   list          │ Direct gRPC └──────────────┘           │       │   │
│  │   stage         │                                        ▼       │   │
│  │   activate      │                                 ┌────────────┐ │   │
│  └─────────────────┘                                 │  Pinecone  │ │   │
│                                                      │  (vectors) │ │   │
│                      ┌──────────────┐                └────────────┘ │   │
│                      │ Azure Blob   │◄──────────────────────────────┘   │
│                      │ (original    │   Store original PDF              │
│                      │  PDFs)       │                                   │
│                      └──────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## CLI Commands (for Ops)

```bash
# Create document from PDF (auto-extraction)
farmer-cli rag create --title "Blister Blight Treatment" \
  --domain plant_diseases \
  --pdf ./documents/blister-blight-guide.pdf \
  --author "Dr. Wanjiku" \
  --region Kenya

# Output:
# ✓ Uploaded PDF (2.3 MB, 15 pages)
# ✓ Extracted using azure_doc_intel (confidence: 0.96)
# ✓ Document created: doc-789 (status: draft)
# ℹ Review recommended: Found 3 tables, verify formatting

# Create document from markdown file
farmer-cli rag create --title "Frost Protection" \
  --domain weather_patterns \
  --file frost-protection.md \
  --author "Operations"

# Create document with inline content
farmer-cli rag create --title "Quick Tip: Pruning" \
  --domain tea_cultivation \
  --content "When temperatures drop below 4°C..." \
  --author "Operations"

# List documents with filters
farmer-cli rag list --domain plant_diseases --status active
farmer-cli rag list --author "Dr. Wanjiku"

# Get specific document
farmer-cli rag get --id doc-123
farmer-cli rag get --id doc-123 --version 2

# Update document
farmer-cli rag update --id doc-123 \
  --file updated-guide.md \
  --change-summary "Added new treatment protocol for resistant strains"

# Stage for A/B testing
farmer-cli rag stage --id doc-123

# Start A/B test
farmer-cli rag ab-test start --id doc-123 --traffic 20 --duration 7

# Check A/B test status
farmer-cli rag ab-test status --test-id test-456

# Activate (promote to production)
farmer-cli rag activate --id doc-123

# Rollback to previous version
farmer-cli rag rollback --id doc-123 --to-version 2

# Archive document
farmer-cli rag archive --id doc-123

# Bulk import from directory
farmer-cli rag import --dir ./knowledge-base/ --domain tea_cultivation --author "Import"
```

## Vectorization Process

When a document is staged or activated, the AI Model automatically:

1. **Chunk content** - Split into semantic chunks (by heading or paragraph)
2. **Generate embeddings** - Using configured embedding model
3. **Store in Pinecone** - With namespace based on version
4. **Update document record** - Store `pinecone_namespace` and `pinecone_ids`

```python
async def vectorize_document(document: RAGDocument) -> RAGDocument:
    """Vectorize document content and store in Pinecone."""
    # 1. Chunk content
    chunks = chunk_by_heading(document.content)

    # 2. Generate embeddings
    embeddings = await embedding_client.embed(
        texts=[chunk.text for chunk in chunks],
        model="text-embedding-3-small"
    )

    # 3. Store in Pinecone
    namespace = f"knowledge-v{document.version}"
    vectors = [
        {
            "id": f"{document.document_id}-{i}",
            "values": embedding,
            "metadata": {
                "document_id": document.document_id,
                "domain": document.domain,
                "chunk_index": i,
                "title": document.title,
                "region": document.metadata.region,
                "tags": document.metadata.tags,
            }
        }
        for i, embedding in enumerate(embeddings)
    ]
    await pinecone_client.upsert(vectors, namespace=namespace)

    # 4. Update document record
    document.pinecone_namespace = namespace
    document.pinecone_ids = [v["id"] for v in vectors]
    document.content_hash = hashlib.sha256(document.content.encode()).hexdigest()

    return document
```
