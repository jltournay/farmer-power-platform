import datetime
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor, message as _message, timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers, enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class FarmScale(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FARM_SCALE_UNSPECIFIED: _ClassVar[FarmScale]
    FARM_SCALE_SMALLHOLDER: _ClassVar[FarmScale]
    FARM_SCALE_MEDIUM: _ClassVar[FarmScale]
    FARM_SCALE_ESTATE: _ClassVar[FarmScale]

class NotificationChannel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOTIFICATION_CHANNEL_UNSPECIFIED: _ClassVar[NotificationChannel]
    NOTIFICATION_CHANNEL_SMS: _ClassVar[NotificationChannel]
    NOTIFICATION_CHANNEL_WHATSAPP: _ClassVar[NotificationChannel]

class InteractionPreference(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INTERACTION_PREFERENCE_UNSPECIFIED: _ClassVar[InteractionPreference]
    INTERACTION_PREFERENCE_TEXT: _ClassVar[InteractionPreference]
    INTERACTION_PREFERENCE_VOICE: _ClassVar[InteractionPreference]

class PreferredLanguage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PREFERRED_LANGUAGE_UNSPECIFIED: _ClassVar[PreferredLanguage]
    PREFERRED_LANGUAGE_SW: _ClassVar[PreferredLanguage]
    PREFERRED_LANGUAGE_KI: _ClassVar[PreferredLanguage]
    PREFERRED_LANGUAGE_LUO: _ClassVar[PreferredLanguage]
    PREFERRED_LANGUAGE_EN: _ClassVar[PreferredLanguage]

class GradingType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GRADING_TYPE_UNSPECIFIED: _ClassVar[GradingType]
    GRADING_TYPE_BINARY: _ClassVar[GradingType]
    GRADING_TYPE_TERNARY: _ClassVar[GradingType]
    GRADING_TYPE_MULTI_LEVEL: _ClassVar[GradingType]

class TrendDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TREND_DIRECTION_UNSPECIFIED: _ClassVar[TrendDirection]
    TREND_DIRECTION_IMPROVING: _ClassVar[TrendDirection]
    TREND_DIRECTION_STABLE: _ClassVar[TrendDirection]
    TREND_DIRECTION_DECLINING: _ClassVar[TrendDirection]

FARM_SCALE_UNSPECIFIED: FarmScale
FARM_SCALE_SMALLHOLDER: FarmScale
FARM_SCALE_MEDIUM: FarmScale
FARM_SCALE_ESTATE: FarmScale
NOTIFICATION_CHANNEL_UNSPECIFIED: NotificationChannel
NOTIFICATION_CHANNEL_SMS: NotificationChannel
NOTIFICATION_CHANNEL_WHATSAPP: NotificationChannel
INTERACTION_PREFERENCE_UNSPECIFIED: InteractionPreference
INTERACTION_PREFERENCE_TEXT: InteractionPreference
INTERACTION_PREFERENCE_VOICE: InteractionPreference
PREFERRED_LANGUAGE_UNSPECIFIED: PreferredLanguage
PREFERRED_LANGUAGE_SW: PreferredLanguage
PREFERRED_LANGUAGE_KI: PreferredLanguage
PREFERRED_LANGUAGE_LUO: PreferredLanguage
PREFERRED_LANGUAGE_EN: PreferredLanguage
GRADING_TYPE_UNSPECIFIED: GradingType
GRADING_TYPE_BINARY: GradingType
GRADING_TYPE_TERNARY: GradingType
GRADING_TYPE_MULTI_LEVEL: GradingType
TREND_DIRECTION_UNSPECIFIED: TrendDirection
TREND_DIRECTION_IMPROVING: TrendDirection
TREND_DIRECTION_STABLE: TrendDirection
TREND_DIRECTION_DECLINING: TrendDirection

class GeoLocation(_message.Message):
    __slots__ = ("altitude_meters", "latitude", "longitude")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_METERS_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    altitude_meters: float
    def __init__(
        self, latitude: float | None = ..., longitude: float | None = ..., altitude_meters: float | None = ...
    ) -> None: ...

class ContactInfo(_message.Message):
    __slots__ = ("address", "email", "phone")
    PHONE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    phone: str
    email: str
    address: str
    def __init__(self, phone: str | None = ..., email: str | None = ..., address: str | None = ...) -> None: ...

class Region(_message.Message):
    __slots__ = ("center", "code", "created_at", "id", "is_active", "name", "parent_region_id", "updated_at")
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        code: str | None = ...,
        center: GeoLocation | _Mapping | None = ...,
        parent_region_id: str | None = ...,
        is_active: bool = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetRegionRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class ListRegionsRequest(_message.Message):
    __slots__ = ("active_only", "page_size", "page_token", "parent_region_id")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    PARENT_REGION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    parent_region_id: str
    active_only: bool
    def __init__(
        self,
        page_size: int | None = ...,
        page_token: str | None = ...,
        parent_region_id: str | None = ...,
        active_only: bool = ...,
    ) -> None: ...

class ListRegionsResponse(_message.Message):
    __slots__ = ("next_page_token", "regions", "total_count")
    REGIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    regions: _containers.RepeatedCompositeFieldContainer[Region]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        regions: _Iterable[Region | _Mapping] | None = ...,
        next_page_token: str | None = ...,
        total_count: int | None = ...,
    ) -> None: ...

class CreateRegionRequest(_message.Message):
    __slots__ = ("center", "code", "name", "parent_region_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    CENTER_FIELD_NUMBER: _ClassVar[int]
    PARENT_REGION_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    code: str
    center: GeoLocation
    parent_region_id: str
    def __init__(
        self,
        name: str | None = ...,
        code: str | None = ...,
        center: GeoLocation | _Mapping | None = ...,
        parent_region_id: str | None = ...,
    ) -> None: ...

class UpdateRegionRequest(_message.Message):
    __slots__ = ("center", "code", "id", "is_active", "name")
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        code: str | None = ...,
        center: GeoLocation | _Mapping | None = ...,
        is_active: bool = ...,
    ) -> None: ...

class Factory(_message.Message):
    __slots__ = (
        "code",
        "contact",
        "created_at",
        "id",
        "is_active",
        "location",
        "name",
        "processing_capacity_kg",
        "region_id",
        "updated_at",
    )
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        code: str | None = ...,
        region_id: str | None = ...,
        location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        processing_capacity_kg: int | None = ...,
        is_active: bool = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetFactoryRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class ListFactoriesRequest(_message.Message):
    __slots__ = ("active_only", "page_size", "page_token", "region_id")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    region_id: str
    active_only: bool
    def __init__(
        self,
        page_size: int | None = ...,
        page_token: str | None = ...,
        region_id: str | None = ...,
        active_only: bool = ...,
    ) -> None: ...

class ListFactoriesResponse(_message.Message):
    __slots__ = ("factories", "next_page_token", "total_count")
    FACTORIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    factories: _containers.RepeatedCompositeFieldContainer[Factory]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        factories: _Iterable[Factory | _Mapping] | None = ...,
        next_page_token: str | None = ...,
        total_count: int | None = ...,
    ) -> None: ...

class CreateFactoryRequest(_message.Message):
    __slots__ = ("code", "contact", "location", "name", "processing_capacity_kg", "region_id")
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
    def __init__(
        self,
        name: str | None = ...,
        code: str | None = ...,
        region_id: str | None = ...,
        location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        processing_capacity_kg: int | None = ...,
    ) -> None: ...

class UpdateFactoryRequest(_message.Message):
    __slots__ = ("code", "contact", "id", "is_active", "location", "name", "processing_capacity_kg")
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        code: str | None = ...,
        location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        processing_capacity_kg: int | None = ...,
        is_active: bool = ...,
    ) -> None: ...

class DeleteFactoryRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

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
    def __init__(self, weekdays: str | None = ..., weekends: str | None = ...) -> None: ...

class CollectionPointCapacity(_message.Message):
    __slots__ = ("has_qc_device", "has_weighing_scale", "max_daily_kg", "storage_type")
    MAX_DAILY_KG_FIELD_NUMBER: _ClassVar[int]
    STORAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    HAS_WEIGHING_SCALE_FIELD_NUMBER: _ClassVar[int]
    HAS_QC_DEVICE_FIELD_NUMBER: _ClassVar[int]
    max_daily_kg: int
    storage_type: str
    has_weighing_scale: bool
    has_qc_device: bool
    def __init__(
        self,
        max_daily_kg: int | None = ...,
        storage_type: str | None = ...,
        has_weighing_scale: bool = ...,
        has_qc_device: bool = ...,
    ) -> None: ...

class CollectionPoint(_message.Message):
    __slots__ = (
        "capacity",
        "clerk_id",
        "clerk_phone",
        "collection_days",
        "created_at",
        "factory_id",
        "id",
        "location",
        "name",
        "operating_hours",
        "region_id",
        "status",
        "updated_at",
    )
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        factory_id: str | None = ...,
        location: GeoLocation | _Mapping | None = ...,
        region_id: str | None = ...,
        clerk_id: str | None = ...,
        clerk_phone: str | None = ...,
        operating_hours: OperatingHours | _Mapping | None = ...,
        collection_days: _Iterable[str] | None = ...,
        capacity: CollectionPointCapacity | _Mapping | None = ...,
        status: str | None = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetCollectionPointRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class ListCollectionPointsRequest(_message.Message):
    __slots__ = ("active_only", "factory_id", "page_size", "page_token", "region_id", "status")
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
    def __init__(
        self,
        page_size: int | None = ...,
        page_token: str | None = ...,
        factory_id: str | None = ...,
        region_id: str | None = ...,
        status: str | None = ...,
        active_only: bool = ...,
    ) -> None: ...

class ListCollectionPointsResponse(_message.Message):
    __slots__ = ("collection_points", "next_page_token", "total_count")
    COLLECTION_POINTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    collection_points: _containers.RepeatedCompositeFieldContainer[CollectionPoint]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        collection_points: _Iterable[CollectionPoint | _Mapping] | None = ...,
        next_page_token: str | None = ...,
        total_count: int | None = ...,
    ) -> None: ...

class CreateCollectionPointRequest(_message.Message):
    __slots__ = (
        "capacity",
        "clerk_id",
        "clerk_phone",
        "collection_days",
        "factory_id",
        "location",
        "name",
        "operating_hours",
        "region_id",
        "status",
    )
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
    def __init__(
        self,
        name: str | None = ...,
        factory_id: str | None = ...,
        location: GeoLocation | _Mapping | None = ...,
        region_id: str | None = ...,
        clerk_id: str | None = ...,
        clerk_phone: str | None = ...,
        operating_hours: OperatingHours | _Mapping | None = ...,
        collection_days: _Iterable[str] | None = ...,
        capacity: CollectionPointCapacity | _Mapping | None = ...,
        status: str | None = ...,
    ) -> None: ...

class UpdateCollectionPointRequest(_message.Message):
    __slots__ = ("capacity", "clerk_id", "clerk_phone", "collection_days", "id", "name", "operating_hours", "status")
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
    def __init__(
        self,
        id: str | None = ...,
        name: str | None = ...,
        clerk_id: str | None = ...,
        clerk_phone: str | None = ...,
        operating_hours: OperatingHours | _Mapping | None = ...,
        collection_days: _Iterable[str] | None = ...,
        capacity: CollectionPointCapacity | _Mapping | None = ...,
        status: str | None = ...,
    ) -> None: ...

class DeleteCollectionPointRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class DeleteCollectionPointResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class Farmer(_message.Message):
    __slots__ = (
        "collection_point_id",
        "contact",
        "created_at",
        "farm_location",
        "farm_scale",
        "farm_size_hectares",
        "first_name",
        "grower_number",
        "id",
        "interaction_pref",
        "is_active",
        "last_name",
        "national_id",
        "notification_channel",
        "pref_lang",
        "region_id",
        "registration_date",
        "updated_at",
    )
    ID_FIELD_NUMBER: _ClassVar[int]
    GROWER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_POINT_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    FARM_SCALE_FIELD_NUMBER: _ClassVar[int]
    NATIONAL_ID_FIELD_NUMBER: _ClassVar[int]
    REGISTRATION_DATE_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    INTERACTION_PREF_FIELD_NUMBER: _ClassVar[int]
    PREF_LANG_FIELD_NUMBER: _ClassVar[int]
    id: str
    grower_number: str
    first_name: str
    last_name: str
    region_id: str
    collection_point_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    farm_scale: FarmScale
    national_id: str
    registration_date: _timestamp_pb2.Timestamp
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    notification_channel: NotificationChannel
    interaction_pref: InteractionPreference
    pref_lang: PreferredLanguage
    def __init__(
        self,
        id: str | None = ...,
        grower_number: str | None = ...,
        first_name: str | None = ...,
        last_name: str | None = ...,
        region_id: str | None = ...,
        collection_point_id: str | None = ...,
        farm_location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        farm_size_hectares: float | None = ...,
        farm_scale: FarmScale | str | None = ...,
        national_id: str | None = ...,
        registration_date: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        is_active: bool = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        notification_channel: NotificationChannel | str | None = ...,
        interaction_pref: InteractionPreference | str | None = ...,
        pref_lang: PreferredLanguage | str | None = ...,
    ) -> None: ...

class GetFarmerRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class GetFarmerByPhoneRequest(_message.Message):
    __slots__ = ("phone",)
    PHONE_FIELD_NUMBER: _ClassVar[int]
    phone: str
    def __init__(self, phone: str | None = ...) -> None: ...

class ListFarmersRequest(_message.Message):
    __slots__ = ("active_only", "collection_point_id", "page_size", "page_token", "region_id")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_POINT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    region_id: str
    collection_point_id: str
    active_only: bool
    def __init__(
        self,
        page_size: int | None = ...,
        page_token: str | None = ...,
        region_id: str | None = ...,
        collection_point_id: str | None = ...,
        active_only: bool = ...,
    ) -> None: ...

class ListFarmersResponse(_message.Message):
    __slots__ = ("farmers", "next_page_token", "total_count")
    FARMERS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    farmers: _containers.RepeatedCompositeFieldContainer[Farmer]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        farmers: _Iterable[Farmer | _Mapping] | None = ...,
        next_page_token: str | None = ...,
        total_count: int | None = ...,
    ) -> None: ...

class CreateFarmerRequest(_message.Message):
    __slots__ = (
        "collection_point_id",
        "contact",
        "farm_location",
        "farm_size_hectares",
        "first_name",
        "grower_number",
        "last_name",
        "national_id",
    )
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_POINT_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    NATIONAL_ID_FIELD_NUMBER: _ClassVar[int]
    GROWER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    first_name: str
    last_name: str
    collection_point_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    national_id: str
    grower_number: str
    def __init__(
        self,
        first_name: str | None = ...,
        last_name: str | None = ...,
        collection_point_id: str | None = ...,
        farm_location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        farm_size_hectares: float | None = ...,
        national_id: str | None = ...,
        grower_number: str | None = ...,
    ) -> None: ...

class UpdateFarmerRequest(_message.Message):
    __slots__ = ("contact", "farm_location", "farm_size_hectares", "first_name", "id", "is_active", "last_name")
    ID_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    FARM_LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    first_name: str
    last_name: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    is_active: bool
    def __init__(
        self,
        id: str | None = ...,
        first_name: str | None = ...,
        last_name: str | None = ...,
        farm_location: GeoLocation | _Mapping | None = ...,
        contact: ContactInfo | _Mapping | None = ...,
        farm_size_hectares: float | None = ...,
        is_active: bool = ...,
    ) -> None: ...

class PerformanceSummary(_message.Message):
    __slots__ = (
        "average_quality_score",
        "collection_count",
        "created_at",
        "entity_id",
        "entity_type",
        "id",
        "period",
        "period_end",
        "period_start",
        "total_green_leaf_kg",
        "total_made_tea_kg",
        "updated_at",
    )
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
    def __init__(
        self,
        id: str | None = ...,
        entity_type: str | None = ...,
        entity_id: str | None = ...,
        period: str | None = ...,
        period_start: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        period_end: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        total_green_leaf_kg: float | None = ...,
        total_made_tea_kg: float | None = ...,
        collection_count: int | None = ...,
        average_quality_score: float | None = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetPerformanceSummaryRequest(_message.Message):
    __slots__ = ("entity_id", "entity_type", "period", "period_start")
    ENTITY_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    entity_type: str
    entity_id: str
    period: str
    period_start: _timestamp_pb2.Timestamp
    def __init__(
        self,
        entity_type: str | None = ...,
        entity_id: str | None = ...,
        period: str | None = ...,
        period_start: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GradingAttribute(_message.Message):
    __slots__ = ("classes", "num_classes")
    NUM_CLASSES_FIELD_NUMBER: _ClassVar[int]
    CLASSES_FIELD_NUMBER: _ClassVar[int]
    num_classes: int
    classes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, num_classes: int | None = ..., classes: _Iterable[str] | None = ...) -> None: ...

class ConditionalReject(_message.Message):
    __slots__ = ("if_attribute", "if_value", "reject_values", "then_attribute")
    IF_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    IF_VALUE_FIELD_NUMBER: _ClassVar[int]
    THEN_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    REJECT_VALUES_FIELD_NUMBER: _ClassVar[int]
    if_attribute: str
    if_value: str
    then_attribute: str
    reject_values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        if_attribute: str | None = ...,
        if_value: str | None = ...,
        then_attribute: str | None = ...,
        reject_values: _Iterable[str] | None = ...,
    ) -> None: ...

class GradeRules(_message.Message):
    __slots__ = ("conditional_reject", "reject_conditions")
    class RejectConditionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: StringList
        def __init__(self, key: str | None = ..., value: StringList | _Mapping | None = ...) -> None: ...

    REJECT_CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_REJECT_FIELD_NUMBER: _ClassVar[int]
    reject_conditions: _containers.MessageMap[str, StringList]
    conditional_reject: _containers.RepeatedCompositeFieldContainer[ConditionalReject]
    def __init__(
        self,
        reject_conditions: _Mapping[str, StringList] | None = ...,
        conditional_reject: _Iterable[ConditionalReject | _Mapping] | None = ...,
    ) -> None: ...

class StringList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Iterable[str] | None = ...) -> None: ...

class GradingModel(_message.Message):
    __slots__ = (
        "active_at_factory",
        "attributes",
        "created_at",
        "crops_name",
        "grade_labels",
        "grade_rules",
        "grading_type",
        "market_name",
        "model_id",
        "model_version",
        "regulatory_authority",
        "updated_at",
    )
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: GradingAttribute
        def __init__(self, key: str | None = ..., value: GradingAttribute | _Mapping | None = ...) -> None: ...

    class GradeLabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    REGULATORY_AUTHORITY_FIELD_NUMBER: _ClassVar[int]
    CROPS_NAME_FIELD_NUMBER: _ClassVar[int]
    MARKET_NAME_FIELD_NUMBER: _ClassVar[int]
    GRADING_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    GRADE_RULES_FIELD_NUMBER: _ClassVar[int]
    GRADE_LABELS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_AT_FACTORY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    model_version: str
    regulatory_authority: str
    crops_name: str
    market_name: str
    grading_type: GradingType
    attributes: _containers.MessageMap[str, GradingAttribute]
    grade_rules: GradeRules
    grade_labels: _containers.ScalarMap[str, str]
    active_at_factory: _containers.RepeatedScalarFieldContainer[str]
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        model_id: str | None = ...,
        model_version: str | None = ...,
        regulatory_authority: str | None = ...,
        crops_name: str | None = ...,
        market_name: str | None = ...,
        grading_type: GradingType | str | None = ...,
        attributes: _Mapping[str, GradingAttribute] | None = ...,
        grade_rules: GradeRules | _Mapping | None = ...,
        grade_labels: _Mapping[str, str] | None = ...,
        active_at_factory: _Iterable[str] | None = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class GetGradingModelRequest(_message.Message):
    __slots__ = ("model_id",)
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    def __init__(self, model_id: str | None = ...) -> None: ...

class GetFactoryGradingModelRequest(_message.Message):
    __slots__ = ("factory_id",)
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    factory_id: str
    def __init__(self, factory_id: str | None = ...) -> None: ...

class CreateGradingModelRequest(_message.Message):
    __slots__ = (
        "active_at_factory",
        "attributes",
        "crops_name",
        "grade_labels",
        "grade_rules",
        "grading_type",
        "market_name",
        "model_id",
        "model_version",
        "regulatory_authority",
    )
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: GradingAttribute
        def __init__(self, key: str | None = ..., value: GradingAttribute | _Mapping | None = ...) -> None: ...

    class GradeLabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    REGULATORY_AUTHORITY_FIELD_NUMBER: _ClassVar[int]
    CROPS_NAME_FIELD_NUMBER: _ClassVar[int]
    MARKET_NAME_FIELD_NUMBER: _ClassVar[int]
    GRADING_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    GRADE_RULES_FIELD_NUMBER: _ClassVar[int]
    GRADE_LABELS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_AT_FACTORY_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    model_version: str
    regulatory_authority: str
    crops_name: str
    market_name: str
    grading_type: GradingType
    attributes: _containers.MessageMap[str, GradingAttribute]
    grade_rules: GradeRules
    grade_labels: _containers.ScalarMap[str, str]
    active_at_factory: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        model_id: str | None = ...,
        model_version: str | None = ...,
        regulatory_authority: str | None = ...,
        crops_name: str | None = ...,
        market_name: str | None = ...,
        grading_type: GradingType | str | None = ...,
        attributes: _Mapping[str, GradingAttribute] | None = ...,
        grade_rules: GradeRules | _Mapping | None = ...,
        grade_labels: _Mapping[str, str] | None = ...,
        active_at_factory: _Iterable[str] | None = ...,
    ) -> None: ...

class AssignGradingModelToFactoryRequest(_message.Message):
    __slots__ = ("factory_id", "model_id")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    factory_id: str
    def __init__(self, model_id: str | None = ..., factory_id: str | None = ...) -> None: ...

class DistributionCounts(_message.Message):
    __slots__ = ("counts",)
    class CountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...

    COUNTS_FIELD_NUMBER: _ClassVar[int]
    counts: _containers.ScalarMap[str, int]
    def __init__(self, counts: _Mapping[str, int] | None = ...) -> None: ...

class HistoricalMetrics(_message.Message):
    __slots__ = (
        "attribute_distributions_30d",
        "attribute_distributions_90d",
        "attribute_distributions_year",
        "computed_at",
        "grade_distribution_30d",
        "grade_distribution_90d",
        "grade_distribution_year",
        "improvement_trend",
        "primary_percentage_30d",
        "primary_percentage_90d",
        "primary_percentage_year",
        "total_kg_30d",
        "total_kg_90d",
        "total_kg_year",
        "yield_kg_per_hectare_30d",
        "yield_kg_per_hectare_90d",
        "yield_kg_per_hectare_year",
    )
    class GradeDistribution30dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...

    class GradeDistribution90dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...

    class GradeDistributionYearEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...

    class AttributeDistributions30dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(self, key: str | None = ..., value: DistributionCounts | _Mapping | None = ...) -> None: ...

    class AttributeDistributions90dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(self, key: str | None = ..., value: DistributionCounts | _Mapping | None = ...) -> None: ...

    class AttributeDistributionsYearEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(self, key: str | None = ..., value: DistributionCounts | _Mapping | None = ...) -> None: ...

    GRADE_DISTRIBUTION_30D_FIELD_NUMBER: _ClassVar[int]
    GRADE_DISTRIBUTION_90D_FIELD_NUMBER: _ClassVar[int]
    GRADE_DISTRIBUTION_YEAR_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_DISTRIBUTIONS_30D_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_DISTRIBUTIONS_90D_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_DISTRIBUTIONS_YEAR_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_PERCENTAGE_30D_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_PERCENTAGE_90D_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_PERCENTAGE_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_KG_30D_FIELD_NUMBER: _ClassVar[int]
    TOTAL_KG_90D_FIELD_NUMBER: _ClassVar[int]
    TOTAL_KG_YEAR_FIELD_NUMBER: _ClassVar[int]
    YIELD_KG_PER_HECTARE_30D_FIELD_NUMBER: _ClassVar[int]
    YIELD_KG_PER_HECTARE_90D_FIELD_NUMBER: _ClassVar[int]
    YIELD_KG_PER_HECTARE_YEAR_FIELD_NUMBER: _ClassVar[int]
    IMPROVEMENT_TREND_FIELD_NUMBER: _ClassVar[int]
    COMPUTED_AT_FIELD_NUMBER: _ClassVar[int]
    grade_distribution_30d: _containers.ScalarMap[str, int]
    grade_distribution_90d: _containers.ScalarMap[str, int]
    grade_distribution_year: _containers.ScalarMap[str, int]
    attribute_distributions_30d: _containers.MessageMap[str, DistributionCounts]
    attribute_distributions_90d: _containers.MessageMap[str, DistributionCounts]
    attribute_distributions_year: _containers.MessageMap[str, DistributionCounts]
    primary_percentage_30d: float
    primary_percentage_90d: float
    primary_percentage_year: float
    total_kg_30d: float
    total_kg_90d: float
    total_kg_year: float
    yield_kg_per_hectare_30d: float
    yield_kg_per_hectare_90d: float
    yield_kg_per_hectare_year: float
    improvement_trend: TrendDirection
    computed_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        grade_distribution_30d: _Mapping[str, int] | None = ...,
        grade_distribution_90d: _Mapping[str, int] | None = ...,
        grade_distribution_year: _Mapping[str, int] | None = ...,
        attribute_distributions_30d: _Mapping[str, DistributionCounts] | None = ...,
        attribute_distributions_90d: _Mapping[str, DistributionCounts] | None = ...,
        attribute_distributions_year: _Mapping[str, DistributionCounts] | None = ...,
        primary_percentage_30d: float | None = ...,
        primary_percentage_90d: float | None = ...,
        primary_percentage_year: float | None = ...,
        total_kg_30d: float | None = ...,
        total_kg_90d: float | None = ...,
        total_kg_year: float | None = ...,
        yield_kg_per_hectare_30d: float | None = ...,
        yield_kg_per_hectare_90d: float | None = ...,
        yield_kg_per_hectare_year: float | None = ...,
        improvement_trend: TrendDirection | str | None = ...,
        computed_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class TodayMetrics(_message.Message):
    __slots__ = ("attribute_counts", "deliveries", "grade_counts", "last_delivery", "metrics_date", "total_kg")
    class GradeCountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: str | None = ..., value: int | None = ...) -> None: ...

    class AttributeCountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(self, key: str | None = ..., value: DistributionCounts | _Mapping | None = ...) -> None: ...

    DELIVERIES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_KG_FIELD_NUMBER: _ClassVar[int]
    GRADE_COUNTS_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_COUNTS_FIELD_NUMBER: _ClassVar[int]
    LAST_DELIVERY_FIELD_NUMBER: _ClassVar[int]
    METRICS_DATE_FIELD_NUMBER: _ClassVar[int]
    deliveries: int
    total_kg: float
    grade_counts: _containers.ScalarMap[str, int]
    attribute_counts: _containers.MessageMap[str, DistributionCounts]
    last_delivery: _timestamp_pb2.Timestamp
    metrics_date: str
    def __init__(
        self,
        deliveries: int | None = ...,
        total_kg: float | None = ...,
        grade_counts: _Mapping[str, int] | None = ...,
        attribute_counts: _Mapping[str, DistributionCounts] | None = ...,
        last_delivery: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        metrics_date: str | None = ...,
    ) -> None: ...

class FarmerSummary(_message.Message):
    __slots__ = (
        "collection_point_id",
        "created_at",
        "farm_scale",
        "farm_size_hectares",
        "farmer_id",
        "first_name",
        "grading_model_id",
        "grading_model_version",
        "historical",
        "interaction_pref",
        "last_name",
        "notification_channel",
        "phone",
        "pref_lang",
        "today",
        "trend_direction",
        "updated_at",
    )
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_POINT_ID_FIELD_NUMBER: _ClassVar[int]
    FARM_SIZE_HECTARES_FIELD_NUMBER: _ClassVar[int]
    FARM_SCALE_FIELD_NUMBER: _ClassVar[int]
    GRADING_MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    GRADING_MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    HISTORICAL_FIELD_NUMBER: _ClassVar[int]
    TODAY_FIELD_NUMBER: _ClassVar[int]
    TREND_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    INTERACTION_PREF_FIELD_NUMBER: _ClassVar[int]
    PREF_LANG_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    first_name: str
    last_name: str
    phone: str
    collection_point_id: str
    farm_size_hectares: float
    farm_scale: FarmScale
    grading_model_id: str
    grading_model_version: str
    historical: HistoricalMetrics
    today: TodayMetrics
    trend_direction: TrendDirection
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    notification_channel: NotificationChannel
    interaction_pref: InteractionPreference
    pref_lang: PreferredLanguage
    def __init__(
        self,
        farmer_id: str | None = ...,
        first_name: str | None = ...,
        last_name: str | None = ...,
        phone: str | None = ...,
        collection_point_id: str | None = ...,
        farm_size_hectares: float | None = ...,
        farm_scale: FarmScale | str | None = ...,
        grading_model_id: str | None = ...,
        grading_model_version: str | None = ...,
        historical: HistoricalMetrics | _Mapping | None = ...,
        today: TodayMetrics | _Mapping | None = ...,
        trend_direction: TrendDirection | str | None = ...,
        created_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        updated_at: datetime.datetime | _timestamp_pb2.Timestamp | _Mapping | None = ...,
        notification_channel: NotificationChannel | str | None = ...,
        interaction_pref: InteractionPreference | str | None = ...,
        pref_lang: PreferredLanguage | str | None = ...,
    ) -> None: ...

class GetFarmerSummaryRequest(_message.Message):
    __slots__ = ("farmer_id",)
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    def __init__(self, farmer_id: str | None = ...) -> None: ...

class UpdateCommunicationPreferencesRequest(_message.Message):
    __slots__ = ("farmer_id", "interaction_pref", "notification_channel", "pref_lang")
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    INTERACTION_PREF_FIELD_NUMBER: _ClassVar[int]
    PREF_LANG_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    notification_channel: NotificationChannel
    interaction_pref: InteractionPreference
    pref_lang: PreferredLanguage
    def __init__(
        self,
        farmer_id: str | None = ...,
        notification_channel: NotificationChannel | str | None = ...,
        interaction_pref: InteractionPreference | str | None = ...,
        pref_lang: PreferredLanguage | str | None = ...,
    ) -> None: ...

class UpdateCommunicationPreferencesResponse(_message.Message):
    __slots__ = ("farmer",)
    FARMER_FIELD_NUMBER: _ClassVar[int]
    farmer: Farmer
    def __init__(self, farmer: Farmer | _Mapping | None = ...) -> None: ...
