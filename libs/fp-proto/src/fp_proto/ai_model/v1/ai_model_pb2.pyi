import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExtractionRequest(_message.Message):
    __slots__ = ("raw_content", "ai_agent_id", "source_config_json", "content_type", "trace_id")
    RAW_CONTENT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_CONFIG_JSON_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    raw_content: str
    ai_agent_id: str
    source_config_json: str
    content_type: str
    trace_id: str
    def __init__(self, raw_content: _Optional[str] = ..., ai_agent_id: _Optional[str] = ..., source_config_json: _Optional[str] = ..., content_type: _Optional[str] = ..., trace_id: _Optional[str] = ...) -> None: ...

class ExtractionResponse(_message.Message):
    __slots__ = ("success", "extracted_fields_json", "confidence", "validation_passed", "validation_warnings", "error_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    EXTRACTED_FIELDS_JSON_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_PASSED_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_WARNINGS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    extracted_fields_json: str
    confidence: float
    validation_passed: bool
    validation_warnings: _containers.RepeatedScalarFieldContainer[str]
    error_message: str
    def __init__(self, success: bool = ..., extracted_fields_json: _Optional[str] = ..., confidence: _Optional[float] = ..., validation_passed: bool = ..., validation_warnings: _Optional[_Iterable[str]] = ..., error_message: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "version")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    version: str
    def __init__(self, healthy: bool = ..., version: _Optional[str] = ...) -> None: ...

class DateRangeRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: _timestamp_pb2.Timestamp
    end_date: _timestamp_pb2.Timestamp
    def __init__(self, start_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CostSummaryResponse(_message.Message):
    __slots__ = ("total_cost_usd", "total_requests", "total_tokens_in", "total_tokens_out")
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    total_cost_usd: str
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    def __init__(self, total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens_in: _Optional[int] = ..., total_tokens_out: _Optional[int] = ...) -> None: ...

class DailyCost(_message.Message):
    __slots__ = ("date", "total_cost_usd", "total_requests", "total_tokens_in", "total_tokens_out", "success_count", "failure_count")
    DATE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_COUNT_FIELD_NUMBER: _ClassVar[int]
    FAILURE_COUNT_FIELD_NUMBER: _ClassVar[int]
    date: _timestamp_pb2.Timestamp
    total_cost_usd: str
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    success_count: int
    failure_count: int
    def __init__(self, date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens_in: _Optional[int] = ..., total_tokens_out: _Optional[int] = ..., success_count: _Optional[int] = ..., failure_count: _Optional[int] = ...) -> None: ...

class DailyCostSummaryResponse(_message.Message):
    __slots__ = ("daily_costs",)
    DAILY_COSTS_FIELD_NUMBER: _ClassVar[int]
    daily_costs: _containers.RepeatedCompositeFieldContainer[DailyCost]
    def __init__(self, daily_costs: _Optional[_Iterable[_Union[DailyCost, _Mapping]]] = ...) -> None: ...

class AgentTypeCostEntry(_message.Message):
    __slots__ = ("agent_type", "total_cost_usd", "total_requests", "total_tokens")
    AGENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    agent_type: str
    total_cost_usd: str
    total_requests: int
    total_tokens: int
    def __init__(self, agent_type: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens: _Optional[int] = ...) -> None: ...

class CostByAgentTypeResponse(_message.Message):
    __slots__ = ("agent_type_costs",)
    AGENT_TYPE_COSTS_FIELD_NUMBER: _ClassVar[int]
    agent_type_costs: _containers.RepeatedCompositeFieldContainer[AgentTypeCostEntry]
    def __init__(self, agent_type_costs: _Optional[_Iterable[_Union[AgentTypeCostEntry, _Mapping]]] = ...) -> None: ...

class ModelCostEntry(_message.Message):
    __slots__ = ("model", "total_cost_usd", "total_requests", "total_tokens")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    model: str
    total_cost_usd: str
    total_requests: int
    total_tokens: int
    def __init__(self, model: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens: _Optional[int] = ...) -> None: ...

class CostByModelResponse(_message.Message):
    __slots__ = ("model_costs",)
    MODEL_COSTS_FIELD_NUMBER: _ClassVar[int]
    model_costs: _containers.RepeatedCompositeFieldContainer[ModelCostEntry]
    def __init__(self, model_costs: _Optional[_Iterable[_Union[ModelCostEntry, _Mapping]]] = ...) -> None: ...

class CostAlert(_message.Message):
    __slots__ = ("threshold_type", "threshold_usd", "current_cost_usd", "triggered_at", "event_id")
    THRESHOLD_TYPE_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    CURRENT_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TRIGGERED_AT_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    threshold_type: str
    threshold_usd: str
    current_cost_usd: str
    triggered_at: _timestamp_pb2.Timestamp
    event_id: str
    def __init__(self, threshold_type: _Optional[str] = ..., threshold_usd: _Optional[str] = ..., current_cost_usd: _Optional[str] = ..., triggered_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., event_id: _Optional[str] = ...) -> None: ...

class CostAlertsResponse(_message.Message):
    __slots__ = ("alerts", "daily_threshold_usd", "daily_total_usd", "daily_alert_triggered", "monthly_threshold_usd", "monthly_total_usd", "monthly_alert_triggered")
    ALERTS_FIELD_NUMBER: _ClassVar[int]
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    alerts: _containers.RepeatedCompositeFieldContainer[CostAlert]
    daily_threshold_usd: str
    daily_total_usd: str
    daily_alert_triggered: bool
    monthly_threshold_usd: str
    monthly_total_usd: str
    monthly_alert_triggered: bool
    def __init__(self, alerts: _Optional[_Iterable[_Union[CostAlert, _Mapping]]] = ..., daily_threshold_usd: _Optional[str] = ..., daily_total_usd: _Optional[str] = ..., daily_alert_triggered: bool = ..., monthly_threshold_usd: _Optional[str] = ..., monthly_total_usd: _Optional[str] = ..., monthly_alert_triggered: bool = ...) -> None: ...

class ThresholdConfigRequest(_message.Message):
    __slots__ = ("daily_threshold_usd", "monthly_threshold_usd")
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    daily_threshold_usd: float
    monthly_threshold_usd: float
    def __init__(self, daily_threshold_usd: _Optional[float] = ..., monthly_threshold_usd: _Optional[float] = ...) -> None: ...

class RAGDocument(_message.Message):
    __slots__ = ("id", "document_id", "version", "title", "domain", "content", "status", "metadata", "source_file", "change_summary", "created_at", "updated_at", "pinecone_namespace", "pinecone_ids", "content_hash")
    ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FILE_FIELD_NUMBER: _ClassVar[int]
    CHANGE_SUMMARY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    PINECONE_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    PINECONE_IDS_FIELD_NUMBER: _ClassVar[int]
    CONTENT_HASH_FIELD_NUMBER: _ClassVar[int]
    id: str
    document_id: str
    version: int
    title: str
    domain: str
    content: str
    status: str
    metadata: RAGDocumentMetadata
    source_file: SourceFile
    change_summary: str
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    pinecone_namespace: str
    pinecone_ids: _containers.RepeatedScalarFieldContainer[str]
    content_hash: str
    def __init__(self, id: _Optional[str] = ..., document_id: _Optional[str] = ..., version: _Optional[int] = ..., title: _Optional[str] = ..., domain: _Optional[str] = ..., content: _Optional[str] = ..., status: _Optional[str] = ..., metadata: _Optional[_Union[RAGDocumentMetadata, _Mapping]] = ..., source_file: _Optional[_Union[SourceFile, _Mapping]] = ..., change_summary: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., pinecone_namespace: _Optional[str] = ..., pinecone_ids: _Optional[_Iterable[str]] = ..., content_hash: _Optional[str] = ...) -> None: ...

class RAGDocumentMetadata(_message.Message):
    __slots__ = ("author", "source", "region", "season", "tags")
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    SEASON_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    author: str
    source: str
    region: str
    season: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, author: _Optional[str] = ..., source: _Optional[str] = ..., region: _Optional[str] = ..., season: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class SourceFile(_message.Message):
    __slots__ = ("filename", "file_type", "blob_path", "file_size_bytes", "extraction_method", "extraction_confidence", "page_count")
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    FILE_TYPE_FIELD_NUMBER: _ClassVar[int]
    BLOB_PATH_FIELD_NUMBER: _ClassVar[int]
    FILE_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    EXTRACTION_METHOD_FIELD_NUMBER: _ClassVar[int]
    EXTRACTION_CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_COUNT_FIELD_NUMBER: _ClassVar[int]
    filename: str
    file_type: str
    blob_path: str
    file_size_bytes: int
    extraction_method: str
    extraction_confidence: float
    page_count: int
    def __init__(self, filename: _Optional[str] = ..., file_type: _Optional[str] = ..., blob_path: _Optional[str] = ..., file_size_bytes: _Optional[int] = ..., extraction_method: _Optional[str] = ..., extraction_confidence: _Optional[float] = ..., page_count: _Optional[int] = ...) -> None: ...

class CreateDocumentRequest(_message.Message):
    __slots__ = ("document_id", "title", "domain", "content", "metadata", "source_file")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FILE_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    domain: str
    content: str
    metadata: RAGDocumentMetadata
    source_file: SourceFile
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., domain: _Optional[str] = ..., content: _Optional[str] = ..., metadata: _Optional[_Union[RAGDocumentMetadata, _Mapping]] = ..., source_file: _Optional[_Union[SourceFile, _Mapping]] = ...) -> None: ...

class CreateDocumentResponse(_message.Message):
    __slots__ = ("document",)
    DOCUMENT_FIELD_NUMBER: _ClassVar[int]
    document: RAGDocument
    def __init__(self, document: _Optional[_Union[RAGDocument, _Mapping]] = ...) -> None: ...

class GetDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class UpdateDocumentRequest(_message.Message):
    __slots__ = ("document_id", "title", "content", "metadata", "change_summary")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CHANGE_SUMMARY_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    content: str
    metadata: RAGDocumentMetadata
    change_summary: str
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., metadata: _Optional[_Union[RAGDocumentMetadata, _Mapping]] = ..., change_summary: _Optional[str] = ...) -> None: ...

class DeleteDocumentRequest(_message.Message):
    __slots__ = ("document_id",)
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    def __init__(self, document_id: _Optional[str] = ...) -> None: ...

class DeleteDocumentResponse(_message.Message):
    __slots__ = ("versions_archived",)
    VERSIONS_ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    versions_archived: int
    def __init__(self, versions_archived: _Optional[int] = ...) -> None: ...

class ListDocumentsRequest(_message.Message):
    __slots__ = ("page", "page_size", "domain", "status", "author")
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    page: int
    page_size: int
    domain: str
    status: str
    author: str
    def __init__(self, page: _Optional[int] = ..., page_size: _Optional[int] = ..., domain: _Optional[str] = ..., status: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class ListDocumentsResponse(_message.Message):
    __slots__ = ("documents", "total_count", "page", "page_size")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[RAGDocument]
    total_count: int
    page: int
    page_size: int
    def __init__(self, documents: _Optional[_Iterable[_Union[RAGDocument, _Mapping]]] = ..., total_count: _Optional[int] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...

class SearchDocumentsRequest(_message.Message):
    __slots__ = ("query", "domain", "status", "limit")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    query: str
    domain: str
    status: str
    limit: int
    def __init__(self, query: _Optional[str] = ..., domain: _Optional[str] = ..., status: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class SearchDocumentsResponse(_message.Message):
    __slots__ = ("documents",)
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[RAGDocument]
    def __init__(self, documents: _Optional[_Iterable[_Union[RAGDocument, _Mapping]]] = ...) -> None: ...

class StageDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class ActivateDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class ArchiveDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class RollbackDocumentRequest(_message.Message):
    __slots__ = ("document_id", "target_version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    target_version: int
    def __init__(self, document_id: _Optional[str] = ..., target_version: _Optional[int] = ...) -> None: ...

class ExtractDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class ExtractDocumentResponse(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetExtractionJobRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class ExtractionJobResponse(_message.Message):
    __slots__ = ("job_id", "document_id", "status", "progress_percent", "pages_processed", "total_pages", "error_message", "started_at", "completed_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    PAGES_PROCESSED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PAGES_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    document_id: str
    status: str
    progress_percent: int
    pages_processed: int
    total_pages: int
    error_message: str
    started_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    def __init__(self, job_id: _Optional[str] = ..., document_id: _Optional[str] = ..., status: _Optional[str] = ..., progress_percent: _Optional[int] = ..., pages_processed: _Optional[int] = ..., total_pages: _Optional[int] = ..., error_message: _Optional[str] = ..., started_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class StreamExtractionProgressRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class ExtractionProgressEvent(_message.Message):
    __slots__ = ("job_id", "status", "progress_percent", "pages_processed", "total_pages", "error_message")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    PAGES_PROCESSED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PAGES_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    progress_percent: int
    pages_processed: int
    total_pages: int
    error_message: str
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., progress_percent: _Optional[int] = ..., pages_processed: _Optional[int] = ..., total_pages: _Optional[int] = ..., error_message: _Optional[str] = ...) -> None: ...

class RagChunk(_message.Message):
    __slots__ = ("chunk_id", "document_id", "document_version", "chunk_index", "content", "section_title", "word_count", "char_count", "created_at", "pinecone_id")
    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    CHUNK_INDEX_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SECTION_TITLE_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    CHAR_COUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    PINECONE_ID_FIELD_NUMBER: _ClassVar[int]
    chunk_id: str
    document_id: str
    document_version: int
    chunk_index: int
    content: str
    section_title: str
    word_count: int
    char_count: int
    created_at: _timestamp_pb2.Timestamp
    pinecone_id: str
    def __init__(self, chunk_id: _Optional[str] = ..., document_id: _Optional[str] = ..., document_version: _Optional[int] = ..., chunk_index: _Optional[int] = ..., content: _Optional[str] = ..., section_title: _Optional[str] = ..., word_count: _Optional[int] = ..., char_count: _Optional[int] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., pinecone_id: _Optional[str] = ...) -> None: ...

class ChunkDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class ChunkDocumentResponse(_message.Message):
    __slots__ = ("chunks_created", "total_char_count", "total_word_count")
    CHUNKS_CREATED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_CHAR_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    chunks_created: int
    total_char_count: int
    total_word_count: int
    def __init__(self, chunks_created: _Optional[int] = ..., total_char_count: _Optional[int] = ..., total_word_count: _Optional[int] = ...) -> None: ...

class ListChunksRequest(_message.Message):
    __slots__ = ("document_id", "version", "page", "page_size")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    page: int
    page_size: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...

class ListChunksResponse(_message.Message):
    __slots__ = ("chunks", "total_count", "page", "page_size")
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    chunks: _containers.RepeatedCompositeFieldContainer[RagChunk]
    total_count: int
    page: int
    page_size: int
    def __init__(self, chunks: _Optional[_Iterable[_Union[RagChunk, _Mapping]]] = ..., total_count: _Optional[int] = ..., page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...

class GetChunkRequest(_message.Message):
    __slots__ = ("chunk_id",)
    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    chunk_id: str
    def __init__(self, chunk_id: _Optional[str] = ...) -> None: ...

class DeleteChunksRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class DeleteChunksResponse(_message.Message):
    __slots__ = ("chunks_deleted",)
    CHUNKS_DELETED_FIELD_NUMBER: _ClassVar[int]
    chunks_deleted: int
    def __init__(self, chunks_deleted: _Optional[int] = ...) -> None: ...

class VectorizeDocumentRequest(_message.Message):
    __slots__ = ("document_id", "version")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ASYNC_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    version: int
    def __init__(self, document_id: _Optional[str] = ..., version: _Optional[int] = ..., **kwargs) -> None: ...

class VectorizeDocumentResponse(_message.Message):
    __slots__ = ("job_id", "status", "namespace", "chunks_total", "chunks_embedded", "chunks_stored", "failed_count", "content_hash", "error_message")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_EMBEDDED_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_STORED_FIELD_NUMBER: _ClassVar[int]
    FAILED_COUNT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_HASH_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    namespace: str
    chunks_total: int
    chunks_embedded: int
    chunks_stored: int
    failed_count: int
    content_hash: str
    error_message: str
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., namespace: _Optional[str] = ..., chunks_total: _Optional[int] = ..., chunks_embedded: _Optional[int] = ..., chunks_stored: _Optional[int] = ..., failed_count: _Optional[int] = ..., content_hash: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class GetVectorizationJobRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class VectorizationJobResponse(_message.Message):
    __slots__ = ("job_id", "status", "document_id", "document_version", "namespace", "chunks_total", "chunks_embedded", "chunks_stored", "failed_count", "content_hash", "error_message", "started_at", "completed_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_EMBEDDED_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_STORED_FIELD_NUMBER: _ClassVar[int]
    FAILED_COUNT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_HASH_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: str
    document_id: str
    document_version: int
    namespace: str
    chunks_total: int
    chunks_embedded: int
    chunks_stored: int
    failed_count: int
    content_hash: str
    error_message: str
    started_at: _timestamp_pb2.Timestamp
    completed_at: _timestamp_pb2.Timestamp
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[str] = ..., document_id: _Optional[str] = ..., document_version: _Optional[int] = ..., namespace: _Optional[str] = ..., chunks_total: _Optional[int] = ..., chunks_embedded: _Optional[int] = ..., chunks_stored: _Optional[int] = ..., failed_count: _Optional[int] = ..., content_hash: _Optional[str] = ..., error_message: _Optional[str] = ..., started_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., completed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
