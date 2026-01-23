"""Knowledge Management transformer for admin API (Story 9.9a).

Transforms proto RAGDocument messages to admin API schemas.
Note: Receives proto objects from AiModelClient (NOT Pydantic models).
"""

from datetime import UTC, datetime

from bff.api.schemas.admin.knowledge_schemas import (
    ChunkSummary,
    DocumentDetail,
    DocumentMetadataResponse,
    DocumentSummary,
    ExtractionJobStatus,
    QueryResultItem,
    SourceFileResponse,
    VectorizationJobStatus,
)
from fp_proto.ai_model.v1 import ai_model_pb2
from google.protobuf.timestamp_pb2 import Timestamp


def _timestamp_to_datetime(ts: Timestamp | None) -> datetime | None:
    """Convert protobuf Timestamp to Python datetime."""
    if ts is None or ts.seconds == 0:
        return None
    return ts.ToDatetime().replace(tzinfo=UTC)


class KnowledgeTransformer:
    """Transforms proto RAGDocument messages to admin API schemas."""

    @staticmethod
    def to_summary(doc: ai_model_pb2.RAGDocument) -> DocumentSummary:
        """Transform RAGDocument proto to summary schema for list views."""
        author = ""
        if doc.HasField("metadata"):
            author = doc.metadata.author
        return DocumentSummary(
            document_id=doc.document_id,
            version=doc.version,
            title=doc.title,
            domain=doc.domain,
            status=doc.status,
            author=author,
            created_at=_timestamp_to_datetime(doc.created_at),
            updated_at=_timestamp_to_datetime(doc.updated_at),
        )

    @staticmethod
    def to_detail(doc: ai_model_pb2.RAGDocument) -> DocumentDetail:
        """Transform RAGDocument proto to detail schema."""
        metadata_resp = DocumentMetadataResponse()
        if doc.HasField("metadata"):
            metadata_resp = DocumentMetadataResponse(
                author=doc.metadata.author,
                source=doc.metadata.source,
                region=doc.metadata.region,
                season=doc.metadata.season,
                tags=list(doc.metadata.tags),
            )

        source_file_resp = None
        if doc.HasField("source_file") and doc.source_file.filename:
            source_file_resp = SourceFileResponse(
                filename=doc.source_file.filename,
                file_type=doc.source_file.file_type,
                file_size_bytes=doc.source_file.file_size_bytes,
                extraction_method=doc.source_file.extraction_method,
                extraction_confidence=doc.source_file.extraction_confidence,
                page_count=doc.source_file.page_count,
            )

        return DocumentDetail(
            id=doc.id,
            document_id=doc.document_id,
            version=doc.version,
            title=doc.title,
            domain=doc.domain,
            content=doc.content,
            status=doc.status,
            metadata=metadata_resp,
            source_file=source_file_resp,
            change_summary=doc.change_summary,
            pinecone_namespace=doc.pinecone_namespace,
            content_hash=doc.content_hash,
            created_at=_timestamp_to_datetime(doc.created_at),
            updated_at=_timestamp_to_datetime(doc.updated_at),
        )

    @staticmethod
    def to_extraction_status(job: ai_model_pb2.ExtractionJobResponse) -> ExtractionJobStatus:
        """Transform ExtractionJobResponse proto to status schema."""
        return ExtractionJobStatus(
            job_id=job.job_id,
            document_id=job.document_id,
            status=job.status,
            progress_percent=job.progress_percent,
            pages_processed=job.pages_processed,
            total_pages=job.total_pages,
            error_message=job.error_message,
            started_at=_timestamp_to_datetime(job.started_at),
            completed_at=_timestamp_to_datetime(job.completed_at),
        )

    @staticmethod
    def to_vectorization_status(job: ai_model_pb2.VectorizationJobResponse) -> VectorizationJobStatus:
        """Transform VectorizationJobResponse proto to status schema."""
        return VectorizationJobStatus(
            job_id=job.job_id,
            status=job.status,
            document_id=job.document_id,
            document_version=job.document_version,
            namespace=job.namespace,
            chunks_total=job.chunks_total,
            chunks_embedded=job.chunks_embedded,
            chunks_stored=job.chunks_stored,
            failed_count=job.failed_count,
            content_hash=job.content_hash,
            error_message=job.error_message,
            started_at=_timestamp_to_datetime(job.started_at),
            completed_at=_timestamp_to_datetime(job.completed_at),
        )

    @staticmethod
    def to_chunk_summary(chunk: ai_model_pb2.RagChunk) -> ChunkSummary:
        """Transform RagChunk proto to chunk summary schema."""
        return ChunkSummary(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_version=chunk.document_version,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            section_title=chunk.section_title,
            word_count=chunk.word_count,
            char_count=chunk.char_count,
            pinecone_id=chunk.pinecone_id,
            created_at=_timestamp_to_datetime(chunk.created_at),
        )

    @staticmethod
    def to_query_result(match: ai_model_pb2.RetrievalMatch) -> QueryResultItem:
        """Transform RetrievalMatch proto to query result schema."""
        return QueryResultItem(
            chunk_id=match.chunk_id,
            content=match.content,
            score=match.score,
            document_id=match.document_id,
            title=match.title,
            domain=match.domain,
        )
