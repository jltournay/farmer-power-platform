"""Proto-to-Pydantic and Pydantic-to-Proto converters for Agent Config domain.

Story 9.12a: AgentConfigService gRPC in AI Model
Story 9.12b: Agent Config gRPC Client + REST API in BFF (Proto-to-Pydantic converters)

These converters centralize the mapping between:
- AgentConfig Pydantic model (ai_model.domain.agent_config)
- Prompt Pydantic model (ai_model.domain.prompt)
- AgentConfigSummary, AgentConfigResponse, PromptSummary Proto messages

Field mapping strategy:
- Timestamps: Python datetime -> Protobuf Timestamp
- JSON serialization: model_dump_json() for config_json field
- Model extraction: Extract llm.model or tiered_llm.diagnose.model
- Optional fields: Empty strings for nullable proto fields

Proto-to-Pydantic converters (Story 9.12b):
- agent_config_summary_from_proto: Returns AgentConfigSummary Pydantic model
- agent_config_detail_from_proto: Returns AgentConfigDetail Pydantic model
- prompt_summary_from_proto: Returns PromptSummary Pydantic model

Reference:
- Proto definitions: proto/ai_model/v1/ai_model.proto
- Pydantic models: services/ai-model/src/ai_model/domain/agent_config.py
- Pydantic models: services/ai-model/src/ai_model/domain/prompt.py
- BFF models: libs/fp-common/fp_common/models/agent_config_summary.py
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - used at runtime
from typing import TYPE_CHECKING

from google.protobuf import timestamp_pb2

if TYPE_CHECKING:
    from fp_proto.ai_model.v1 import ai_model_pb2

    from fp_common.models.agent_config_summary import (
        AgentConfigDetail,
        AgentConfigSummary,
        PromptSummary,
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


def agent_config_summary_to_proto(
    config,  # AgentConfig (any subtype)
    prompt_count: int,
) -> ai_model_pb2.AgentConfigSummary:
    """Convert AgentConfig Pydantic model to AgentConfigSummary proto.

    Args:
        config: The AgentConfig Pydantic model (any agent type).
        prompt_count: Number of linked prompts (from PromptRepository.count_by_agent).

    Returns:
        AgentConfigSummary proto message.
    """
    from fp_proto.ai_model.v1 import ai_model_pb2

    # Extract model from llm config (or tiered_llm for tiered-vision)
    model = ""
    if hasattr(config, "tiered_llm") and config.tiered_llm is not None:
        # Tiered-vision uses diagnose model as the primary
        model = config.tiered_llm.diagnose.model
    elif hasattr(config, "llm") and config.llm is not None:
        model = config.llm.model

    # Get updated_at from metadata
    updated_at = None
    if hasattr(config, "metadata") and config.metadata is not None:
        updated_at = config.metadata.updated_at

    return ai_model_pb2.AgentConfigSummary(
        agent_id=config.agent_id,
        version=config.version,
        agent_type=config.type,
        status=config.status.value if hasattr(config.status, "value") else str(config.status),
        description=config.description,
        model=model,
        prompt_count=prompt_count,
        updated_at=_datetime_to_proto_timestamp(updated_at),
    )


def agent_config_response_to_proto(
    config,  # AgentConfig (any subtype)
    prompts: list,  # list[Prompt]
) -> ai_model_pb2.AgentConfigResponse:
    """Convert AgentConfig Pydantic model to AgentConfigResponse proto.

    Args:
        config: The AgentConfig Pydantic model (any agent type).
        prompts: List of Prompt Pydantic models linked to this agent.

    Returns:
        AgentConfigResponse proto message with full config as JSON.
    """
    from fp_proto.ai_model.v1 import ai_model_pb2

    # Get timestamps from metadata
    created_at = None
    updated_at = None
    if hasattr(config, "metadata") and config.metadata is not None:
        created_at = config.metadata.created_at
        updated_at = config.metadata.updated_at

    # Convert prompts to PromptSummary protos
    prompt_summaries = [prompt_summary_to_proto(p) for p in prompts]

    return ai_model_pb2.AgentConfigResponse(
        agent_id=config.agent_id,
        version=config.version,
        agent_type=config.type,
        status=config.status.value if hasattr(config.status, "value") else str(config.status),
        description=config.description,
        config_json=config.model_dump_json(indent=2),
        prompts=prompt_summaries,
        created_at=_datetime_to_proto_timestamp(created_at),
        updated_at=_datetime_to_proto_timestamp(updated_at),
    )


def prompt_summary_to_proto(
    prompt,  # Prompt
) -> ai_model_pb2.PromptSummary:
    """Convert Prompt Pydantic model to PromptSummary proto.

    Args:
        prompt: The Prompt Pydantic model.

    Returns:
        PromptSummary proto message.
    """
    from fp_proto.ai_model.v1 import ai_model_pb2

    # Get updated_at and author from metadata
    updated_at = None
    author = ""
    if hasattr(prompt, "metadata") and prompt.metadata is not None:
        updated_at = prompt.metadata.updated_at
        author = prompt.metadata.author or ""

    return ai_model_pb2.PromptSummary(
        id=prompt.id,
        prompt_id=prompt.prompt_id,
        agent_id=prompt.agent_id,
        version=prompt.version,
        status=prompt.status.value if hasattr(prompt.status, "value") else str(prompt.status),
        author=author,
        updated_at=_datetime_to_proto_timestamp(updated_at),
    )


# =============================================================================
# Proto-to-Pydantic Converters (for BFF client - Story 9.12b)
# =============================================================================


def prompt_summary_from_proto(
    proto: ai_model_pb2.PromptSummary,
) -> PromptSummary:
    """Convert PromptSummary proto to Pydantic model for BFF.

    Args:
        proto: The PromptSummary proto message.

    Returns:
        PromptSummary Pydantic model.
    """
    from fp_common.models.agent_config_summary import PromptSummary

    return PromptSummary(
        id=proto.id,
        prompt_id=proto.prompt_id,
        agent_id=proto.agent_id,
        version=proto.version,
        status=proto.status,
        author=proto.author if proto.author else "",
        updated_at=_proto_timestamp_to_datetime(proto.updated_at),
    )


def agent_config_summary_from_proto(
    proto: ai_model_pb2.AgentConfigSummary,
) -> AgentConfigSummary:
    """Convert AgentConfigSummary proto to Pydantic model for BFF.

    Args:
        proto: The AgentConfigSummary proto message.

    Returns:
        AgentConfigSummary Pydantic model.
    """
    from fp_common.models.agent_config_summary import AgentConfigSummary

    return AgentConfigSummary(
        agent_id=proto.agent_id,
        version=proto.version,
        agent_type=proto.agent_type,
        status=proto.status,
        description=proto.description,
        model=proto.model if proto.model else "",
        prompt_count=proto.prompt_count,
        updated_at=_proto_timestamp_to_datetime(proto.updated_at),
    )


def agent_config_detail_from_proto(
    proto: ai_model_pb2.AgentConfigResponse,
) -> AgentConfigDetail:
    """Convert AgentConfigResponse proto to AgentConfigDetail Pydantic model.

    Args:
        proto: The AgentConfigResponse proto message.

    Returns:
        AgentConfigDetail Pydantic model with full configuration.
    """
    from fp_common.models.agent_config_summary import AgentConfigDetail

    # Convert prompts to Pydantic models
    prompts = [prompt_summary_from_proto(p) for p in proto.prompts]

    return AgentConfigDetail(
        agent_id=proto.agent_id,
        version=proto.version,
        agent_type=proto.agent_type,
        status=proto.status,
        description=proto.description,
        model="",  # AgentConfigResponse proto doesn't include model field; UI can parse from config_json if needed
        prompt_count=len(prompts),
        config_json=proto.config_json,
        prompts=prompts,
        created_at=_proto_timestamp_to_datetime(proto.created_at),
        updated_at=_proto_timestamp_to_datetime(proto.updated_at),
    )


# Legacy dict converter - kept for backward compatibility
def agent_config_response_from_proto(
    proto: ai_model_pb2.AgentConfigResponse,
) -> AgentConfigDetail:
    """Convert AgentConfigResponse proto to AgentConfigDetail Pydantic model.

    This is an alias for agent_config_detail_from_proto() for backward compatibility.

    Args:
        proto: The AgentConfigResponse proto message.

    Returns:
        AgentConfigDetail Pydantic model with full configuration.
    """
    return agent_config_detail_from_proto(proto)
