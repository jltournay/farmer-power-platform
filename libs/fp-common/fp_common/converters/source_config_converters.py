"""Proto-to-Pydantic and Pydantic-to-Proto converters for Source Config domain.

Story 9.11a: SourceConfigService gRPC in Collection Model

These converters centralize the mapping between:
- SourceConfig Pydantic model (fp_common.models.source_config)
- SourceConfigSummary and SourceConfigResponse Proto messages

Field mapping strategy:
- Timestamps: Python datetime -> Protobuf Timestamp
- JSON serialization: model_dump_json() for config_json field
- Optional fields: Empty strings for nullable proto fields

Reference:
- Proto definitions: proto/collection/v1/collection.proto
- Pydantic models: fp_common/models/source_config.py
"""

from datetime import datetime

from fp_proto.collection.v1 import collection_pb2
from google.protobuf import timestamp_pb2

from fp_common.models.source_config import SourceConfig
from fp_common.models.source_config_summary import (
    SourceConfigDetail,
    SourceConfigSummary,
)


def _datetime_to_proto_timestamp(dt: datetime | None) -> timestamp_pb2.Timestamp:
    """Convert Python datetime to protobuf Timestamp.

    Args:
        dt: Python datetime object, or None.

    Returns:
        Protobuf Timestamp message. Returns empty timestamp if dt is None.
    """
    ts = timestamp_pb2.Timestamp()
    if dt is not None:
        ts.FromDatetime(dt)
    return ts


def _proto_timestamp_to_datetime(ts: timestamp_pb2.Timestamp) -> datetime | None:
    """Convert protobuf Timestamp to Python datetime.

    Args:
        ts: Protobuf Timestamp message.

    Returns:
        Python datetime object, or None if timestamp is empty.
    """
    if ts.seconds == 0 and ts.nanos == 0:
        return None
    return ts.ToDatetime()


# =============================================================================
# Pydantic-to-Proto Converters (for gRPC service responses)
# =============================================================================


def source_config_summary_to_proto(
    config: SourceConfig,
    updated_at: datetime | None = None,
) -> collection_pb2.SourceConfigSummary:
    """Convert SourceConfig Pydantic model to SourceConfigSummary proto.

    Args:
        config: The SourceConfig Pydantic model.
        updated_at: Optional timestamp for when the config was last updated.
            Since SourceConfig doesn't have timestamps, this must be provided
            separately (e.g., from MongoDB document metadata).

    Returns:
        SourceConfigSummary proto message.
    """
    # Get the AI agent ID from the transformation config
    ai_agent_id = config.transformation.get_ai_agent_id() or ""

    return collection_pb2.SourceConfigSummary(
        source_id=config.source_id,
        display_name=config.display_name,
        description=config.description,
        enabled=config.enabled,
        ingestion_mode=config.ingestion.mode,
        ai_agent_id=ai_agent_id,
        updated_at=_datetime_to_proto_timestamp(updated_at),
    )


def source_config_response_to_proto(
    config: SourceConfig,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> collection_pb2.SourceConfigResponse:
    """Convert SourceConfig Pydantic model to SourceConfigResponse proto.

    Args:
        config: The SourceConfig Pydantic model.
        created_at: Optional timestamp for when the config was created.
        updated_at: Optional timestamp for when the config was last updated.

    Returns:
        SourceConfigResponse proto message.
    """
    return collection_pb2.SourceConfigResponse(
        source_id=config.source_id,
        display_name=config.display_name,
        description=config.description,
        enabled=config.enabled,
        config_json=config.model_dump_json(indent=2),
        created_at=_datetime_to_proto_timestamp(created_at),
        updated_at=_datetime_to_proto_timestamp(updated_at),
    )


# =============================================================================
# Proto-to-Pydantic Converters (for BFF client - Story 9.11b)
# =============================================================================


def source_config_summary_from_proto(
    proto: collection_pb2.SourceConfigSummary,
) -> SourceConfigSummary:
    """Convert SourceConfigSummary proto to Pydantic model for BFF.

    Args:
        proto: The SourceConfigSummary proto message.

    Returns:
        SourceConfigSummary Pydantic model.
    """
    return SourceConfigSummary(
        source_id=proto.source_id,
        display_name=proto.display_name,
        description=proto.description,
        enabled=proto.enabled,
        ingestion_mode=proto.ingestion_mode,
        ai_agent_id=proto.ai_agent_id if proto.ai_agent_id else None,
        updated_at=_proto_timestamp_to_datetime(proto.updated_at),
    )


def source_config_detail_from_proto(
    proto: collection_pb2.SourceConfigResponse,
) -> SourceConfigDetail:
    """Convert SourceConfigResponse proto to SourceConfigDetail Pydantic model.

    Args:
        proto: The SourceConfigResponse proto message.

    Returns:
        SourceConfigDetail Pydantic model with full configuration.
    """
    return SourceConfigDetail(
        source_id=proto.source_id,
        display_name=proto.display_name,
        description=proto.description,
        enabled=proto.enabled,
        ingestion_mode="",  # Not in SourceConfigResponse, set to empty
        ai_agent_id=None,  # Not in SourceConfigResponse
        config_json=proto.config_json,
        created_at=_proto_timestamp_to_datetime(proto.created_at),
        updated_at=_proto_timestamp_to_datetime(proto.updated_at),
    )
