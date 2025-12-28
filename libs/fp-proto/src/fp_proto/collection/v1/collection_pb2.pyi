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

class DocumentStoredEvent(_message.Message):
    __slots__ = (
        "document_id",
        "source_type",
        "farmer_id",
        "blob_path",
        "blob_etag",
        "content_hash",
        "content_type",
        "content_length",
        "timestamp",
    )
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
    def __init__(
        self,
        document_id: _Optional[str] = ...,
        source_type: _Optional[str] = ...,
        farmer_id: _Optional[str] = ...,
        blob_path: _Optional[str] = ...,
        blob_etag: _Optional[str] = ...,
        content_hash: _Optional[str] = ...,
        content_type: _Optional[str] = ...,
        content_length: _Optional[int] = ...,
        timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class PoorQualityDetectedEvent(_message.Message):
    __slots__ = (
        "event_id",
        "farmer_id",
        "primary_percentage",
        "threshold",
        "leaf_type_distribution",
        "priority",
        "timestamp",
    )
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
    def __init__(
        self,
        event_id: _Optional[str] = ...,
        farmer_id: _Optional[str] = ...,
        primary_percentage: _Optional[float] = ...,
        threshold: _Optional[float] = ...,
        leaf_type_distribution: _Optional[_Mapping[str, float]] = ...,
        priority: _Optional[str] = ...,
        timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class WeatherUpdatedEvent(_message.Message):
    __slots__ = (
        "region_id",
        "weather_date",
        "temperature_high",
        "temperature_low",
        "rainfall_mm",
        "humidity_percent",
        "timestamp",
    )
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
    def __init__(
        self,
        region_id: _Optional[str] = ...,
        weather_date: _Optional[str] = ...,
        temperature_high: _Optional[float] = ...,
        temperature_low: _Optional[float] = ...,
        rainfall_mm: _Optional[float] = ...,
        humidity_percent: _Optional[float] = ...,
        timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        commodity: _Optional[str] = ...,
        region: _Optional[str] = ...,
        price_per_kg: _Optional[float] = ...,
        currency: _Optional[str] = ...,
        price_date: _Optional[str] = ...,
        timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        event_id: _Optional[str] = ...,
        farmer_id: _Optional[str] = ...,
        collection_point_id: _Optional[str] = ...,
        timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        source: _Optional[str] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        metadata: _Optional[_Union[EventMetadata, _Mapping]] = ...,
        weight_kg: _Optional[float] = ...,
        quality_grade: _Optional[_Union[QualityGrade, str]] = ...,
        attributes: _Optional[_Mapping[str, str]] = ...,
        bag_id: _Optional[str] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        farmer_id: _Optional[str] = ...,
        start_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        end_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        page_size: _Optional[int] = ...,
        page_token: _Optional[str] = ...,
    ) -> None: ...

class GetQualityEventsResponse(_message.Message):
    __slots__ = ("events", "next_page_token", "total_count")
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[EndBagEvent]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        events: _Optional[_Iterable[_Union[EndBagEvent, _Mapping]]] = ...,
        next_page_token: _Optional[str] = ...,
        total_count: _Optional[int] = ...,
    ) -> None: ...
