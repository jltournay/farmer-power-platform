"""Proto-to-Pydantic converters for Plantation domain.

These converters centralize the mapping from Proto messages to Pydantic models,
eliminating duplicate _to_dict() methods across services and MCP clients.

Field mapping strategy:
- Proto enum names (FARM_SCALE_SMALLHOLDER) -> Pydantic enum values (smallholder)
- Nested messages -> Nested Pydantic models
- Optional fields -> Default values when not present
- Timestamp fields -> datetime objects

Reference:
- Proto definitions: proto/plantation/v1/plantation.proto
- Pydantic models: fp_common/models/
"""

from datetime import datetime
from typing import Any, TypeVar

from fp_proto.plantation.v1 import plantation_pb2

from fp_common.models import (
    CollectionPoint,
    Factory,
    Farmer,
    FarmScale,
    GeoLocation,
    HistoricalMetrics,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
    QualityThresholds,
    Region,
    TodayMetrics,
    TrendDirection,
)
from fp_common.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    CollectionPointCapacity,
    ContactInfo,
    Coordinate,
    FlushCalendar,
    FlushPeriod,
    Geography,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    PolygonRing,
    RegionBoundary,
    WeatherConfig,
)

T = TypeVar("T")


def _proto_enum_to_pydantic(proto_name: str, pydantic_enum: type[T], prefix: str) -> T:  # noqa: UP047
    """Convert Proto enum name to Pydantic enum value.

    Proto enums use uppercase with prefix (e.g., FARM_SCALE_SMALLHOLDER).
    Pydantic enums use lowercase values (e.g., "smallholder").

    Args:
        proto_name: Proto enum name (e.g., "FARM_SCALE_SMALLHOLDER").
        pydantic_enum: Target Pydantic enum class.
        prefix: Prefix to strip (e.g., "farm_scale_").

    Returns:
        Matching Pydantic enum member.
    """
    # Strip prefix and convert to lowercase
    value = proto_name.lower()
    if value.startswith(prefix):
        value = value[len(prefix) :]

    # Match against Pydantic enum values
    for member in pydantic_enum:
        if member.value == value:
            return member

    # Fallback to first member if no match (for UNSPECIFIED)
    return next(iter(pydantic_enum))


def _timestamp_to_datetime(proto_ts: Any) -> datetime | None:
    """Convert Proto Timestamp to Python datetime.

    Args:
        proto_ts: Proto Timestamp message.

    Returns:
        Python datetime or None if timestamp is empty.
    """
    if proto_ts and proto_ts.seconds > 0:
        return proto_ts.ToDatetime()
    return None


def farmer_from_proto(proto: plantation_pb2.Farmer) -> Farmer:
    """Convert Farmer proto message to Pydantic model.

    Args:
        proto: The Farmer proto message from gRPC response.

    Returns:
        Farmer Pydantic model with all fields mapped.

    Note:
        Enum values are converted from Proto enum to Pydantic enum.
        The Proto uses uppercase (FARM_SCALE_SMALLHOLDER), Pydantic uses lowercase.
    """
    # Convert Proto enum names to Pydantic enum values
    farm_scale = _proto_enum_to_pydantic(
        plantation_pb2.FarmScale.Name(proto.farm_scale),
        FarmScale,
        "farm_scale_",
    )
    notification_channel = _proto_enum_to_pydantic(
        plantation_pb2.NotificationChannel.Name(proto.notification_channel),
        NotificationChannel,
        "notification_channel_",
    )
    interaction_pref = _proto_enum_to_pydantic(
        plantation_pb2.InteractionPreference.Name(proto.interaction_pref),
        InteractionPreference,
        "interaction_preference_",
    )
    pref_lang = _proto_enum_to_pydantic(
        plantation_pb2.PreferredLanguage.Name(proto.pref_lang),
        PreferredLanguage,
        "preferred_language_",
    )

    # Build timestamps
    created_at = _timestamp_to_datetime(proto.created_at)
    updated_at = _timestamp_to_datetime(proto.updated_at)
    registration_date = _timestamp_to_datetime(proto.registration_date)

    return Farmer(
        id=proto.id,
        grower_number=proto.grower_number if proto.grower_number else None,
        first_name=proto.first_name,
        last_name=proto.last_name,
        region_id=proto.region_id,
        collection_point_id=proto.collection_point_id,
        contact=ContactInfo(
            phone=proto.contact.phone if proto.contact else "",
            email=proto.contact.email if proto.contact else "",
            address=proto.contact.address if proto.contact else "",
        ),
        farm_location=GeoLocation(
            latitude=proto.farm_location.latitude if proto.farm_location else 0.0,
            longitude=proto.farm_location.longitude if proto.farm_location else 0.0,
            altitude_meters=proto.farm_location.altitude_meters if proto.farm_location else 0.0,
        ),
        farm_size_hectares=proto.farm_size_hectares if proto.farm_size_hectares > 0 else 0.01,
        farm_scale=farm_scale,
        national_id=proto.national_id if proto.national_id else "unknown",
        is_active=proto.is_active,
        notification_channel=notification_channel,
        interaction_pref=interaction_pref,
        pref_lang=pref_lang,
        registration_date=registration_date if registration_date else datetime.now(),
        created_at=created_at if created_at else datetime.now(),
        updated_at=updated_at if updated_at else datetime.now(),
    )


def factory_from_proto(proto: plantation_pb2.Factory) -> Factory:
    """Convert Factory proto message to Pydantic model.

    Args:
        proto: The Factory proto message from gRPC response.

    Returns:
        Factory Pydantic model with quality_thresholds.

    Note:
        If quality_thresholds is not set in proto, defaults are used (85/70/50).
    """
    # Handle quality thresholds with defaults
    if proto.HasField("quality_thresholds"):
        qt = QualityThresholds(
            tier_1=proto.quality_thresholds.tier_1,
            tier_2=proto.quality_thresholds.tier_2,
            tier_3=proto.quality_thresholds.tier_3,
        )
    else:
        qt = QualityThresholds()  # Uses defaults from model

    # Handle payment policy
    if proto.HasField("payment_policy"):
        policy_type = _proto_enum_to_pydantic(
            plantation_pb2.PaymentPolicyType.Name(proto.payment_policy.policy_type),
            PaymentPolicyType,
            "payment_policy_type_",
        )
        pp = PaymentPolicy(
            policy_type=policy_type,
            tier_1_adjustment=proto.payment_policy.tier_1_adjustment,
            tier_2_adjustment=proto.payment_policy.tier_2_adjustment,
            tier_3_adjustment=proto.payment_policy.tier_3_adjustment,
            below_tier_3_adjustment=proto.payment_policy.below_tier_3_adjustment,
        )
    else:
        pp = PaymentPolicy()  # Uses defaults from model

    # Build timestamps
    created_at = _timestamp_to_datetime(proto.created_at)
    updated_at = _timestamp_to_datetime(proto.updated_at)

    return Factory(
        id=proto.id,
        name=proto.name,
        code=proto.code,
        region_id=proto.region_id,
        location=GeoLocation(
            latitude=proto.location.latitude if proto.location else 0.0,
            longitude=proto.location.longitude if proto.location else 0.0,
            altitude_meters=proto.location.altitude_meters if proto.location else 0.0,
        ),
        contact=ContactInfo(
            phone=proto.contact.phone if proto.contact else "",
            email=proto.contact.email if proto.contact else "",
            address=proto.contact.address if proto.contact else "",
        ),
        processing_capacity_kg=proto.processing_capacity_kg,
        quality_thresholds=qt,
        payment_policy=pp,
        is_active=proto.is_active,
        created_at=created_at if created_at else datetime.now(),
        updated_at=updated_at if updated_at else datetime.now(),
    )


def collection_point_from_proto(proto: plantation_pb2.CollectionPoint) -> CollectionPoint:
    """Convert CollectionPoint proto message to Pydantic model.

    Args:
        proto: The CollectionPoint proto message from gRPC response.

    Returns:
        CollectionPoint Pydantic model.
    """
    # Handle operating hours
    if proto.HasField("operating_hours"):
        operating_hours = OperatingHours(
            weekdays=proto.operating_hours.weekdays if proto.operating_hours.weekdays else "06:00-10:00",
            weekends=proto.operating_hours.weekends if proto.operating_hours.weekends else "07:00-09:00",
        )
    else:
        operating_hours = OperatingHours()

    # Handle capacity
    if proto.HasField("capacity"):
        capacity = CollectionPointCapacity(
            max_daily_kg=proto.capacity.max_daily_kg,
            storage_type=proto.capacity.storage_type if proto.capacity.storage_type else "covered_shed",
            has_weighing_scale=proto.capacity.has_weighing_scale,
            has_qc_device=proto.capacity.has_qc_device,
        )
    else:
        capacity = CollectionPointCapacity()

    # Build timestamps
    created_at = _timestamp_to_datetime(proto.created_at)
    updated_at = _timestamp_to_datetime(proto.updated_at)

    return CollectionPoint(
        id=proto.id,
        name=proto.name,
        factory_id=proto.factory_id,
        region_id=proto.region_id,
        location=GeoLocation(
            latitude=proto.location.latitude if proto.location else 0.0,
            longitude=proto.location.longitude if proto.location else 0.0,
            altitude_meters=proto.location.altitude_meters if proto.location else 0.0,
        ),
        clerk_id=proto.clerk_id if proto.clerk_id else None,
        clerk_phone=proto.clerk_phone if proto.clerk_phone else None,
        operating_hours=operating_hours,
        collection_days=list(proto.collection_days) if proto.collection_days else ["mon", "wed", "fri", "sat"],
        capacity=capacity,
        status=proto.status if proto.status else "active",
        created_at=created_at if created_at else datetime.now(),
        updated_at=updated_at if updated_at else datetime.now(),
    )


def _coordinate_from_proto(proto: plantation_pb2.Coordinate) -> Coordinate:
    """Convert Coordinate proto message to value object (Story 1.10)."""
    return Coordinate(
        longitude=proto.longitude,
        latitude=proto.latitude,
    )


def _polygon_ring_from_proto(proto: plantation_pb2.PolygonRing) -> PolygonRing:
    """Convert PolygonRing proto message to value object (Story 1.10)."""
    return PolygonRing(
        points=[_coordinate_from_proto(p) for p in proto.points],
    )


def _region_boundary_from_proto(proto: plantation_pb2.RegionBoundary) -> RegionBoundary:
    """Convert RegionBoundary proto message to value object (Story 1.10)."""
    return RegionBoundary(
        type=proto.type if proto.type else "Polygon",
        rings=[_polygon_ring_from_proto(r) for r in proto.rings],
    )


def region_from_proto(proto: plantation_pb2.Region) -> Region:
    """Convert Region proto message to Pydantic model.

    Args:
        proto: The Region proto message from gRPC response.

    Returns:
        Region Pydantic model with nested geography, flush_calendar, agronomic, and weather_config.

    Note:
        Story 1.10: Includes optional boundary, area_km2, and perimeter_km fields.
    """
    # Convert altitude band label enum
    altitude_label = _proto_enum_to_pydantic(
        plantation_pb2.AltitudeBandLabel.Name(proto.geography.altitude_band.label)
        if proto.geography
        else "ALTITUDE_BAND_HIGHLAND",
        AltitudeBandLabel,
        "altitude_band_",
    )

    # Story 1.10: Build boundary if present
    boundary = None
    if proto.geography and proto.geography.HasField("boundary") and len(proto.geography.boundary.rings) > 0:
        boundary = _region_boundary_from_proto(proto.geography.boundary)

    # Story 1.10: Extract optional computed values
    area_km2 = None
    perimeter_km = None
    if proto.geography:
        if proto.geography.HasField("area_km2"):
            area_km2 = proto.geography.area_km2
        if proto.geography.HasField("perimeter_km"):
            perimeter_km = proto.geography.perimeter_km

    # Build geography
    geography = Geography(
        center_gps=GPS(
            lat=proto.geography.center_gps.lat if proto.geography and proto.geography.center_gps else 0.0,
            lng=proto.geography.center_gps.lng if proto.geography and proto.geography.center_gps else 0.0,
        ),
        radius_km=proto.geography.radius_km if proto.geography and proto.geography.radius_km > 0 else 25.0,
        altitude_band=AltitudeBand(
            min_meters=proto.geography.altitude_band.min_meters if proto.geography else 0,
            max_meters=proto.geography.altitude_band.max_meters if proto.geography else 2500,
            label=altitude_label,
        ),
        boundary=boundary,
        area_km2=area_km2,
        perimeter_km=perimeter_km,
    )

    # Build flush calendar
    def _flush_period_from_proto(fp: Any) -> FlushPeriod:
        return FlushPeriod(
            start=fp.start if fp and fp.start else "01-01",
            end=fp.end if fp and fp.end else "01-31",
            characteristics=fp.characteristics if fp else "",
        )

    flush_calendar = FlushCalendar(
        first_flush=_flush_period_from_proto(proto.flush_calendar.first_flush if proto.flush_calendar else None),
        monsoon_flush=_flush_period_from_proto(proto.flush_calendar.monsoon_flush if proto.flush_calendar else None),
        autumn_flush=_flush_period_from_proto(proto.flush_calendar.autumn_flush if proto.flush_calendar else None),
        dormant=_flush_period_from_proto(proto.flush_calendar.dormant if proto.flush_calendar else None),
    )

    # Build agronomic
    agronomic = Agronomic(
        soil_type=proto.agronomic.soil_type if proto.agronomic and proto.agronomic.soil_type else "unknown",
        typical_diseases=list(proto.agronomic.typical_diseases) if proto.agronomic else [],
        harvest_peak_hours=proto.agronomic.harvest_peak_hours
        if proto.agronomic and proto.agronomic.harvest_peak_hours
        else "06:00-10:00",
        frost_risk=proto.agronomic.frost_risk if proto.agronomic else False,
    )

    # Build weather config
    weather_config = WeatherConfig(
        api_location=GPS(
            lat=proto.weather_config.api_location.lat
            if proto.weather_config and proto.weather_config.api_location
            else 0.0,
            lng=proto.weather_config.api_location.lng
            if proto.weather_config and proto.weather_config.api_location
            else 0.0,
        ),
        altitude_for_api=proto.weather_config.altitude_for_api if proto.weather_config else 0,
        collection_time=proto.weather_config.collection_time
        if proto.weather_config and proto.weather_config.collection_time
        else "06:00",
    )

    # Build timestamps
    created_at = _timestamp_to_datetime(proto.created_at)
    updated_at = _timestamp_to_datetime(proto.updated_at)

    return Region(
        region_id=proto.region_id,
        name=proto.name,
        county=proto.county,
        country=proto.country if proto.country else "Kenya",
        geography=geography,
        flush_calendar=flush_calendar,
        agronomic=agronomic,
        weather_config=weather_config,
        is_active=proto.is_active,
        created_at=created_at if created_at else datetime.now(),
        updated_at=updated_at if updated_at else datetime.now(),
    )


def farmer_summary_from_proto(proto: plantation_pb2.FarmerSummary) -> dict[str, Any]:
    """Convert FarmerSummary proto message to dict with structured metrics.

    Args:
        proto: The FarmerSummary proto message from gRPC response.

    Returns:
        Dict with farmer info, historical metrics, and today metrics.

    Note:
        Returns a dict rather than a dedicated Pydantic model because
        FarmerSummary is a composite view that doesn't map directly to
        a single entity model. The historical and today metrics are
        converted to their respective Pydantic models.
    """
    # Convert enums
    farm_scale = _proto_enum_to_pydantic(
        plantation_pb2.FarmScale.Name(proto.farm_scale),
        FarmScale,
        "farm_scale_",
    )
    trend_direction = _proto_enum_to_pydantic(
        plantation_pb2.TrendDirection.Name(proto.trend_direction),
        TrendDirection,
        "trend_direction_",
    )
    notification_channel = _proto_enum_to_pydantic(
        plantation_pb2.NotificationChannel.Name(proto.notification_channel),
        NotificationChannel,
        "notification_channel_",
    )
    interaction_pref = _proto_enum_to_pydantic(
        plantation_pb2.InteractionPreference.Name(proto.interaction_pref),
        InteractionPreference,
        "interaction_preference_",
    )
    pref_lang = _proto_enum_to_pydantic(
        plantation_pb2.PreferredLanguage.Name(proto.pref_lang),
        PreferredLanguage,
        "preferred_language_",
    )

    # Convert historical metrics if present
    historical: HistoricalMetrics | None = None
    if proto.HasField("historical"):
        h = proto.historical

        # Convert nested attribute distributions
        def _convert_attr_dist(proto_dist: Any) -> dict[str, dict[str, int]]:
            result: dict[str, dict[str, int]] = {}
            for attr_name, counts_proto in proto_dist.items():
                result[attr_name] = dict(counts_proto.counts)
            return result

        historical_trend = _proto_enum_to_pydantic(
            plantation_pb2.TrendDirection.Name(h.improvement_trend),
            TrendDirection,
            "trend_direction_",
        )

        historical = HistoricalMetrics(
            grade_distribution_30d=dict(h.grade_distribution_30d),
            grade_distribution_90d=dict(h.grade_distribution_90d),
            grade_distribution_year=dict(h.grade_distribution_year),
            attribute_distributions_30d=_convert_attr_dist(h.attribute_distributions_30d),
            attribute_distributions_90d=_convert_attr_dist(h.attribute_distributions_90d),
            attribute_distributions_year=_convert_attr_dist(h.attribute_distributions_year),
            primary_percentage_30d=h.primary_percentage_30d,
            primary_percentage_90d=h.primary_percentage_90d,
            primary_percentage_year=h.primary_percentage_year,
            total_kg_30d=h.total_kg_30d,
            total_kg_90d=h.total_kg_90d,
            total_kg_year=h.total_kg_year,
            yield_kg_per_hectare_30d=h.yield_kg_per_hectare_30d,
            yield_kg_per_hectare_90d=h.yield_kg_per_hectare_90d,
            yield_kg_per_hectare_year=h.yield_kg_per_hectare_year,
            improvement_trend=historical_trend,
            computed_at=_timestamp_to_datetime(h.computed_at),
        )

    # Convert today metrics if present
    today: TodayMetrics | None = None
    if proto.HasField("today"):
        t = proto.today

        # Convert attribute counts
        attr_counts: dict[str, dict[str, int]] = {}
        for attr_name, counts_proto in t.attribute_counts.items():
            attr_counts[attr_name] = dict(counts_proto.counts)

        today = TodayMetrics(
            deliveries=t.deliveries,
            total_kg=t.total_kg,
            grade_counts=dict(t.grade_counts),
            attribute_counts=attr_counts,
            last_delivery=_timestamp_to_datetime(t.last_delivery),
            metrics_date=datetime.strptime(t.metrics_date, "%Y-%m-%d").date()
            if t.metrics_date
            else datetime.now().date(),
        )

    # Build timestamps
    created_at = _timestamp_to_datetime(proto.created_at)
    updated_at = _timestamp_to_datetime(proto.updated_at)

    return {
        "farmer_id": proto.farmer_id,
        "first_name": proto.first_name,
        "last_name": proto.last_name,
        "phone": proto.phone,
        "collection_point_id": proto.collection_point_id,
        "farm_size_hectares": proto.farm_size_hectares,
        "farm_scale": farm_scale,
        "grading_model_id": proto.grading_model_id,
        "grading_model_version": proto.grading_model_version,
        "historical": historical,
        "today": today,
        "trend_direction": trend_direction,
        "notification_channel": notification_channel,
        "interaction_pref": interaction_pref,
        "pref_lang": pref_lang,
        "created_at": created_at,
        "updated_at": updated_at,
    }
