"""Unit tests for Cost Event factory.

Story 0.8.6: Cost Event Demo Data Generator
Tests AC #1: CostEventFactory generates valid UnifiedCostEvent instances
Tests AC #2: Cost events are JSON-serializable
Tests AC #6: Unit tests validate factory behavior with full coverage
Tests AC #7: Metadata is realistic per cost type
"""

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

# Skip all tests if polyfactory is not installed
pytest.importorskip("polyfactory", reason="polyfactory required for generator tests")

# Add tests/demo and scripts/demo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests" / "demo"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts" / "demo"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "platform-cost" / "src"))

from fk_registry import FKRegistry
from generators import reset_fk_registry, set_fk_registry
from generators.cost import (
    AGENT_TYPES,
    COST_AMOUNT_RANGES,
    COST_TYPE_UNIT_MAP,
    KNOWLEDGE_DOMAINS,
    LLM_MODELS,
    SMS_MESSAGE_TYPES,
    CostEventFactory,
)
from platform_cost.domain.cost_event import UnifiedCostEvent


@pytest.fixture(autouse=True)
def reset_factories():
    """Reset FK registry and counters before each test."""
    reset_fk_registry()
    CostEventFactory.reset_counter()
    yield


@pytest.fixture
def fk_registry():
    """Create and configure FK registry."""
    registry = FKRegistry()
    set_fk_registry(registry)
    # Register factories for optional FK
    registry.register("factories", ["factory-001", "factory-002"])
    return registry


class TestCostEventFactory:
    """Tests for CostEventFactory basic build behavior."""

    def test_build_creates_valid_cost_event(self, fk_registry) -> None:
        """Build should create a valid UnifiedCostEvent instance."""
        event = CostEventFactory.build()
        assert isinstance(event, UnifiedCostEvent)

    def test_event_passes_pydantic_revalidation(self, fk_registry) -> None:
        """Generated event should pass Pydantic re-validation."""
        event = CostEventFactory.build()
        validated = UnifiedCostEvent.model_validate(event.model_dump())
        assert validated.id == event.id
        assert validated.cost_type == event.cost_type

    def test_cost_type_unit_pairing_valid(self, fk_registry) -> None:
        """Each cost_type should have the correct unit."""
        for cost_type, expected_unit in COST_TYPE_UNIT_MAP.items():
            event = CostEventFactory.build(cost_type=cost_type)
            assert event.unit == expected_unit, (
                f"cost_type={cost_type} should have unit={expected_unit}, got {event.unit}"
            )

    def test_amount_usd_non_negative(self, fk_registry) -> None:
        """amount_usd should always be non-negative."""
        for _ in range(50):
            event = CostEventFactory.build()
            assert event.amount_usd >= 0

    def test_request_id_unique(self, fk_registry) -> None:
        """Each event should have a unique request_id."""
        events = [CostEventFactory.build() for _ in range(20)]
        request_ids = [e.request_id for e in events]
        assert len(set(request_ids)) == len(request_ids)

    def test_id_unique(self, fk_registry) -> None:
        """Each event should have a unique id."""
        events = [CostEventFactory.build() for _ in range(20)]
        ids = [e.id for e in events]
        assert len(set(ids)) == len(ids)

    def test_amount_in_realistic_range(self, fk_registry) -> None:
        """Amount should be within realistic range for the cost_type."""
        for cost_type, (min_amt, max_amt) in COST_AMOUNT_RANGES.items():
            for _ in range(10):
                event = CostEventFactory.build(cost_type=cost_type)
                assert Decimal(str(min_amt)) <= event.amount_usd <= Decimal(str(max_amt)), (
                    f"cost_type={cost_type}: amount {event.amount_usd} not in [{min_amt}, {max_amt}]"
                )

    def test_source_service_matches_cost_type(self, fk_registry) -> None:
        """Source service should match the cost type."""
        expected_services = {
            "llm": "ai-model",
            "document": "collection-model",
            "embedding": "knowledge-model",
            "sms": "notification-model",
        }
        for cost_type, expected_service in expected_services.items():
            event = CostEventFactory.build(cost_type=cost_type)
            assert event.source_service == expected_service

    def test_timestamp_is_recent(self, fk_registry) -> None:
        """Timestamp should be within reasonable range."""
        event = CostEventFactory.build()
        now = datetime.now(UTC)
        # Should be within last 31 days
        assert (now - event.timestamp).days <= 31

    def test_success_mostly_true(self, fk_registry) -> None:
        """Success should be mostly True (95% rate)."""
        events = [CostEventFactory.build() for _ in range(100)]
        success_count = sum(1 for e in events if e.success)
        # Allow some variance - should be roughly 85-100% in 100 samples
        assert success_count >= 80


class TestCostEventFactoryMetadata:
    """Tests for metadata generation per cost type (AC #7)."""

    def test_llm_metadata(self, fk_registry) -> None:
        """LLM events should have model, agent_type, tokens_in, tokens_out."""
        event = CostEventFactory.build(cost_type="llm")
        assert "model" in event.metadata
        assert "agent_type" in event.metadata
        assert "tokens_in" in event.metadata
        assert "tokens_out" in event.metadata
        assert event.metadata["model"] in LLM_MODELS
        assert event.metadata["agent_type"] in AGENT_TYPES
        assert isinstance(event.metadata["tokens_in"], int)
        assert isinstance(event.metadata["tokens_out"], int)

    def test_document_metadata(self, fk_registry) -> None:
        """Document events should have model_id, page_count."""
        event = CostEventFactory.build(cost_type="document")
        assert "model_id" in event.metadata
        assert "page_count" in event.metadata
        assert event.metadata["model_id"] == "prebuilt-document"
        assert isinstance(event.metadata["page_count"], int)
        assert 1 <= event.metadata["page_count"] <= 10

    def test_embedding_metadata(self, fk_registry) -> None:
        """Embedding events should have model, knowledge_domain, texts_count."""
        event = CostEventFactory.build(cost_type="embedding")
        assert "model" in event.metadata
        assert "knowledge_domain" in event.metadata
        assert "texts_count" in event.metadata
        assert event.metadata["model"] == "text-embedding-3-small"
        assert event.metadata["knowledge_domain"] in KNOWLEDGE_DOMAINS
        assert isinstance(event.metadata["texts_count"], int)

    def test_sms_metadata(self, fk_registry) -> None:
        """SMS events should have message_type, recipient_count."""
        event = CostEventFactory.build(cost_type="sms")
        assert "message_type" in event.metadata
        assert "recipient_count" in event.metadata
        assert event.metadata["message_type"] in SMS_MESSAGE_TYPES
        assert isinstance(event.metadata["recipient_count"], int)
        assert 1 <= event.metadata["recipient_count"] <= 5

    def test_llm_indexed_fields(self, fk_registry) -> None:
        """LLM events should populate agent_type and model indexed fields."""
        event = CostEventFactory.build(cost_type="llm")
        assert event.agent_type is not None
        assert event.agent_type in AGENT_TYPES
        assert event.model is not None
        assert event.model in LLM_MODELS

    def test_embedding_indexed_fields(self, fk_registry) -> None:
        """Embedding events should populate model and knowledge_domain indexed fields."""
        event = CostEventFactory.build(cost_type="embedding")
        assert event.model == "text-embedding-3-small"
        assert event.knowledge_domain is not None
        assert event.knowledge_domain in KNOWLEDGE_DOMAINS

    def test_non_llm_no_agent_type(self, fk_registry) -> None:
        """Non-LLM events should not have agent_type indexed field."""
        for ct in ("document", "embedding", "sms"):
            event = CostEventFactory.build(cost_type=ct)
            assert event.agent_type is None


class TestCostEventFactorySerialization:
    """Tests for JSON serialization (AC #2)."""

    def test_json_serializable(self, fk_registry) -> None:
        """Events should be JSON-serializable via model_dump(mode='json')."""
        event = CostEventFactory.build()
        json_str = json.dumps(event.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "cost_type" in parsed
        assert "amount_usd" in parsed

    def test_decimal_serialized_as_string(self, fk_registry) -> None:
        """Decimal amounts should serialize as strings."""
        event = CostEventFactory.build()
        dumped = event.model_dump(mode="json")
        assert isinstance(dumped["amount_usd"], str)

    def test_roundtrip_serialization(self, fk_registry) -> None:
        """Events should round-trip through JSON without error."""
        for cost_type in COST_TYPE_UNIT_MAP:
            event = CostEventFactory.build(cost_type=cost_type)
            json_str = json.dumps(event.model_dump(mode="json"))
            parsed = json.loads(json_str)
            # Verify key fields survive round-trip
            assert parsed["cost_type"] == cost_type
            assert parsed["unit"] == COST_TYPE_UNIT_MAP[cost_type]


class TestCostEventFactoryBatch:
    """Tests for batch generation."""

    def test_batch_generates_correct_count(self, fk_registry) -> None:
        """Batch should generate the specified number of events."""
        events = [CostEventFactory.build() for _ in range(25)]
        assert len(events) == 25

    def test_batch_has_unique_request_ids(self, fk_registry) -> None:
        """All events in a batch should have unique request_ids."""
        events = [CostEventFactory.build() for _ in range(50)]
        request_ids = [e.request_id for e in events]
        assert len(set(request_ids)) == 50

    def test_batch_distribution(self, fk_registry) -> None:
        """Batch should have reasonable cost_type distribution."""
        events = [CostEventFactory.build() for _ in range(200)]
        type_counts = {}
        for e in events:
            type_counts[e.cost_type] = type_counts.get(e.cost_type, 0) + 1

        # LLM should be most common (60% weight)
        assert type_counts.get("llm", 0) > type_counts.get("sms", 0)


class TestCostEventFactoryPeriod:
    """Tests for time-period generation."""

    def test_build_batch_for_period_count(self, fk_registry) -> None:
        """Period batch should generate approximately daily_events * days_span events."""
        events = CostEventFactory.build_batch_for_period(
            days_span=7,
            daily_events=5,
        )
        assert len(events) == 35  # 7 * 5

    def test_build_batch_for_period_variable_daily(self, fk_registry) -> None:
        """Period batch with range should generate within expected bounds."""
        events = CostEventFactory.build_batch_for_period(
            days_span=10,
            daily_events=(3, 7),
        )
        # Should be between 30 and 70
        assert 30 <= len(events) <= 70

    def test_build_batch_for_period_timestamps_spread(self, fk_registry) -> None:
        """Events should be spread across the time period."""
        events = CostEventFactory.build_batch_for_period(
            days_span=30,
            daily_events=2,
        )
        # Get unique dates
        dates = set()
        for e in events:
            dates.add(e.timestamp.date())
        # Should cover most of the 30 days
        assert len(dates) >= 20

    def test_build_batch_for_period_distribution(self, fk_registry) -> None:
        """Period batch should respect cost_type distribution."""
        custom_dist = {"llm": 80, "document": 10, "embedding": 5, "sms": 5}
        events = CostEventFactory.build_batch_for_period(
            days_span=10,
            daily_events=20,
            distribution=custom_dist,
        )
        type_counts = {}
        for e in events:
            type_counts[e.cost_type] = type_counts.get(e.cost_type, 0) + 1

        # LLM should dominate with 80% weight
        total = len(events)
        llm_ratio = type_counts.get("llm", 0) / total
        assert llm_ratio > 0.5  # Allow some randomness but should be well above 50%

    def test_build_batch_for_period_custom_services(self, fk_registry) -> None:
        """Period batch with custom source_services should override defaults."""
        custom_services = ["custom-service-a", "custom-service-b"]
        events = CostEventFactory.build_batch_for_period(
            days_span=5,
            daily_events=4,
            source_services=custom_services,
        )
        for e in events:
            assert e.source_service in custom_services


class TestCostEventFactoryOverrides:
    """Tests for custom overrides."""

    def test_override_cost_type(self, fk_registry) -> None:
        """Should be able to override cost_type."""
        event = CostEventFactory.build(cost_type="sms")
        assert event.cost_type == "sms"
        assert event.unit == "messages"

    def test_override_factory_id(self, fk_registry) -> None:
        """Should be able to override factory_id."""
        event = CostEventFactory.build(factory_id="custom-factory")
        assert event.factory_id == "custom-factory"

    def test_override_timestamp(self, fk_registry) -> None:
        """Should be able to override timestamp."""
        fixed_ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = CostEventFactory.build(timestamp=fixed_ts)
        assert event.timestamp == fixed_ts

    def test_override_source_service(self, fk_registry) -> None:
        """Should be able to override source_service."""
        event = CostEventFactory.build(source_service="my-custom-service")
        assert event.source_service == "my-custom-service"

    def test_all_cost_types_generate_valid_events(self, fk_registry) -> None:
        """Each cost type should produce a valid event."""
        for ct in COST_TYPE_UNIT_MAP:
            event = CostEventFactory.build(cost_type=ct)
            assert event.cost_type == ct
            assert event.unit == COST_TYPE_UNIT_MAP[ct]
            # Verify Pydantic validation
            UnifiedCostEvent.model_validate(event.model_dump())
