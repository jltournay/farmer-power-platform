"""Unit tests for source_config_converters module.

Story 9.11a: SourceConfigService gRPC in Collection Model
Story 9.11b: Updated converters to return Pydantic models

Tests verify bidirectional conversion correctness:
- Pydantic-to-Proto conversion for gRPC service responses
- Proto-to-Pydantic conversion for BFF clients
- Timestamp handling (datetime -> proto -> datetime roundtrip)
- JSON serialization for config_json field
"""

from datetime import UTC, datetime

from fp_common.converters import (
    source_config_detail_from_proto,
    source_config_response_to_proto,
    source_config_summary_from_proto,
    source_config_summary_to_proto,
)
from fp_common.models.source_config import SourceConfig
from fp_proto.collection.v1 import collection_pb2
from google.protobuf import timestamp_pb2


def create_test_source_config(
    source_id: str = "test-source",
    display_name: str = "Test Source",
    enabled: bool = True,
    mode: str = "blob_trigger",
    ai_agent_id: str | None = None,
) -> SourceConfig:
    """Create a test SourceConfig for testing."""
    ingestion_data = {
        "mode": mode,
        "file_format": "json",
        "processor_type": "json-extraction",
    }
    if mode == "blob_trigger":
        ingestion_data["landing_container"] = "test-landing"
    else:
        ingestion_data["schedule"] = "0 * * * *"
        ingestion_data["provider"] = "test-provider"

    transformation_data = {
        "extract_fields": ["field1", "field2"],
        "link_field": "farmer_id",
    }
    if ai_agent_id:
        transformation_data["ai_agent_id"] = ai_agent_id

    return SourceConfig.model_validate(
        {
            "source_id": source_id,
            "display_name": display_name,
            "description": "Test description",
            "enabled": enabled,
            "ingestion": ingestion_data,
            "transformation": transformation_data,
            "storage": {
                "raw_container": "test-raw",
                "index_collection": "test_documents",
            },
        }
    )


class TestSourceConfigSummaryToProto:
    """Tests for source_config_summary_to_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped to proto."""
        config = create_test_source_config(
            source_id="my-source",
            display_name="My Source",
            enabled=True,
            mode="blob_trigger",
        )
        proto = source_config_summary_to_proto(config)

        assert proto.source_id == "my-source"
        assert proto.display_name == "My Source"
        assert proto.description == "Test description"
        assert proto.enabled is True
        assert proto.ingestion_mode == "blob_trigger"

    def test_scheduled_pull_mode(self):
        """Scheduled pull mode is correctly mapped."""
        config = create_test_source_config(mode="scheduled_pull")
        proto = source_config_summary_to_proto(config)

        assert proto.ingestion_mode == "scheduled_pull"

    def test_ai_agent_id_mapped(self):
        """AI agent ID from transformation config is mapped."""
        config = create_test_source_config(ai_agent_id="qc-extractor-v1")
        proto = source_config_summary_to_proto(config)

        assert proto.ai_agent_id == "qc-extractor-v1"

    def test_ai_agent_id_empty_when_not_set(self):
        """AI agent ID is empty string when not configured."""
        config = create_test_source_config(ai_agent_id=None)
        proto = source_config_summary_to_proto(config)

        assert proto.ai_agent_id == ""

    def test_updated_at_timestamp_set(self):
        """Updated at timestamp is correctly set."""
        config = create_test_source_config()
        updated_at = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        proto = source_config_summary_to_proto(config, updated_at=updated_at)

        assert proto.updated_at.seconds > 0

    def test_updated_at_timestamp_none(self):
        """Updated at timestamp is empty when None."""
        config = create_test_source_config()
        proto = source_config_summary_to_proto(config, updated_at=None)

        assert proto.updated_at.seconds == 0
        assert proto.updated_at.nanos == 0


class TestSourceConfigResponseToProto:
    """Tests for source_config_response_to_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped to proto."""
        config = create_test_source_config(
            source_id="detail-source",
            display_name="Detail Source",
        )
        proto = source_config_response_to_proto(config)

        assert proto.source_id == "detail-source"
        assert proto.display_name == "Detail Source"
        assert proto.enabled is True

    def test_config_json_contains_full_config(self):
        """Config JSON contains the full serialized config."""
        config = create_test_source_config(
            source_id="json-test",
            mode="blob_trigger",
        )
        proto = source_config_response_to_proto(config)

        assert '"source_id": "json-test"' in proto.config_json
        assert '"blob_trigger"' in proto.config_json
        assert '"ingestion"' in proto.config_json
        assert '"transformation"' in proto.config_json
        assert '"storage"' in proto.config_json

    def test_timestamps_set(self):
        """Created and updated timestamps are correctly set."""
        config = create_test_source_config()
        created = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        updated = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)

        proto = source_config_response_to_proto(config, created_at=created, updated_at=updated)

        assert proto.created_at.seconds > 0
        assert proto.updated_at.seconds > 0


class TestSourceConfigSummaryFromProto:
    """Tests for source_config_summary_from_proto converter.

    Story 9.11b: Now returns SourceConfigSummary Pydantic model instead of dict.
    """

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped from proto to Pydantic model."""
        proto = collection_pb2.SourceConfigSummary(
            source_id="from-proto",
            display_name="From Proto",
            description="Proto description",
            enabled=True,
            ingestion_mode="blob_trigger",
            ai_agent_id="my-agent",
        )
        result = source_config_summary_from_proto(proto)

        assert result.source_id == "from-proto"
        assert result.display_name == "From Proto"
        assert result.description == "Proto description"
        assert result.enabled is True
        assert result.ingestion_mode == "blob_trigger"
        assert result.ai_agent_id == "my-agent"

    def test_empty_ai_agent_id_becomes_none(self):
        """Empty AI agent ID in proto becomes None in model."""
        proto = collection_pb2.SourceConfigSummary(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            ingestion_mode="blob_trigger",
            ai_agent_id="",  # Empty string
        )
        result = source_config_summary_from_proto(proto)

        assert result.ai_agent_id is None

    def test_timestamp_converted_to_datetime(self):
        """Updated at timestamp is converted to datetime object."""
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC))

        proto = collection_pb2.SourceConfigSummary(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            ingestion_mode="blob_trigger",
            updated_at=ts,
        )
        result = source_config_summary_from_proto(proto)

        assert result.updated_at is not None
        assert result.updated_at.year == 2025
        assert result.updated_at.month == 1
        assert result.updated_at.day == 15

    def test_empty_timestamp_becomes_none(self):
        """Empty timestamp becomes None."""
        proto = collection_pb2.SourceConfigSummary(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            ingestion_mode="blob_trigger",
        )
        result = source_config_summary_from_proto(proto)

        assert result.updated_at is None


class TestSourceConfigDetailFromProto:
    """Tests for source_config_detail_from_proto converter.

    Story 9.11b: Renamed from source_config_response_from_proto.
    Now returns SourceConfigDetail Pydantic model instead of dict.
    Extracts ingestion_mode and ai_agent_id from config_json for consistency.
    """

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped from proto to Pydantic model."""
        proto = collection_pb2.SourceConfigResponse(
            source_id="response-test",
            display_name="Response Test",
            description="Response description",
            enabled=True,
            config_json='{"key": "value"}',
        )
        result = source_config_detail_from_proto(proto)

        assert result.source_id == "response-test"
        assert result.display_name == "Response Test"
        assert result.description == "Response description"
        assert result.enabled is True
        assert result.config_json == '{"key": "value"}'

    def test_ingestion_mode_extracted_from_config_json(self):
        """Ingestion mode is extracted from config_json for consistency."""
        config_json = '{"source_id": "test", "ingestion": {"mode": "blob_trigger"}}'
        proto = collection_pb2.SourceConfigResponse(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            config_json=config_json,
        )
        result = source_config_detail_from_proto(proto)

        assert result.ingestion_mode == "blob_trigger"

    def test_ai_agent_id_extracted_from_config_json(self):
        """AI agent ID is extracted from config_json for consistency."""
        config_json = '{"source_id": "test", "transformation": {"ai_agent_id": "qc-extractor-v1"}}'
        proto = collection_pb2.SourceConfigResponse(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            config_json=config_json,
        )
        result = source_config_detail_from_proto(proto)

        assert result.ai_agent_id == "qc-extractor-v1"

    def test_empty_ai_agent_id_in_config_json_becomes_none(self):
        """Empty AI agent ID in config_json becomes None."""
        config_json = '{"source_id": "test", "transformation": {"ai_agent_id": ""}}'
        proto = collection_pb2.SourceConfigResponse(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            config_json=config_json,
        )
        result = source_config_detail_from_proto(proto)

        assert result.ai_agent_id is None

    def test_invalid_config_json_uses_defaults(self):
        """Invalid config_json uses default empty values."""
        proto = collection_pb2.SourceConfigResponse(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            config_json="not valid json",
        )
        result = source_config_detail_from_proto(proto)

        assert result.ingestion_mode == ""
        assert result.ai_agent_id is None

    def test_timestamps_converted_to_datetime(self):
        """Timestamps are converted to datetime objects."""
        created_ts = timestamp_pb2.Timestamp()
        created_ts.FromDatetime(datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC))
        updated_ts = timestamp_pb2.Timestamp()
        updated_ts.FromDatetime(datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC))

        proto = collection_pb2.SourceConfigResponse(
            source_id="test",
            display_name="Test",
            description="Desc",
            enabled=True,
            config_json="{}",
            created_at=created_ts,
            updated_at=updated_ts,
        )
        result = source_config_detail_from_proto(proto)

        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.created_at.year == 2025
        assert result.created_at.month == 1
        assert result.created_at.day == 1
        assert result.updated_at.year == 2025
        assert result.updated_at.month == 1
        assert result.updated_at.day == 15


class TestRoundTrip:
    """Tests for Pydantic -> Proto -> Pydantic round-trip conversions.

    Story 9.11b: Updated to test Pydantic model return types.
    """

    def test_summary_round_trip(self):
        """SourceConfigSummary round-trip preserves data."""
        config = create_test_source_config(
            source_id="round-trip",
            display_name="Round Trip Test",
            enabled=True,
            mode="blob_trigger",
            ai_agent_id="test-agent",
        )
        updated_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        proto = source_config_summary_to_proto(config, updated_at=updated_at)
        result = source_config_summary_from_proto(proto)

        assert result.source_id == config.source_id
        assert result.display_name == config.display_name
        assert result.enabled == config.enabled
        assert result.ingestion_mode == config.ingestion.mode
        assert result.ai_agent_id == config.transformation.get_ai_agent_id()

    def test_detail_round_trip(self):
        """SourceConfigDetail round-trip preserves data."""
        config = create_test_source_config(
            source_id="detail-round-trip",
            display_name="Detail Round Trip",
        )
        created_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        updated_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        proto = source_config_response_to_proto(config, created_at=created_at, updated_at=updated_at)
        result = source_config_detail_from_proto(proto)

        assert result.source_id == config.source_id
        assert result.display_name == config.display_name
        assert result.enabled == config.enabled
        # Verify JSON is valid by checking it contains expected content
        assert config.source_id in result.config_json
