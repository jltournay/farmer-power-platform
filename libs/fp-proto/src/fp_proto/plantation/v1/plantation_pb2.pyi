import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AltitudeBandLabel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ALTITUDE_BAND_UNSPECIFIED: _ClassVar[AltitudeBandLabel]
    ALTITUDE_BAND_HIGHLAND: _ClassVar[AltitudeBandLabel]
    ALTITUDE_BAND_MIDLAND: _ClassVar[AltitudeBandLabel]
    ALTITUDE_BAND_LOWLAND: _ClassVar[AltitudeBandLabel]

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

ALTITUDE_BAND_UNSPECIFIED: AltitudeBandLabel
ALTITUDE_BAND_HIGHLAND: AltitudeBandLabel
ALTITUDE_BAND_MIDLAND: AltitudeBandLabel
ALTITUDE_BAND_LOWLAND: AltitudeBandLabel
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
    __slots__ = ("latitude", "longitude", "altitude_meters")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_METERS_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    altitude_meters: float
    def __init__(
        self,
        latitude: _Optional[float] = ...,
        longitude: _Optional[float] = ...,
        altitude_meters: _Optional[float] = ...,
    ) -> None: ...

class ContactInfo(_message.Message):
    __slots__ = ("phone", "email", "address")
    PHONE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    phone: str
    email: str
    address: str
    def __init__(
        self, phone: _Optional[str] = ..., email: _Optional[str] = ..., address: _Optional[str] = ...
    ) -> None: ...

class QualityThresholds(_message.Message):
    __slots__ = ("tier_1", "tier_2", "tier_3")
    TIER_1_FIELD_NUMBER: _ClassVar[int]
    TIER_2_FIELD_NUMBER: _ClassVar[int]
    TIER_3_FIELD_NUMBER: _ClassVar[int]
    tier_1: float
    tier_2: float
    tier_3: float
    def __init__(
        self, tier_1: _Optional[float] = ..., tier_2: _Optional[float] = ..., tier_3: _Optional[float] = ...
    ) -> None: ...

class GPS(_message.Message):
    __slots__ = ("lat", "lng")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LNG_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lng: float
    def __init__(self, lat: _Optional[float] = ..., lng: _Optional[float] = ...) -> None: ...

class AltitudeBand(_message.Message):
    __slots__ = ("min_meters", "max_meters", "label")
    MIN_METERS_FIELD_NUMBER: _ClassVar[int]
    MAX_METERS_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    min_meters: int
    max_meters: int
    label: AltitudeBandLabel
    def __init__(
        self,
        min_meters: _Optional[int] = ...,
        max_meters: _Optional[int] = ...,
        label: _Optional[_Union[AltitudeBandLabel, str]] = ...,
    ) -> None: ...

class Geography(_message.Message):
    __slots__ = ("center_gps", "radius_km", "altitude_band")
    CENTER_GPS_FIELD_NUMBER: _ClassVar[int]
    RADIUS_KM_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_BAND_FIELD_NUMBER: _ClassVar[int]
    center_gps: GPS
    radius_km: float
    altitude_band: AltitudeBand
    def __init__(
        self,
        center_gps: _Optional[_Union[GPS, _Mapping]] = ...,
        radius_km: _Optional[float] = ...,
        altitude_band: _Optional[_Union[AltitudeBand, _Mapping]] = ...,
    ) -> None: ...

class FlushPeriod(_message.Message):
    __slots__ = ("start", "end", "characteristics")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICS_FIELD_NUMBER: _ClassVar[int]
    start: str
    end: str
    characteristics: str
    def __init__(
        self, start: _Optional[str] = ..., end: _Optional[str] = ..., characteristics: _Optional[str] = ...
    ) -> None: ...

class FlushCalendar(_message.Message):
    __slots__ = ("first_flush", "monsoon_flush", "autumn_flush", "dormant")
    FIRST_FLUSH_FIELD_NUMBER: _ClassVar[int]
    MONSOON_FLUSH_FIELD_NUMBER: _ClassVar[int]
    AUTUMN_FLUSH_FIELD_NUMBER: _ClassVar[int]
    DORMANT_FIELD_NUMBER: _ClassVar[int]
    first_flush: FlushPeriod
    monsoon_flush: FlushPeriod
    autumn_flush: FlushPeriod
    dormant: FlushPeriod
    def __init__(
        self,
        first_flush: _Optional[_Union[FlushPeriod, _Mapping]] = ...,
        monsoon_flush: _Optional[_Union[FlushPeriod, _Mapping]] = ...,
        autumn_flush: _Optional[_Union[FlushPeriod, _Mapping]] = ...,
        dormant: _Optional[_Union[FlushPeriod, _Mapping]] = ...,
    ) -> None: ...

class WeatherConfig(_message.Message):
    __slots__ = ("api_location", "altitude_for_api", "collection_time")
    API_LOCATION_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_FOR_API_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_TIME_FIELD_NUMBER: _ClassVar[int]
    api_location: GPS
    altitude_for_api: int
    collection_time: str
    def __init__(
        self,
        api_location: _Optional[_Union[GPS, _Mapping]] = ...,
        altitude_for_api: _Optional[int] = ...,
        collection_time: _Optional[str] = ...,
    ) -> None: ...

class Agronomic(_message.Message):
    __slots__ = ("soil_type", "typical_diseases", "harvest_peak_hours", "frost_risk")
    SOIL_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPICAL_DISEASES_FIELD_NUMBER: _ClassVar[int]
    HARVEST_PEAK_HOURS_FIELD_NUMBER: _ClassVar[int]
    FROST_RISK_FIELD_NUMBER: _ClassVar[int]
    soil_type: str
    typical_diseases: _containers.RepeatedScalarFieldContainer[str]
    harvest_peak_hours: str
    frost_risk: bool
    def __init__(
        self,
        soil_type: _Optional[str] = ...,
        typical_diseases: _Optional[_Iterable[str]] = ...,
        harvest_peak_hours: _Optional[str] = ...,
        frost_risk: bool = ...,
    ) -> None: ...

class Region(_message.Message):
    __slots__ = (
        "region_id",
        "name",
        "county",
        "country",
        "geography",
        "flush_calendar",
        "agronomic",
        "weather_config",
        "is_active",
        "created_at",
        "updated_at",
    )
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNTY_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    GEOGRAPHY_FIELD_NUMBER: _ClassVar[int]
    FLUSH_CALENDAR_FIELD_NUMBER: _ClassVar[int]
    AGRONOMIC_FIELD_NUMBER: _ClassVar[int]
    WEATHER_CONFIG_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    name: str
    county: str
    country: str
    geography: Geography
    flush_calendar: FlushCalendar
    agronomic: Agronomic
    weather_config: WeatherConfig
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        region_id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        county: _Optional[str] = ...,
        country: _Optional[str] = ...,
        geography: _Optional[_Union[Geography, _Mapping]] = ...,
        flush_calendar: _Optional[_Union[FlushCalendar, _Mapping]] = ...,
        agronomic: _Optional[_Union[Agronomic, _Mapping]] = ...,
        weather_config: _Optional[_Union[WeatherConfig, _Mapping]] = ...,
        is_active: bool = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class GetRegionRequest(_message.Message):
    __slots__ = ("region_id",)
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    def __init__(self, region_id: _Optional[str] = ...) -> None: ...

class ListRegionsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "county", "altitude_band", "active_only")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    COUNTY_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_BAND_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    county: str
    altitude_band: str
    active_only: bool
    def __init__(
        self,
        page_size: _Optional[int] = ...,
        page_token: _Optional[str] = ...,
        county: _Optional[str] = ...,
        altitude_band: _Optional[str] = ...,
        active_only: bool = ...,
    ) -> None: ...

class ListRegionsResponse(_message.Message):
    __slots__ = ("regions", "next_page_token", "total_count")
    REGIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    regions: _containers.RepeatedCompositeFieldContainer[Region]
    next_page_token: str
    total_count: int
    def __init__(
        self,
        regions: _Optional[_Iterable[_Union[Region, _Mapping]]] = ...,
        next_page_token: _Optional[str] = ...,
        total_count: _Optional[int] = ...,
    ) -> None: ...

class CreateRegionRequest(_message.Message):
    __slots__ = ("name", "county", "country", "geography", "flush_calendar", "agronomic", "weather_config")
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNTY_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    GEOGRAPHY_FIELD_NUMBER: _ClassVar[int]
    FLUSH_CALENDAR_FIELD_NUMBER: _ClassVar[int]
    AGRONOMIC_FIELD_NUMBER: _ClassVar[int]
    WEATHER_CONFIG_FIELD_NUMBER: _ClassVar[int]
    name: str
    county: str
    country: str
    geography: Geography
    flush_calendar: FlushCalendar
    agronomic: Agronomic
    weather_config: WeatherConfig
    def __init__(
        self,
        name: _Optional[str] = ...,
        county: _Optional[str] = ...,
        country: _Optional[str] = ...,
        geography: _Optional[_Union[Geography, _Mapping]] = ...,
        flush_calendar: _Optional[_Union[FlushCalendar, _Mapping]] = ...,
        agronomic: _Optional[_Union[Agronomic, _Mapping]] = ...,
        weather_config: _Optional[_Union[WeatherConfig, _Mapping]] = ...,
    ) -> None: ...

class UpdateRegionRequest(_message.Message):
    __slots__ = ("region_id", "name", "geography", "flush_calendar", "agronomic", "weather_config", "is_active")
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    GEOGRAPHY_FIELD_NUMBER: _ClassVar[int]
    FLUSH_CALENDAR_FIELD_NUMBER: _ClassVar[int]
    AGRONOMIC_FIELD_NUMBER: _ClassVar[int]
    WEATHER_CONFIG_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    name: str
    geography: Geography
    flush_calendar: FlushCalendar
    agronomic: Agronomic
    weather_config: WeatherConfig
    is_active: bool
    def __init__(
        self,
        region_id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        geography: _Optional[_Union[Geography, _Mapping]] = ...,
        flush_calendar: _Optional[_Union[FlushCalendar, _Mapping]] = ...,
        agronomic: _Optional[_Union[Agronomic, _Mapping]] = ...,
        weather_config: _Optional[_Union[WeatherConfig, _Mapping]] = ...,
        is_active: bool = ...,
    ) -> None: ...

class WeatherObservation(_message.Message):
    __slots__ = ("temp_min", "temp_max", "precipitation_mm", "humidity_avg")
    TEMP_MIN_FIELD_NUMBER: _ClassVar[int]
    TEMP_MAX_FIELD_NUMBER: _ClassVar[int]
    PRECIPITATION_MM_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_AVG_FIELD_NUMBER: _ClassVar[int]
    temp_min: float
    temp_max: float
    precipitation_mm: float
    humidity_avg: float
    def __init__(
        self,
        temp_min: _Optional[float] = ...,
        temp_max: _Optional[float] = ...,
        precipitation_mm: _Optional[float] = ...,
        humidity_avg: _Optional[float] = ...,
    ) -> None: ...

class RegionalWeather(_message.Message):
    __slots__ = (
        "region_id",
        "date",
        "temp_min",
        "temp_max",
        "precipitation_mm",
        "humidity_avg",
        "source",
        "created_at",
    )
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    TEMP_MIN_FIELD_NUMBER: _ClassVar[int]
    TEMP_MAX_FIELD_NUMBER: _ClassVar[int]
    PRECIPITATION_MM_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_AVG_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    date: str
    temp_min: float
    temp_max: float
    precipitation_mm: float
    humidity_avg: float
    source: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        region_id: _Optional[str] = ...,
        date: _Optional[str] = ...,
        temp_min: _Optional[float] = ...,
        temp_max: _Optional[float] = ...,
        precipitation_mm: _Optional[float] = ...,
        humidity_avg: _Optional[float] = ...,
        source: _Optional[str] = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class GetRegionWeatherRequest(_message.Message):
    __slots__ = ("region_id", "days")
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    days: int
    def __init__(self, region_id: _Optional[str] = ..., days: _Optional[int] = ...) -> None: ...

class GetRegionWeatherResponse(_message.Message):
    __slots__ = ("region_id", "observations")
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    OBSERVATIONS_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    observations: _containers.RepeatedCompositeFieldContainer[RegionalWeather]
    def __init__(
        self,
        region_id: _Optional[str] = ...,
        observations: _Optional[_Iterable[_Union[RegionalWeather, _Mapping]]] = ...,
    ) -> None: ...

class CurrentFlush(_message.Message):
    __slots__ = ("flush_name", "start_date", "end_date", "characteristics", "days_remaining")
    FLUSH_NAME_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICS_FIELD_NUMBER: _ClassVar[int]
    DAYS_REMAINING_FIELD_NUMBER: _ClassVar[int]
    flush_name: str
    start_date: str
    end_date: str
    characteristics: str
    days_remaining: int
    def __init__(
        self,
        flush_name: _Optional[str] = ...,
        start_date: _Optional[str] = ...,
        end_date: _Optional[str] = ...,
        characteristics: _Optional[str] = ...,
        days_remaining: _Optional[int] = ...,
    ) -> None: ...

class GetCurrentFlushRequest(_message.Message):
    __slots__ = ("region_id",)
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    def __init__(self, region_id: _Optional[str] = ...) -> None: ...

class GetCurrentFlushResponse(_message.Message):
    __slots__ = ("region_id", "current_flush")
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FLUSH_FIELD_NUMBER: _ClassVar[int]
    region_id: str
    current_flush: CurrentFlush
    def __init__(
        self, region_id: _Optional[str] = ..., current_flush: _Optional[_Union[CurrentFlush, _Mapping]] = ...
    ) -> None: ...

class Factory(_message.Message):
    __slots__ = (
        "id",
        "name",
        "code",
        "region_id",
        "location",
        "contact",
        "processing_capacity_kg",
        "quality_thresholds",
        "is_active",
        "created_at",
        "updated_at",
    )
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    QUALITY_THRESHOLDS_FIELD_NUMBER: _ClassVar[int]
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
    quality_thresholds: QualityThresholds
    is_active: bool
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        code: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
        location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        processing_capacity_kg: _Optional[int] = ...,
        quality_thresholds: _Optional[_Union[QualityThresholds, _Mapping]] = ...,
        is_active: bool = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        page_size: _Optional[int] = ...,
        page_token: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
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
        factories: _Optional[_Iterable[_Union[Factory, _Mapping]]] = ...,
        next_page_token: _Optional[str] = ...,
        total_count: _Optional[int] = ...,
    ) -> None: ...

class CreateFactoryRequest(_message.Message):
    __slots__ = ("name", "code", "region_id", "location", "contact", "processing_capacity_kg", "quality_thresholds")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    REGION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    QUALITY_THRESHOLDS_FIELD_NUMBER: _ClassVar[int]
    name: str
    code: str
    region_id: str
    location: GeoLocation
    contact: ContactInfo
    processing_capacity_kg: int
    quality_thresholds: QualityThresholds
    def __init__(
        self,
        name: _Optional[str] = ...,
        code: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
        location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        processing_capacity_kg: _Optional[int] = ...,
        quality_thresholds: _Optional[_Union[QualityThresholds, _Mapping]] = ...,
    ) -> None: ...

class UpdateFactoryRequest(_message.Message):
    __slots__ = (
        "id",
        "name",
        "code",
        "location",
        "contact",
        "processing_capacity_kg",
        "quality_thresholds",
        "is_active",
    )
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    QUALITY_THRESHOLDS_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    location: GeoLocation
    contact: ContactInfo
    processing_capacity_kg: int
    quality_thresholds: QualityThresholds
    is_active: bool
    def __init__(
        self,
        id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        code: _Optional[str] = ...,
        location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        processing_capacity_kg: _Optional[int] = ...,
        quality_thresholds: _Optional[_Union[QualityThresholds, _Mapping]] = ...,
        is_active: bool = ...,
    ) -> None: ...

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
    def __init__(
        self,
        max_daily_kg: _Optional[int] = ...,
        storage_type: _Optional[str] = ...,
        has_weighing_scale: bool = ...,
        has_qc_device: bool = ...,
    ) -> None: ...

class CollectionPoint(_message.Message):
    __slots__ = (
        "id",
        "name",
        "factory_id",
        "location",
        "region_id",
        "clerk_id",
        "clerk_phone",
        "operating_hours",
        "collection_days",
        "capacity",
        "status",
        "created_at",
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
        id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        factory_id: _Optional[str] = ...,
        location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        region_id: _Optional[str] = ...,
        clerk_id: _Optional[str] = ...,
        clerk_phone: _Optional[str] = ...,
        operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ...,
        collection_days: _Optional[_Iterable[str]] = ...,
        capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ...,
        status: _Optional[str] = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        page_size: _Optional[int] = ...,
        page_token: _Optional[str] = ...,
        factory_id: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
        status: _Optional[str] = ...,
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
        collection_points: _Optional[_Iterable[_Union[CollectionPoint, _Mapping]]] = ...,
        next_page_token: _Optional[str] = ...,
        total_count: _Optional[int] = ...,
    ) -> None: ...

class CreateCollectionPointRequest(_message.Message):
    __slots__ = (
        "name",
        "factory_id",
        "location",
        "region_id",
        "clerk_id",
        "clerk_phone",
        "operating_hours",
        "collection_days",
        "capacity",
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
        name: _Optional[str] = ...,
        factory_id: _Optional[str] = ...,
        location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        region_id: _Optional[str] = ...,
        clerk_id: _Optional[str] = ...,
        clerk_phone: _Optional[str] = ...,
        operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ...,
        collection_days: _Optional[_Iterable[str]] = ...,
        capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ...,
        status: _Optional[str] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        clerk_id: _Optional[str] = ...,
        clerk_phone: _Optional[str] = ...,
        operating_hours: _Optional[_Union[OperatingHours, _Mapping]] = ...,
        collection_days: _Optional[_Iterable[str]] = ...,
        capacity: _Optional[_Union[CollectionPointCapacity, _Mapping]] = ...,
        status: _Optional[str] = ...,
    ) -> None: ...

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
    __slots__ = (
        "id",
        "grower_number",
        "first_name",
        "last_name",
        "region_id",
        "collection_point_id",
        "farm_location",
        "contact",
        "farm_size_hectares",
        "farm_scale",
        "national_id",
        "registration_date",
        "is_active",
        "created_at",
        "updated_at",
        "notification_channel",
        "interaction_pref",
        "pref_lang",
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
        id: _Optional[str] = ...,
        grower_number: _Optional[str] = ...,
        first_name: _Optional[str] = ...,
        last_name: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
        collection_point_id: _Optional[str] = ...,
        farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        farm_size_hectares: _Optional[float] = ...,
        farm_scale: _Optional[_Union[FarmScale, str]] = ...,
        national_id: _Optional[str] = ...,
        registration_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        is_active: bool = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        notification_channel: _Optional[_Union[NotificationChannel, str]] = ...,
        interaction_pref: _Optional[_Union[InteractionPreference, str]] = ...,
        pref_lang: _Optional[_Union[PreferredLanguage, str]] = ...,
    ) -> None: ...

class GetFarmerRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class GetFarmerByPhoneRequest(_message.Message):
    __slots__ = ("phone",)
    PHONE_FIELD_NUMBER: _ClassVar[int]
    phone: str
    def __init__(self, phone: _Optional[str] = ...) -> None: ...

class ListFarmersRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "region_id", "collection_point_id", "active_only")
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
        page_size: _Optional[int] = ...,
        page_token: _Optional[str] = ...,
        region_id: _Optional[str] = ...,
        collection_point_id: _Optional[str] = ...,
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
        farmers: _Optional[_Iterable[_Union[Farmer, _Mapping]]] = ...,
        next_page_token: _Optional[str] = ...,
        total_count: _Optional[int] = ...,
    ) -> None: ...

class CreateFarmerRequest(_message.Message):
    __slots__ = (
        "first_name",
        "last_name",
        "collection_point_id",
        "farm_location",
        "contact",
        "farm_size_hectares",
        "national_id",
        "grower_number",
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
        first_name: _Optional[str] = ...,
        last_name: _Optional[str] = ...,
        collection_point_id: _Optional[str] = ...,
        farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        farm_size_hectares: _Optional[float] = ...,
        national_id: _Optional[str] = ...,
        grower_number: _Optional[str] = ...,
    ) -> None: ...

class UpdateFarmerRequest(_message.Message):
    __slots__ = ("id", "first_name", "last_name", "farm_location", "contact", "farm_size_hectares", "is_active")
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
        id: _Optional[str] = ...,
        first_name: _Optional[str] = ...,
        last_name: _Optional[str] = ...,
        farm_location: _Optional[_Union[GeoLocation, _Mapping]] = ...,
        contact: _Optional[_Union[ContactInfo, _Mapping]] = ...,
        farm_size_hectares: _Optional[float] = ...,
        is_active: bool = ...,
    ) -> None: ...

class PerformanceSummary(_message.Message):
    __slots__ = (
        "id",
        "entity_type",
        "entity_id",
        "period",
        "period_start",
        "period_end",
        "total_green_leaf_kg",
        "total_made_tea_kg",
        "collection_count",
        "average_quality_score",
        "created_at",
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
        id: _Optional[str] = ...,
        entity_type: _Optional[str] = ...,
        entity_id: _Optional[str] = ...,
        period: _Optional[str] = ...,
        period_start: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        period_end: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        total_green_leaf_kg: _Optional[float] = ...,
        total_made_tea_kg: _Optional[float] = ...,
        collection_count: _Optional[int] = ...,
        average_quality_score: _Optional[float] = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

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
    def __init__(
        self,
        entity_type: _Optional[str] = ...,
        entity_id: _Optional[str] = ...,
        period: _Optional[str] = ...,
        period_start: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class GradingAttribute(_message.Message):
    __slots__ = ("num_classes", "classes")
    NUM_CLASSES_FIELD_NUMBER: _ClassVar[int]
    CLASSES_FIELD_NUMBER: _ClassVar[int]
    num_classes: int
    classes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, num_classes: _Optional[int] = ..., classes: _Optional[_Iterable[str]] = ...) -> None: ...

class ConditionalReject(_message.Message):
    __slots__ = ("if_attribute", "if_value", "then_attribute", "reject_values")
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
        if_attribute: _Optional[str] = ...,
        if_value: _Optional[str] = ...,
        then_attribute: _Optional[str] = ...,
        reject_values: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class GradeRules(_message.Message):
    __slots__ = ("reject_conditions", "conditional_reject")
    class RejectConditionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: StringList
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[StringList, _Mapping]] = ...) -> None: ...

    REJECT_CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_REJECT_FIELD_NUMBER: _ClassVar[int]
    reject_conditions: _containers.MessageMap[str, StringList]
    conditional_reject: _containers.RepeatedCompositeFieldContainer[ConditionalReject]
    def __init__(
        self,
        reject_conditions: _Optional[_Mapping[str, StringList]] = ...,
        conditional_reject: _Optional[_Iterable[_Union[ConditionalReject, _Mapping]]] = ...,
    ) -> None: ...

class StringList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class GradingModel(_message.Message):
    __slots__ = (
        "model_id",
        "model_version",
        "regulatory_authority",
        "crops_name",
        "market_name",
        "grading_type",
        "attributes",
        "grade_rules",
        "grade_labels",
        "active_at_factory",
        "created_at",
        "updated_at",
    )
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: GradingAttribute
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[GradingAttribute, _Mapping]] = ...
        ) -> None: ...

    class GradeLabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

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
        model_id: _Optional[str] = ...,
        model_version: _Optional[str] = ...,
        regulatory_authority: _Optional[str] = ...,
        crops_name: _Optional[str] = ...,
        market_name: _Optional[str] = ...,
        grading_type: _Optional[_Union[GradingType, str]] = ...,
        attributes: _Optional[_Mapping[str, GradingAttribute]] = ...,
        grade_rules: _Optional[_Union[GradeRules, _Mapping]] = ...,
        grade_labels: _Optional[_Mapping[str, str]] = ...,
        active_at_factory: _Optional[_Iterable[str]] = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class GetGradingModelRequest(_message.Message):
    __slots__ = ("model_id",)
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    def __init__(self, model_id: _Optional[str] = ...) -> None: ...

class GetFactoryGradingModelRequest(_message.Message):
    __slots__ = ("factory_id",)
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    factory_id: str
    def __init__(self, factory_id: _Optional[str] = ...) -> None: ...

class CreateGradingModelRequest(_message.Message):
    __slots__ = (
        "model_id",
        "model_version",
        "regulatory_authority",
        "crops_name",
        "market_name",
        "grading_type",
        "attributes",
        "grade_rules",
        "grade_labels",
        "active_at_factory",
    )
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: GradingAttribute
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[GradingAttribute, _Mapping]] = ...
        ) -> None: ...

    class GradeLabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

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
        model_id: _Optional[str] = ...,
        model_version: _Optional[str] = ...,
        regulatory_authority: _Optional[str] = ...,
        crops_name: _Optional[str] = ...,
        market_name: _Optional[str] = ...,
        grading_type: _Optional[_Union[GradingType, str]] = ...,
        attributes: _Optional[_Mapping[str, GradingAttribute]] = ...,
        grade_rules: _Optional[_Union[GradeRules, _Mapping]] = ...,
        grade_labels: _Optional[_Mapping[str, str]] = ...,
        active_at_factory: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class AssignGradingModelToFactoryRequest(_message.Message):
    __slots__ = ("model_id", "factory_id")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    factory_id: str
    def __init__(self, model_id: _Optional[str] = ..., factory_id: _Optional[str] = ...) -> None: ...

class DistributionCounts(_message.Message):
    __slots__ = ("counts",)
    class CountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    COUNTS_FIELD_NUMBER: _ClassVar[int]
    counts: _containers.ScalarMap[str, int]
    def __init__(self, counts: _Optional[_Mapping[str, int]] = ...) -> None: ...

class HistoricalMetrics(_message.Message):
    __slots__ = (
        "grade_distribution_30d",
        "grade_distribution_90d",
        "grade_distribution_year",
        "attribute_distributions_30d",
        "attribute_distributions_90d",
        "attribute_distributions_year",
        "primary_percentage_30d",
        "primary_percentage_90d",
        "primary_percentage_year",
        "total_kg_30d",
        "total_kg_90d",
        "total_kg_year",
        "yield_kg_per_hectare_30d",
        "yield_kg_per_hectare_90d",
        "yield_kg_per_hectare_year",
        "improvement_trend",
        "computed_at",
    )
    class GradeDistribution30dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    class GradeDistribution90dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    class GradeDistributionYearEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    class AttributeDistributions30dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[DistributionCounts, _Mapping]] = ...
        ) -> None: ...

    class AttributeDistributions90dEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[DistributionCounts, _Mapping]] = ...
        ) -> None: ...

    class AttributeDistributionsYearEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[DistributionCounts, _Mapping]] = ...
        ) -> None: ...

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
        grade_distribution_30d: _Optional[_Mapping[str, int]] = ...,
        grade_distribution_90d: _Optional[_Mapping[str, int]] = ...,
        grade_distribution_year: _Optional[_Mapping[str, int]] = ...,
        attribute_distributions_30d: _Optional[_Mapping[str, DistributionCounts]] = ...,
        attribute_distributions_90d: _Optional[_Mapping[str, DistributionCounts]] = ...,
        attribute_distributions_year: _Optional[_Mapping[str, DistributionCounts]] = ...,
        primary_percentage_30d: _Optional[float] = ...,
        primary_percentage_90d: _Optional[float] = ...,
        primary_percentage_year: _Optional[float] = ...,
        total_kg_30d: _Optional[float] = ...,
        total_kg_90d: _Optional[float] = ...,
        total_kg_year: _Optional[float] = ...,
        yield_kg_per_hectare_30d: _Optional[float] = ...,
        yield_kg_per_hectare_90d: _Optional[float] = ...,
        yield_kg_per_hectare_year: _Optional[float] = ...,
        improvement_trend: _Optional[_Union[TrendDirection, str]] = ...,
        computed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
    ) -> None: ...

class TodayMetrics(_message.Message):
    __slots__ = ("deliveries", "total_kg", "grade_counts", "attribute_counts", "last_delivery", "metrics_date")
    class GradeCountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    class AttributeCountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DistributionCounts
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[DistributionCounts, _Mapping]] = ...
        ) -> None: ...

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
        deliveries: _Optional[int] = ...,
        total_kg: _Optional[float] = ...,
        grade_counts: _Optional[_Mapping[str, int]] = ...,
        attribute_counts: _Optional[_Mapping[str, DistributionCounts]] = ...,
        last_delivery: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        metrics_date: _Optional[str] = ...,
    ) -> None: ...

class FarmerSummary(_message.Message):
    __slots__ = (
        "farmer_id",
        "first_name",
        "last_name",
        "phone",
        "collection_point_id",
        "farm_size_hectares",
        "farm_scale",
        "grading_model_id",
        "grading_model_version",
        "historical",
        "today",
        "trend_direction",
        "created_at",
        "updated_at",
        "notification_channel",
        "interaction_pref",
        "pref_lang",
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
        farmer_id: _Optional[str] = ...,
        first_name: _Optional[str] = ...,
        last_name: _Optional[str] = ...,
        phone: _Optional[str] = ...,
        collection_point_id: _Optional[str] = ...,
        farm_size_hectares: _Optional[float] = ...,
        farm_scale: _Optional[_Union[FarmScale, str]] = ...,
        grading_model_id: _Optional[str] = ...,
        grading_model_version: _Optional[str] = ...,
        historical: _Optional[_Union[HistoricalMetrics, _Mapping]] = ...,
        today: _Optional[_Union[TodayMetrics, _Mapping]] = ...,
        trend_direction: _Optional[_Union[TrendDirection, str]] = ...,
        created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...,
        notification_channel: _Optional[_Union[NotificationChannel, str]] = ...,
        interaction_pref: _Optional[_Union[InteractionPreference, str]] = ...,
        pref_lang: _Optional[_Union[PreferredLanguage, str]] = ...,
    ) -> None: ...

class GetFarmerSummaryRequest(_message.Message):
    __slots__ = ("farmer_id",)
    FARMER_ID_FIELD_NUMBER: _ClassVar[int]
    farmer_id: str
    def __init__(self, farmer_id: _Optional[str] = ...) -> None: ...

class UpdateCommunicationPreferencesRequest(_message.Message):
    __slots__ = ("farmer_id", "notification_channel", "interaction_pref", "pref_lang")
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
        farmer_id: _Optional[str] = ...,
        notification_channel: _Optional[_Union[NotificationChannel, str]] = ...,
        interaction_pref: _Optional[_Union[InteractionPreference, str]] = ...,
        pref_lang: _Optional[_Union[PreferredLanguage, str]] = ...,
    ) -> None: ...

class UpdateCommunicationPreferencesResponse(_message.Message):
    __slots__ = ("farmer",)
    FARMER_FIELD_NUMBER: _ClassVar[int]
    farmer: Farmer
    def __init__(self, farmer: _Optional[_Union[Farmer, _Mapping]] = ...) -> None: ...
