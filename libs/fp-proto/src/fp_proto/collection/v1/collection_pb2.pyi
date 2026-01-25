import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EVENT_TYPE_UNSPECIFIED: _ClassVar[EventType]
    EVENT_TYPE_DOCUMENT_STORED: _ClassVar[EventType]
    EVENT_TYPE_POOR_QUALITY_DETECTED: _ClassVar[EventType]
    EVENT_TYPE_WEATHER_UPDATED: _ClassVar[EventType]
    EVENT_TYPE_MARKET_PRICES_UPDATED: _ClassVar[EventType]

class QualityGrade(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    QUALITY_GRADE_UNSPECIFIED: _ClassVar[QualityGrade]
    QUALITY_GRADE_PRIMARY: _ClassVar[QualityGrade]
    QUALITY_GRADE_SECONDARY: _ClassVar[QualityGrade]
EVENT_TYPE_UNSPECIFIED: EventType
EVENT_TYPE_DOCUMENT_STORED: EventType
EVENT_TYPE_POOR_QUALITY_DETECTED: EventType
EVENT_TYPE_WEATHER_UPDATED: EventType
EVENT_TYPE_MARKET_PRICES_UPDATED: EventType
QUALITY_GRADE_UNSPECIFIED: QualityGrade
QUALITY_GRADE_PRIMARY: QualityGrade
QUALITY_GRADE_SECONDARY: QualityGrade

class ListSourceConfigsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "enabled_only", "ingestion_mode")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    ENABLED_ONLY_FIELD_NUMBER: _ClassVar[int]
    INGESTION_MODE_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    enabled_only: bool
    ingestion_mode: str
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., enabled_only: bool = ..., ingestion_mode: _Optional[str] = ...) -> None: ...

class ListSourceConfigsResponse(_message.Message):
    __slots__ = ("configs", "next_page_token", "total_count")
    CONFIGS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    configs: _containers.RepeatedCompositeFieldContainer[SourceConfigSummary]
    next_page_token: str
    total_count: int
    def __init__(self, configs: _Optional[_Iterable[_Union[SourceConfigSummary, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class GetSourceConfigRequest(_message.Message):
    __slots__ = ("source_id",)
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    source_id: str
    def __init__(self, source_id: _Optional[str] = ...) -> None: ...

class SourceConfigSummary(_message.Message):
    __slots__ = ("source_id", "display_name", "description", "enabled", "ingestion_mode", "ai_agent_id", "updated_at")
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    INGESTION_MODE_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    source_id: str
    display_name: str
    description: str
    enabled: bool
    ingestion_mode: str
    ai_agent_id: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, source_id: _Optional[str] = ..., display_name: _Optional[str] = ..., description: _Optional[str] = ..., enabled: bool = ..., ingestion_mode: _Optional[str] = ..., ai_agent_id: _Optional[str] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class SourceConfigResponse(_message.Message):
    __slots__ = ("source_id", "display_name", "description", "enabled", "config_json", "created_at", "updated_at")
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    CONFIG_JSON_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    source_id: str
    display_name: str
    description: str
    enabled: bool
    config_json: str
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, source_id: _Optional[str] = ..., display_name: _Optional[str] = ..., description: _Optional[str] = ..., enabled: bool = ..., config_json: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class RawDocumentRef(_message.Message):
    __slots__ = ("blob_container", "blob_path", "content_hash", "size_bytes", "stored_at")
    BLOB_CONTAINER_FIELD_NUMBER: _ClassVar[int]
    BLOB_PATH_FIELD_NUMBER: _ClassVar[int]
    CONTENT_HASH_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    STORED_AT_FIELD_NUMBER: _ClassVar[int]
    blob_container: str
    blob_path: str
    content_hash: str
    size_bytes: int
    stored_at: _timestamp_pb2.Timestamp
    def __init__(self, blob_container: _Optional[str] = ..., blob_path: _Optional[str] = ..., content_hash: _Optional[str] = ..., size_bytes: _Optional[int] = ..., stored_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ExtractionMetadata(_message.Message):
    __slots__ = ("ai_agent_id", "extraction_timestamp", "confidence", "validation_passed", "validation_warnings")
    AI_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    EXTRACTION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_PASSED_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_WARNINGS_FIELD_NUMBER: _ClassVar[int]
    ai_agent_id: str
    extraction_timestamp: _timestamp_pb2.Timestamp
    confidence: float
    validation_passed: bool
    validation_warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ai_agent_id: _Optional[str] = ..., extraction_timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., confidence: _Optional[float] = ..., validation_passed: bool = ..., validation_warnings: _Optional[_Iterable[str]] = ...) -> None: ...

class IngestionMetadata(_message.Message):
    __slots__ = ("ingestion_id", "source_id", "received_at", "processed_at")
    INGESTION_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_FIELD_NUMBER: _ClassVar[int]
    PROCESSED_AT_FIELD_NUMBER: _ClassVar[int]
    ingestion_id: str
    source_id: str
    received_at: _timestamp_pb2.Timestamp
    processed_at: _timestamp_pb2.Timestamp
    def __init__(self, ingestion_id: _Optional[str] = ..., source_id: _Optional[str] = ..., received_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., processed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Document(_message.Message):
    __slots__ = ("document_id", "raw_document", "extraction", "ingestion", "extracted_fields", "linkage_fields", "created_at")
    class ExtractedFieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class LinkageFieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    RAW_DOCUMENT_FIELD_NUMBER: _ClassVar[int]
    EXTRACTION_FIELD_NUMBER: _ClassVar[int]
    INGESTION_FIELD_NUMBER: _ClassVar[int]
    EXTRACTED_FIELDS_FIELD_NUMBER: _ClassVar[int]
    LINKAGE_FIELDS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    raw_document: RawDocumentRef
    extraction: ExtractionMetadata
    ingestion: IngestionMetadata
    extracted_fields: _containers.ScalarMap[str, str]
    linkage_fields: _containers.ScalarMap[str, str]
    created_at: _timestamp_pb2.Timestamp
    def __init__(self, document_id: _Optional[str] = ..., raw_document: _Optional[_Union[RawDocumentRef, _Mapping]] = ..., extraction: _Optional[_Union[ExtractionMetadata, _Mapping]] = ..., ingestion: _Optional[_Union[IngestionMetadata, _Mapping]] = ..., extracted_fields: _Optional[_Mapping[str, str]] = ..., linkage_fields: _Optional[_Mapping[str, str]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetDocumentRequest(_message.Message):
    __slots__ = ("document_id", "collection_name")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_NAME_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    collection_name: str
    def __init__(self, document_id: _Optional[str] = ..., collection_name: _Optional[str] = ...) -> None: ...

class ListDocumentsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "farmer_id", "collection_name")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_NAME_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    farmer_id: str
    collection_name: str
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., farmer_id: _Optional[str] = ..., collection_name: _Optional[str] = ...) -> None: ...

class ListDocumentsResponse(_message.Message):
    __slots__ = ("documents", "next_page_token", "total_count")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[Document]
    next_page_token: str
    total_count: int
    def __init__(self, documents: _Optional[_Iterable[_Union[Document, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class GetDocumentsByFarmerRequest(_message.Message):
    __slots__ = ("farmer_id", "collection_name", "limit")
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_NAME_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    collection_name: str
    limit: int
    def __init__(self, farmer_id: _Optional[str] = ..., collection_name: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class GetDocumentsByFarmerResponse(_message.Message):
    __slots__ = ("documents", "total_count")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[Document]
    total_count: int
    def __init__(self, documents: _Optional[_Iterable[_Union[Document, _Mapping]]] = ..., total_count: _Optional[int] = ...) -> None: ...

class SearchDocumentsRequest(_message.Message):
    __slots__ = ("collection_name", "source_id", "start_date", "end_date", "linkage_filters", "page_size", "page_token")
    class LinkageFiltersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    COLLECTION_NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    LINKAGE_FILTERS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    collection_name: str
    source_id: str
    start_date: _timestamp_pb2.Timestamp
    end_date: _timestamp_pb2.Timestamp
    linkage_filters: _containers.ScalarMap[str, str]
    page_size: int
    page_token: str
    def __init__(self, collection_name: _Optional[str] = ..., source_id: _Optional[str] = ..., start_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., linkage_filters: _Optional[_Mapping[str, str]] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ...) -> None: ...

class SearchDocumentsResponse(_message.Message):
    __slots__ = ("documents", "next_page_token", "total_count")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[Document]
    next_page_token: str
    total_count: int
    def __init__(self, documents: _Optional[_Iterable[_Union[Document, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class DocumentStoredEvent(_message.Message):
    __slots__ = ("document_id", "source_type", "farmer_id", "blob_path", "blob_etag", "content_hash", "content_type", "content_length", "timestamp")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    BLOB_PATH_FIELD_NUMBER: _ClassVar[int]
    BLOB_ETAG_FIELD_NUMBER: _ClassVar[int]
    CONTENT_HASH_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_LENGTH_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    source_type: str
    farmer_id: str
    blob_path: str
    blob_etag: str
    content_hash: str
    content_type: str
    content_length: int
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, document_id: _Optional[str] = ..., source_type: _Optional[str] = ..., farmer_id: _Optional[str] = ..., blob_path: _Optional[str] = ..., blob_etag: _Optional[str] = ..., content_hash: _Optional[str] = ..., content_type: _Optional[str] = ..., content_length: _Optional[int] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class PoorQualityDetectedEvent(_message.Message):
    __slots__ = ("event_id", "farmer_id", "primary_percentage", "threshold", "leaf_type_distribution", "priority", "timestamp")
    class LeafTypeDistributionEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    LEAF_TYPE_DISTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    farmer_id: str
    primary_percentage: float
    threshold: float
    leaf_type_distribution: _containers.ScalarMap[str, float]
    priority: str
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, event_id: _Optional[str] = ..., farmer_id: _Optional[str] = ..., primary_percentage: _Optional[float] = ..., threshold: _Optional[float] = ..., leaf_type_distribution: _Optional[_Mapping[str, float]] = ..., priority: _Optional[str] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class WeatherUpdatedEvent(_message.Message):
    __slots__ = ("region_id", "weather_date", "temperature_high", "temperature_low", "rainfall_mm", "humidity_percent", "timestamp")
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    WEATHER_DATE_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_HIGH_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_LOW_FIELD_NUMBER: _ClassVar[int]
    RAINFALL_MM_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    weather_date: str
    temperature_high: float
    temperature_low: float
    rainfall_mm: float
    humidity_percent: float
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, region_id: _Optional[str] = ..., weather_date: _Optional[str] = ..., temperature_high: _Optional[float] = ..., temperature_low: _Optional[float] = ..., rainfall_mm: _Optional[float] = ..., humidity_percent: _Optional[float] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class MarketPricesUpdatedEvent(_message.Message):
    __slots__ = ("commodity", "region", "price_per_kg", "currency", "price_date", "timestamp")
    COMMODITY_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    PRICE_PER_KG_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    PRICE_DATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    commodity: str
    region: str
    price_per_kg: float
    currency: str
    price_date: str
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, commodity: _Optional[str] = ..., region: _Optional[str] = ..., price_per_kg: _Optional[float] = ..., currency: _Optional[str] = ..., price_date: _Optional[str] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class EventMetadata(_message.Message):
    __slots__ = ("event_id", "farmer_id", "collection_point_id", "timestamp", "source")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_POINT_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    farmer_id: str
    collection_point_id: str
    timestamp: _timestamp_pb2.Timestamp
    source: str
    def __init__(self, event_id: _Optional[str] = ..., farmer_id: _Optional[str] = ..., collection_point_id: _Optional[str] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., source: _Optional[str] = ...) -> None: ...

class EndBagEvent(_message.Message):
    __slots__ = ("metadata", "weight_kg", "quality_grade", "attributes", "bag_id")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    METADATA_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_KG_FIELD_NUMBER: _ClassVar[int]
    QUALITY_GRADE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    BAG_ID_FIELD_NUMBER: _ClassVar[int]
    metadata: EventMetadata
    weight_kg: float
    quality_grade: QualityGrade
    attributes: _containers.ScalarMap[str, str]
    bag_id: str
    def __init__(self, metadata: _Optional[_Union[EventMetadata, _Mapping]] = ..., weight_kg: _Optional[float] = ..., quality_grade: _Optional[_Union[QualityGrade, str]] = ..., attributes: _Optional[_Mapping[str, str]] = ..., bag_id: _Optional[str] = ...) -> None: ...

class GetQualityEventsRequest(_message.Message):
    __slots__ = ("farmer_id", "start_date", "end_date", "page_size", "page_token")
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    start_date: _timestamp_pb2.Timestamp
    end_date: _timestamp_pb2.Timestamp
    page_size: int
    page_token: str
    def __init__(self, farmer_id: _Optional[str] = ..., start_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ...) -> None: ...

class GetQualityEventsResponse(_message.Message):
    __slots__ = ("events", "next_page_token", "total_count")
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[EndBagEvent]
    next_page_token: str
    total_count: int
    def __init__(self, events: _Optional[_Iterable[_Union[EndBagEvent, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...
