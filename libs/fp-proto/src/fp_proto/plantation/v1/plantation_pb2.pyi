import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GeoLocation(_message.Message):
    __slots__ = ("latitude", "longitude", "altitude_meters")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_METERS_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    altitude_meters: float
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., altitude_meters: _Optional[float] = ...) -> None: ...

class ContactInfo(_message.Message):
    __slots__ = ("phone", "email", "address")
    PHONE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    phone: str
    email: str
    address: str
    def __init__(self, phone: _Optional[str] = ..., email: _Optional[str] = ..., address: _Optional[str] = ...) -> None: ...

class Region(_message.Message):
    __slots__ = ("id", "name", "code", "center", "parent_region_id", "is_active", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    CENTER_FIELD_NUMBER: _ClassVar[int]
    PARENT_REGION_ID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    center: GeoLocation
    parent_region_id: str
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., center: _Optional[_Union[GeoLocation, _Mapping]] = ..., parent_region_id: _Optional[str] = ..., is_active: bool = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetRegionRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ListRegionsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "parent_region_id", "active_only")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    PARENT_REGION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    parent_region_id: str
    active_only: bool
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., parent_region_id: _Optional[str] = ..., active_only: bool = ...) -> None: ...

class ListRegionsResponse(_message.Message):
    __slots__ = ("regions", "next_page_token", "total_count")
    REGIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    regions: _containers.RepeatedCompositeFieldContainer[Region]
    next_page_token: str
    total_count: int
    def __init__(self, regions: _Optional[_Iterable[_Union[Region, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class CreateRegionRequest(_message.Message):
    __slots__ = ("name", "code", "center", "parent_region_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    CENTER_FIELD_NUMBER: _ClassVar[int]
    PARENT_REGION_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    code: str
    center: GeoLocation
    parent_region_id: str
    def __init__(self, name: _Optional[str] = ..., code: _Optional[str] = ..., center: _Optional[_Union[GeoLocation, _Mapping]] = ..., parent_region_id: _Optional[str] = ...) -> None: ...

class UpdateRegionRequest(_message.Message):
    __slots__ = ("id", "name", "code", "center", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    CENTER_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    center: GeoLocation
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., center: _Optional[_Union[GeoLocation, _Mapping]] = ..., is_active: bool = ...) -> None: ...

class Factory(_message.Message):
    __slots__ = ("id", "name", "code", "region_id", "location", "contact", "processing_capacity_kg", "is_active", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    region_id: str
    location: GeoLocation
    contact: ContactInfo
    processing_capacity_kg: int
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., region_id: _Optional[str] = ..., location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., processing_capacity_kg: _Optional[int] = ..., is_active: bool = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetFactoryRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ListFactoriesRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "region_id", "active_only")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    region_id: str
    active_only: bool
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., region_id: _Optional[str] = ..., active_only: bool = ...) -> None: ...

class ListFactoriesResponse(_message.Message):
    __slots__ = ("factories", "next_page_token", "total_count")
    FACTORIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    factories: _containers.RepeatedCompositeFieldContainer[Factory]
    next_page_token: str
    total_count: int
    def __init__(self, factories: _Optional[_Iterable[_Union[Factory, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class CreateFactoryRequest(_message.Message):
    __slots__ = ("name", "code", "region_id", "location", "contact", "processing_capacity_kg")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    name: str
    code: str
    region_id: str
    location: GeoLocation
    contact: ContactInfo
    processing_capacity_kg: int
    def __init__(self, name: _Optional[str] = ..., code: _Optional[str] = ..., region_id: _Optional[str] = ..., location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., processing_capacity_kg: _Optional[int] = ...) -> None: ...

class UpdateFactoryRequest(_message.Message):
    __slots__ = ("id", "name", "code", "location", "contact", "processing_capacity_kg", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    location: GeoLocation
    contact: ContactInfo
    processing_capacity_kg: int
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., processing_capacity_kg: _Optional[int] = ..., is_active: bool = ...) -> None: ...

class DeleteFactoryRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DeleteFactoryResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class OperatingHours(_message.Message):
    __slots__ = ("weekdays", "weekends")
    WEEKDAYS_FIELD_NUMBER: _ClassVar[int]
    WEEKENDS_FIELD_NUMBER: _ClassVar[int]
    weekdays: str
    weekends: str
    def __init__(self, weekdays: _Optional[str] = ..., weekends: _Optional[str] = ...) -> None: ...

class CollectionPointCapacity(_message.Message):
    __slots__ = ("max_daily_kg", "storage_type", "has_weighing_scale", "has_qc_device")
    MAX_DAILY_KG_FIELD_NUMBER: _ClassVar[int]
    STORAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    HAS_WEIGHING_SCALE_FIELD_NUMBER: _ClassVar[int]
    HAS_QC_DEVICE_FIELD_NUMBER: _ClassVar[int]
    max_daily_kg: int
    storage_type: str
    has_weighing_scale: bool
    has_qc_device: bool
    def __init__(self, max_daily_kg: _Optional[int] = ..., storage_type: _Optional[str] = ..., has_weighing_scale: bool = ..., has_qc_device: bool = ...) -> None: ...

class CollectionPoint(_message.Message):
    __slots__ = ("id", "name", "factory_id", "location", "region_id", "clerk_id", "clerk_phone", "operating_hours", "collection_days", "capacity", "status", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    CLERK_ID_FIELD_NUMBER: _ClassVar[int]
    CLERK_PHONE_FIELD_NUMBER: _ClassVar[int]
    OPERATING_HOURS_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_DAYS_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    factory_id: str
    location: GeoLocation
    region_id: str
    clerk_id: str
    clerk_phone: str
    operating_hours: OperatingHours
    collection_days: _containers.RepeatedScalarFieldContainer[str]
    capacity: CollectionPointCapacity
    status: str
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., factory_id: _Optional[str] = ..., location: _Optional[_Union[GeoLocation, _Mapping]] = ..., region_id: _Optional[str] = ..., clerk_id: _Optional[str] = ..., clerk_phone: _Optional[str] = ..., operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ..., collection_days: _Optional[_Iterable[str]] = ..., capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ..., status: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetCollectionPointRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ListCollectionPointsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "factory_id", "region_id", "status", "active_only")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    factory_id: str
    region_id: str
    status: str
    active_only: bool
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., factory_id: _Optional[str] = ..., region_id: _Optional[str] = ..., status: _Optional[str] = ..., active_only: bool = ...) -> None: ...

class ListCollectionPointsResponse(_message.Message):
    __slots__ = ("collection_points", "next_page_token", "total_count")
    COLLECTION_POINTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    collection_points: _containers.RepeatedCompositeFieldContainer[CollectionPoint]
    next_page_token: str
    total_count: int
    def __init__(self, collection_points: _Optional[_Iterable[_Union[CollectionPoint, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class CreateCollectionPointRequest(_message.Message):
    __slots__ = ("name", "factory_id", "location", "region_id", "clerk_id", "clerk_phone", "operating_hours", "collection_days", "capacity", "status")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    CLERK_ID_FIELD_NUMBER: _ClassVar[int]
    CLERK_PHONE_FIELD_NUMBER: _ClassVar[int]
    OPERATING_HOURS_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_DAYS_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    name: str
    factory_id: str
    location: GeoLocation
    region_id: str
    clerk_id: str
    clerk_phone: str
    operating_hours: OperatingHours
    collection_days: _containers.RepeatedScalarFieldContainer[str]
    capacity: CollectionPointCapacity
    status: str
    def __init__(self, name: _Optional[str] = ..., factory_id: _Optional[str] = ..., location: _Optional[_Union[GeoLocation, _Mapping]] = ..., region_id: _Optional[str] = ..., clerk_id: _Optional[str] = ..., clerk_phone: _Optional[str] = ..., operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ..., collection_days: _Optional[_Iterable[str]] = ..., capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ..., status: _Optional[str] = ...) -> None: ...

class UpdateCollectionPointRequest(_message.Message):
    __slots__ = ("id", "name", "clerk_id", "clerk_phone", "operating_hours", "collection_days", "capacity", "status")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CLERK_ID_FIELD_NUMBER: _ClassVar[int]
    CLERK_PHONE_FIELD_NUMBER: _ClassVar[int]
    OPERATING_HOURS_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_DAYS_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    clerk_id: str
    clerk_phone: str
    operating_hours: OperatingHours
    collection_days: _containers.RepeatedScalarFieldContainer[str]
    capacity: CollectionPointCapacity
    status: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., clerk_id: _Optional[str] = ..., clerk_phone: _Optional[str] = ..., operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ..., collection_days: _Optional[_Iterable[str]] = ..., capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ..., status: _Optional[str] = ...) -> None: ...

class DeleteCollectionPointRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DeleteCollectionPointResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class Farmer(_message.Message):
    __slots__ = ("id", "grower_number", "first_name", "last_name", "region_id", "factory_id", "farm_location", "contact", "farm_size_hectares", "registration_date", "is_active", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    GROWER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    REGISTRATION_DATE_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    grower_number: str
    first_name: str
    last_name: str
    region_id: str
    factory_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    registration_date: _timestamp_pb2.Timestamp
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., grower_number: _Optional[str] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., region_id: _Optional[str] = ..., factory_id: _Optional[str] = ..., farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., farm_size_hectares: _Optional[float] = ..., registration_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., is_active: bool = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetFarmerRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ListFarmersRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "region_id", "factory_id", "active_only")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    region_id: str
    factory_id: str
    active_only: bool
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., region_id: _Optional[str] = ..., factory_id: _Optional[str] = ..., active_only: bool = ...) -> None: ...

class ListFarmersResponse(_message.Message):
    __slots__ = ("farmers", "next_page_token", "total_count")
    FARMERS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    farmers: _containers.RepeatedCompositeFieldContainer[Farmer]
    next_page_token: str
    total_count: int
    def __init__(self, farmers: _Optional[_Iterable[_Union[Farmer, _Mapping]]] = ..., next_page_token: _Optional[str] = ..., total_count: _Optional[int] = ...) -> None: ...

class CreateFarmerRequest(_message.Message):
    __slots__ = ("grower_number", "first_name", "last_name", "region_id", "factory_id", "farm_location", "contact", "farm_size_hectares")
    GROWER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    grower_number: str
    first_name: str
    last_name: str
    region_id: str
    factory_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    def __init__(self, grower_number: _Optional[str] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., region_id: _Optional[str] = ..., factory_id: _Optional[str] = ..., farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., farm_size_hectares: _Optional[float] = ...) -> None: ...

class UpdateFarmerRequest(_message.Message):
    __slots__ = ("id", "first_name", "last_name", "factory_id", "farm_location", "contact", "farm_size_hectares", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    first_name: str
    last_name: str
    factory_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., factory_id: _Optional[str] = ..., farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ..., contact: _Optional[_Union[ContactInfo, _Mapping]] = ..., farm_size_hectares: _Optional[float] = ..., is_active: bool = ...) -> None: ...

class PerformanceSummary(_message.Message):
    __slots__ = ("id", "entity_type", "entity_id", "period", "period_start", "period_end", "total_green_leaf_kg", "total_made_tea_kg", "collection_count", "average_quality_score", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ENTITY_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    TOTAL_GREEN_LEAF_KG_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MADE_TEA_KG_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_COUNT_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_QUALITY_SCORE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    entity_type: str
    entity_id: str
    period: str
    period_start: _timestamp_pb2.Timestamp
    period_end: _timestamp_pb2.Timestamp
    total_green_leaf_kg: float
    total_made_tea_kg: float
    collection_count: int
    average_quality_score: float
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., entity_type: _Optional[str] = ..., entity_id: _Optional[str] = ..., period: _Optional[str] = ..., period_start: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., period_end: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., total_green_leaf_kg: _Optional[float] = ..., total_made_tea_kg: _Optional[float] = ..., collection_count: _Optional[int] = ..., average_quality_score: _Optional[float] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetPerformanceSummaryRequest(_message.Message):
    __slots__ = ("entity_type", "entity_id", "period", "period_start")
    ENTITY_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    entity_type: str
    entity_id: str
    period: str
    period_start: _timestamp_pb2.Timestamp
    def __init__(self, entity_type: _Optional[str] = ..., entity_id: _Optional[str] = ..., period: _Optional[str] = ..., period_start: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
