"""Unit tests for the unified CostRecordedEvent model.

Story 13.1: Shared Cost Event Model (ADR-016)

Tests cover:
- Model instantiation with all field combinations
- JSON serialization (model_dump_json())
- Decimal serialization to string
- Timestamp serialization to ISO format
- Validation (cost_type enum, non-negative quantity)
- Import from both paths (new and legacy)
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fp_common.events.cost_recorded import (
    CostRecordedEvent,
    CostType,
    CostUnit,
)
from pydantic import ValidationError


class TestCostTypeEnum:
    """Tests for the CostType enum."""

    def test_cost_type_has_all_values(self) -> None:
        """Verify all cost types are defined."""
        assert CostType.LLM == "llm"
        assert CostType.DOCUMENT == "document"
        assert CostType.EMBEDDING == "embedding"
        assert CostType.SMS == "sms"

    def test_cost_type_enum_count(self) -> None:
        """Verify exactly 4 cost types exist."""
        assert len(CostType) == 4


class TestCostUnitEnum:
    """Tests for the CostUnit enum."""

    def test_cost_unit_has_all_values(self) -> None:
        """Verify all cost units are defined."""
        assert CostUnit.TOKENS == "tokens"
        assert CostUnit.PAGES == "pages"
        assert CostUnit.MESSAGES == "messages"
        assert CostUnit.QUERIES == "queries"

    def test_cost_unit_enum_count(self) -> None:
        """Verify exactly 4 cost units exist."""
        assert len(CostUnit) == 4


class TestCostRecordedEventInstantiation:
    """Tests for CostRecordedEvent model instantiation."""

    def test_create_llm_cost_event(self) -> None:
        """Test creating an LLM cost event with all required fields."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.0015",
            quantity=1500,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={
                "model": "anthropic/claude-3-haiku",
                "agent_type": "extractor",
                "tokens_in": 1000,
                "tokens_out": 500,
            },
        )

        assert event.cost_type == CostType.LLM
        assert event.amount_usd == Decimal("0.0015")
        assert event.quantity == 1500
        assert event.unit == CostUnit.TOKENS
        assert event.source_service == "ai-model"
        assert event.success is True
        assert event.metadata["model"] == "anthropic/claude-3-haiku"
        assert event.factory_id is None
        assert event.request_id is None

    def test_create_document_cost_event(self) -> None:
        """Test creating a document processing cost event."""
        event = CostRecordedEvent(
            cost_type=CostType.DOCUMENT,
            amount_usd="0.25",
            quantity=5,
            unit=CostUnit.PAGES,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={
                "model_id": "azure-document-intelligence",
                "page_count": 5,
            },
            factory_id="FAC-001",
        )

        assert event.cost_type == CostType.DOCUMENT
        assert event.amount_usd == Decimal("0.25")
        assert event.quantity == 5
        assert event.unit == CostUnit.PAGES
        assert event.factory_id == "FAC-001"

    def test_create_embedding_cost_event(self) -> None:
        """Test creating an embedding cost event."""
        event = CostRecordedEvent(
            cost_type=CostType.EMBEDDING,
            amount_usd="0.0001",
            quantity=10,
            unit=CostUnit.QUERIES,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={
                "model": "text-embedding-3-small",
                "texts_count": 10,
            },
        )

        assert event.cost_type == CostType.EMBEDDING
        assert event.unit == CostUnit.QUERIES

    def test_create_sms_cost_event(self) -> None:
        """Test creating an SMS cost event."""
        event = CostRecordedEvent(
            cost_type=CostType.SMS,
            amount_usd="0.05",
            quantity=3,
            unit=CostUnit.MESSAGES,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="notification-model",
            success=True,
            metadata={
                "message_type": "action_plan",
                "recipient_count": 3,
            },
        )

        assert event.cost_type == CostType.SMS
        assert event.unit == CostUnit.MESSAGES

    def test_create_with_optional_fields(self) -> None:
        """Test creating event with optional factory_id and request_id."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.001",
            quantity=500,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
            factory_id="FAC-001",
            request_id="req-12345",
        )

        assert event.factory_id == "FAC-001"
        assert event.request_id == "req-12345"

    def test_amount_usd_decimal_precision(self) -> None:
        """Test that amount_usd preserves decimal precision."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.00000123",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
        )

        assert event.amount_usd == Decimal("0.00000123")
        assert str(event.amount_usd) == "0.00000123"


class TestCostRecordedEventValidation:
    """Tests for CostRecordedEvent validation."""

    def test_invalid_cost_type_raises_error(self) -> None:
        """Test that invalid cost_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CostRecordedEvent(
                cost_type="invalid_type",  # type: ignore
                amount_usd="0.001",
                quantity=100,
                unit=CostUnit.TOKENS,
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

        assert "cost_type" in str(exc_info.value)

    def test_invalid_unit_raises_error(self) -> None:
        """Test that invalid unit raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CostRecordedEvent(
                cost_type=CostType.LLM,
                amount_usd="0.001",
                quantity=100,
                unit="invalid_unit",  # type: ignore
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

        assert "unit" in str(exc_info.value)

    def test_negative_quantity_raises_error(self) -> None:
        """Test that negative quantity raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CostRecordedEvent(
                cost_type=CostType.LLM,
                amount_usd="0.001",
                quantity=-1,
                unit=CostUnit.TOKENS,
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

        assert "quantity" in str(exc_info.value)

    def test_zero_quantity_is_valid(self) -> None:
        """Test that zero quantity is valid (failed calls may have 0 tokens)."""
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.0",
            quantity=0,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=False,  # Failed call
            metadata={},
        )

        assert event.quantity == 0

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            CostRecordedEvent(
                cost_type=CostType.LLM,
                # missing amount_usd
                quantity=100,
                unit=CostUnit.TOKENS,
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

    def test_negative_amount_usd_raises_error(self) -> None:
        """Test that negative amount_usd raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CostRecordedEvent(
                cost_type=CostType.LLM,
                amount_usd="-0.001",
                quantity=100,
                unit=CostUnit.TOKENS,
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

        assert "amount_usd" in str(exc_info.value)

    def test_invalid_cost_type_unit_combination_raises_error(self) -> None:
        """Test that mismatched cost_type and unit raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CostRecordedEvent(
                cost_type=CostType.LLM,
                amount_usd="0.001",
                quantity=100,
                unit=CostUnit.PAGES,  # Should be TOKENS for LLM
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )

        assert "Invalid unit" in str(exc_info.value)
        assert "pages" in str(exc_info.value)
        assert "TOKENS" in str(exc_info.value)

    def test_valid_cost_type_unit_combinations(self) -> None:
        """Test that all valid cost_type/unit combinations work."""
        valid_combinations = [
            (CostType.LLM, CostUnit.TOKENS),
            (CostType.DOCUMENT, CostUnit.PAGES),
            (CostType.EMBEDDING, CostUnit.QUERIES),
            (CostType.SMS, CostUnit.MESSAGES),
        ]

        for cost_type, unit in valid_combinations:
            event = CostRecordedEvent(
                cost_type=cost_type,
                amount_usd="0.001",
                quantity=100,
                unit=unit,
                timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
                source_service="ai-model",
                success=True,
                metadata={},
            )
            assert event.cost_type == cost_type
            assert event.unit == unit


class TestCostRecordedEventSerialization:
    """Tests for CostRecordedEvent JSON serialization."""

    def test_model_dump_json_produces_valid_json(self) -> None:
        """Test that model_dump_json() produces valid JSON."""
        import json

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.0015",
            quantity=1500,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={"model": "anthropic/claude-3-haiku"},
        )

        json_str = event.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["cost_type"] == "llm"
        assert parsed["source_service"] == "ai-model"
        assert parsed["success"] is True

    def test_decimal_serialized_as_string(self) -> None:
        """Test that Decimal values are serialized as strings."""
        import json

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.00123456",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        # amount_usd should be a string to preserve precision
        assert isinstance(parsed["amount_usd"], str)
        assert parsed["amount_usd"] == "0.00123456"

    def test_timestamp_serialized_as_iso_format(self) -> None:
        """Test that timestamp is serialized as ISO format string."""
        import json

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.001",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 45, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        # timestamp should be ISO format
        assert isinstance(parsed["timestamp"], str)
        assert "2026-01-12" in parsed["timestamp"]
        assert "10:30:45" in parsed["timestamp"]

    def test_enum_serialized_as_value(self) -> None:
        """Test that enums are serialized as their string values."""
        import json

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.001",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["cost_type"] == "llm"
        assert parsed["unit"] == "tokens"

    def test_optional_fields_null_when_not_set(self) -> None:
        """Test that optional fields are null when not set."""
        import json

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.001",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={},
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["factory_id"] is None
        assert parsed["request_id"] is None

    def test_model_dump_preserves_metadata_structure(self) -> None:
        """Test that metadata dict structure is preserved in serialization."""
        import json

        metadata = {
            "model": "anthropic/claude-3-haiku",
            "agent_type": "extractor",
            "tokens_in": 1000,
            "tokens_out": 500,
            "nested": {"key": "value"},
        }

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.001",
            quantity=100,
            unit=CostUnit.TOKENS,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata=metadata,
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["metadata"]["model"] == "anthropic/claude-3-haiku"
        assert parsed["metadata"]["tokens_in"] == 1000
        assert parsed["metadata"]["nested"]["key"] == "value"


class TestCostRecordedEventDeserialization:
    """Tests for CostRecordedEvent deserialization from JSON."""

    def test_model_validate_json(self) -> None:
        """Test deserializing from JSON string."""
        json_str = """{
            "cost_type": "llm",
            "amount_usd": "0.0015",
            "quantity": 1500,
            "unit": "tokens",
            "timestamp": "2026-01-12T10:30:00Z",
            "source_service": "ai-model",
            "success": true,
            "metadata": {"model": "anthropic/claude-3-haiku"},
            "factory_id": null,
            "request_id": null
        }"""

        event = CostRecordedEvent.model_validate_json(json_str)

        assert event.cost_type == CostType.LLM
        assert event.amount_usd == Decimal("0.0015")
        assert event.quantity == 1500
        assert event.unit == CostUnit.TOKENS
        assert event.source_service == "ai-model"
        assert event.success is True

    def test_roundtrip_serialization(self) -> None:
        """Test that serialization and deserialization are reversible."""
        original = CostRecordedEvent(
            cost_type=CostType.DOCUMENT,
            amount_usd="0.25",
            quantity=5,
            unit=CostUnit.PAGES,
            timestamp=datetime(2026, 1, 12, 10, 30, 0, tzinfo=UTC),
            source_service="ai-model",
            success=True,
            metadata={"document_id": "doc-123"},
            factory_id="FAC-001",
            request_id="req-456",
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        restored = CostRecordedEvent.model_validate_json(json_str)

        # Compare
        assert restored.cost_type == original.cost_type
        assert restored.amount_usd == original.amount_usd
        assert restored.quantity == original.quantity
        assert restored.unit == original.unit
        assert restored.source_service == original.source_service
        assert restored.success == original.success
        assert restored.factory_id == original.factory_id
        assert restored.request_id == original.request_id


class TestBackwardCompatibilityImports:
    """Tests for backward compatibility with legacy import paths."""

    def test_import_from_new_location(self) -> None:
        """Test importing from the new cost_recorded module."""
        from fp_common.events.cost_recorded import (
            CostRecordedEvent as NewCostRecordedEvent,
            CostType,
            CostUnit,
        )

        assert NewCostRecordedEvent is not None
        assert CostType is not None
        assert CostUnit is not None

    def test_import_from_legacy_location(self) -> None:
        """Test importing from the legacy ai_model_events module (deprecated)."""
        # This import should work but may show deprecation warning
        from fp_common.events.ai_model_events import (
            CostRecordedEvent as LegacyCostRecordedEvent,
        )

        # The legacy CostRecordedEvent should still work
        # Note: The legacy model has a different schema (LLM-only)
        # This test verifies the import works, not schema compatibility
        assert LegacyCostRecordedEvent is not None

    def test_import_from_events_init(self) -> None:
        """Test importing from the events package __init__."""
        from fp_common.events import CostRecordedEvent, CostType, CostUnit

        assert CostRecordedEvent is not None
        assert CostType is not None
        assert CostUnit is not None
